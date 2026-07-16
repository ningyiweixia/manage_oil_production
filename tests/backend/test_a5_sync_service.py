import asyncio
import base64
import unittest
from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import BusinessException
from app.core.status_codes import A5_LINK_FAILED, CONFLICT
from app.models.workover import ContractorCapacity, ContractorCapacityStatus, OperationStatus, WorkoverOperationSheet, WorkoverProjectPool
from app.models.workover import A5DailyReportRecord, A5SyncBatch
from app.db.base import Base
from app.schemas.a5_integration import A5AnalyticsQuery, A5CallbackPayload
from app.services import a5_sync_service as service
from app.api.v1.endpoints import a5_integration as a5_endpoint


class MemoryCache:
    def __init__(self) -> None:
        self.values = {}

    def get_json(self, key):
        return self.values.get(key)

    def set_json(self, key, value, expire_seconds=300, *, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def delete(self, key):
        self.values.pop(key, None)


class CallbackCache(MemoryCache):
    def set_lock_json(self, key, value, expire_seconds=300, *, nx=False):
        return self.set_json(key, value, expire_seconds, nx=nx)

    def delete_json_if_matches(self, key, value):
        if self.values.get(key) != value:
            return False
        self.delete(key)
        return True


class A5SyncServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
        Base.metadata.create_all(engine)
        self.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def test_status_whitelist_and_version_ordering_reject_unknown_and_stale_events(self):
        self.assertFalse(service.is_supported_a5_status("UNKNOWN_STATE"))
        sheet = SimpleNamespace(
            status=OperationStatus.WORKING,
            progress=40,
            progress_detail={},
            a5_status=None,
            a5_remark=None,
            last_a5_sync_at=None,
            contractor_capacity=None,
            contractor_capacity_id=None,
            actual_start_at=None,
            actual_end_at=None,
        )
        service.apply_a5_update_to_operation_sheet(
            sheet, status="施工中", detail={"event_id": "evt-2", "version": 2}, source="callback"
        )
        service.apply_a5_update_to_operation_sheet(
            sheet, status="办结", detail={"event_id": "evt-1", "version": 1}, source="callback"
        )
        self.assertEqual(sheet.status, OperationStatus.WORKING)
        self.assertEqual(sheet.progress_detail["a5_event_version"], 2)

    def test_daily_fingerprint_accepts_later_event_revisions_and_version_parsing_is_safe(self):
        first = {"event_id": "evt-1", "version": 1, "operation_no": "OP-1", "status": "WORKING"}
        revised = {"event_id": "evt-1", "version": 2, "operation_no": "OP-1", "status": "完成"}
        self.assertNotEqual(service._daily_fingerprint(first), service._daily_fingerprint(revised))

        sheet = SimpleNamespace(
            status=OperationStatus.WORKING,
            progress=40,
            progress_detail={"a5_event_version": 2},
            a5_status=None,
            a5_remark=None,
            last_a5_sync_at=None,
            last_a5_report_date=None,
            a5_sync_result=None,
            a5_sync_error=None,
            contractor_capacity=None,
            contractor_capacity_id=None,
            actual_start_at=None,
            actual_end_at=None,
        )
        service.apply_a5_update_to_operation_sheet(
            sheet, status="施工中", detail={"event_id": "evt-bad", "version": "not-a-number"}, source="callback"
        )
        self.assertEqual(sheet.status, OperationStatus.WORKING)

    def test_callback_replay_is_durable_when_redis_marker_fails_and_allows_revisions(self):
        class FakeRequest:
            headers = {}
            client = SimpleNamespace(host="127.0.0.1")

            async def body(self):
                return b"{}"

        class MarkerFailingCache(CallbackCache):
            def set_json(self, key, value, expire_seconds=300, *, nx=False):
                if ":replay:" in key and not key.endswith(":processing"):
                    raise RuntimeError("redis unavailable")
                return super().set_json(key, value, expire_seconds, nx=nx)

        cache = MarkerFailingCache()
        with self.SessionLocal() as db:
            sheet = WorkoverOperationSheet(
                project_id=1,
                operation_no="OP-CALLBACK-DURABLE",
                status=OperationStatus.PENDING_A5,
                progress=0,
                progress_detail={},
            )
            db.add(sheet)
            db.commit()

            first = A5CallbackPayload(
                operation_no=sheet.operation_no, status="通过", event_id="evt-revision", version=1
            )
            revised = A5CallbackPayload(
                operation_no=sheet.operation_no, status="施工中", event_id="evt-revision", version=2
            )
            with patch.object(a5_endpoint, "cache_client", cache), patch.object(
                a5_endpoint, "verify_a5_callback_signature", return_value=True
            ):
                first_result = asyncio.run(a5_endpoint.a5_callback(first, FakeRequest(), None, db))
                second_result = asyncio.run(a5_endpoint.a5_callback(first, FakeRequest(), None, db))
                revised_result = asyncio.run(a5_endpoint.a5_callback(revised, FakeRequest(), None, db))

            db.refresh(sheet)
            records = list(db.scalars(select(A5DailyReportRecord).order_by(A5DailyReportRecord.id)).all())
            self.assertTrue(first_result.data["matched"])
            self.assertTrue(second_result.data["duplicate"])
            self.assertEqual(revised_result.data["new_status"], OperationStatus.WORKING.value)
            self.assertEqual(sheet.status, OperationStatus.WORKING)
            self.assertEqual(len(records), 2)
            self.assertEqual([row.external_version for row in records], [1, 2])

    def test_local_daily_report_simulation_advances_dispatched_sheets(self):
        sheet = WorkoverOperationSheet(project_id=1, operation_no="OP-LOCAL")
        sheet.status = OperationStatus.DISPATCHED
        sheet.progress = 0

        reports = service.build_local_daily_reports([sheet], "2026-07-06")

        self.assertEqual(reports[0]["operation_no"], "OP-LOCAL")
        self.assertEqual(reports[0]["status"], "WORKING")
        self.assertEqual(reports[0]["progress"], 35)
        self.assertEqual(reports[0]["report_date"], "2026-07-06")

    def test_local_daily_report_simulation_does_not_auto_approve_pending_a5_sheet(self):
        sheet = WorkoverOperationSheet(project_id=1, operation_no="OP-LOCAL-PENDING")
        sheet.status = OperationStatus.PENDING_A5
        sheet.progress = 0

        reports = service.build_local_daily_reports([sheet], "2026-07-06")

        self.assertEqual(reports, [])

    def test_mock_review_requires_access_to_the_operation_sheet_scope(self):
        owner = SimpleNamespace(id=1, is_superuser=False, department=None, roles=[])
        outsider = SimpleNamespace(id=2, is_superuser=False, department=None, roles=[])
        with self.SessionLocal() as db:
            project = WorkoverProjectPool(
                well_no="WELL-SCOPE-001",
                report_unit="第一作业区",
                status="APPROVED",
                measures_jsonb={"measures": []},
                photo_urls=[],
                is_deleted=False,
                created_by_id=owner.id,
            )
            sheet = WorkoverOperationSheet(project=project, operation_no="OP-SCOPE-001", status=OperationStatus.PENDING_A5, progress=0, progress_detail={})
            db.add_all([project, sheet])
            db.commit()
            with (
                patch.object(a5_endpoint, "ensure_local_a5_mock_enabled"),
                patch.object(a5_endpoint, "verify_a5_sso_token"),
            ):
                accessible = a5_endpoint._get_mock_review_sheet(
                    db, operation_no=sheet.operation_no, token="valid-token", current_user=owner
                )
                self.assertEqual(accessible.id, sheet.id)
                with self.assertRaises(BusinessException):
                    a5_endpoint._get_mock_review_sheet(
                        db, operation_no=sheet.operation_no, token="valid-token", current_user=outsider
                    )

    def test_analytics_uses_date_bucket_cache_and_excludes_undated_records(self):
        cache = MemoryCache()
        cache.values.update(
            {
                service.A5_ANOMALY_DATES_KEY: ["2026-06-29", "2026-06-30"],
                f"{service.A5_ANOMALY_RECORDS_PREFIX}2026-06-29": [
                    {"date": "2026-06-29", "anomaly_type": "井口异常"},
                ],
                f"{service.A5_ANOMALY_RECORDS_PREFIX}2026-06-30": [
                    {"date": "2026-06-30", "anomaly_type": "井口异常"},
                    {"anomaly_type": "无日期异常"},
                ],
                service.A5_PROCESS_DATES_KEY: ["2026-06-30"],
                f"{service.A5_PROCESS_RECORDS_PREFIX}2026-06-30": [
                    {"date": "2026-06-30", "process_type": "压裂"},
                ],
            }
        )

        with patch.object(service, "cache_client", cache):
            result = service.build_a5_analytics(
                A5AnalyticsQuery(start_date=date(2026, 6, 30), end_date=date(2026, 6, 30))
            )

        self.assertEqual(result.anomaly_total, 1)
        self.assertEqual(result.special_process_total, 1)
        self.assertEqual(result.trend.days, ["2026-06-30"])
        self.assertEqual(result.anomaly_distribution[0].name, "井口异常")

    def test_full_sync_raises_business_exception_on_partial_failure_for_celery_retry(self):
        cache = MemoryCache()

        async def daily(_db, _sync_date):
            return {"total": 0, "updated": 0, "failed": 0}

        async def anomalies(_db, _sync_date):
            return {"total": 0, "synced": 0, "error": "A5 系统连接失败"}

        async def process(_db, _sync_date):
            return {"total": 0, "synced": 0}

        with (
            patch.object(service, "cache_client", cache),
            patch.object(service, "sync_daily_operations", daily),
            patch.object(service, "sync_anomalies", anomalies),
            patch.object(service, "sync_process_progress", process),
        ):
            with self.assertRaises(BusinessException) as raised:
                asyncio.run(service.full_sync(None))

        self.assertEqual(raised.exception.code, A5_LINK_FAILED)
        self.assertEqual(cache.values[service.A5_SYNC_STATUS_KEY]["last_sync_status"], "partial_failure")

    def test_daily_sync_rejects_a_second_concurrent_trigger(self):
        cache = MemoryCache()
        cache.values["a5:sync:daily-lock"] = {"token": "another-sync"}
        with patch.object(service, "cache_client", cache):
            with self.assertRaises(BusinessException) as raised:
                asyncio.run(service.sync_daily_operations(None, "2026-07-12"))
        self.assertEqual(raised.exception.code, CONFLICT)

    def test_daily_sync_records_cleaning_failure_instead_of_leaving_running_batch(self):
        with self.SessionLocal() as db:
            with (
                patch.object(service.settings, "environment", "local"),
                patch.object(service.settings, "a5_mock_enabled", True),
                patch.object(service, "clean_daily_report", side_effect=ValueError("坏数据")),
            ):
                result = asyncio.run(service.sync_daily_operations(db, "2026-07-12"))

            batch = db.scalar(select(A5SyncBatch))
            self.assertEqual(batch.status, "FAILED")
            self.assertIsNotNone(batch.finished_at)
            self.assertEqual(result["failed"], 1)
            self.assertIn("清洗失败", result["error"])

    def test_export_a5_analytics_report_returns_xlsx_payload(self):
        cache = MemoryCache()
        cache.values.update(
            {
                service.A5_ANOMALY_DATES_KEY: ["2026-06-30"],
                f"{service.A5_ANOMALY_RECORDS_PREFIX}2026-06-30": [
                    {"date": "2026-06-30", "anomaly_type": "井口异常"},
                ],
                service.A5_PROCESS_DATES_KEY: ["2026-06-30"],
                f"{service.A5_PROCESS_RECORDS_PREFIX}2026-06-30": [
                    {"date": "2026-06-30", "process_type": "压裂"},
                ],
            }
        )

        with patch.object(service, "cache_client", cache):
            result = service.export_a5_analytics_report(
                A5AnalyticsQuery(start_date=date(2026, 6, 30), end_date=date(2026, 6, 30)),
                template_name="专项模板",
            )

        self.assertTrue(result.filename.endswith(".xlsx"))
        self.assertTrue(base64.b64decode(result.content_base64).startswith(b"PK"))

    def test_a5_release_capacity_only_when_leaving_occupied_status(self):
        contractor = ContractorCapacity(
            contractor_name="测试承包商",
            team_name="一队",
            report_date=date(2026, 6, 30),
            available_count=0,
            status=ContractorCapacityStatus.BUSY,
            capability_tags={},
        )
        sheet = WorkoverOperationSheet(
            project_id=1,
            operation_no="OP-TEST-001",
            status=OperationStatus.DISPATCHED,
            progress=1,
            progress_detail={},
        )
        sheet.contractor_capacity = contractor

        service.apply_a5_update_to_operation_sheet(
            sheet,
            status="完成",
            source="callback",
        )
        self.assertEqual(sheet.status, OperationStatus.FINISHED)
        self.assertEqual(contractor.available_count, 1)

        service.apply_a5_update_to_operation_sheet(
            sheet,
            status="取消",
            source="callback",
        )
        self.assertEqual(sheet.status, OperationStatus.FINISHED)
        self.assertEqual(contractor.available_count, 1)

    def test_a5_terminal_sheet_rejects_late_status_and_progress_regression(self):
        contractor = ContractorCapacity(
            contractor_name="测试承包商",
            team_name="一队",
            report_date=date(2026, 6, 30),
            available_count=0,
            status=ContractorCapacityStatus.BUSY,
            capability_tags={},
        )
        sheet = WorkoverOperationSheet(
            project_id=1,
            operation_no="OP-LOCK-001",
            status=OperationStatus.DISPATCHED,
            progress=1,
            progress_detail={},
        )
        sheet.contractor_capacity = contractor
        service.apply_a5_update_to_operation_sheet(sheet, status="完成", progress=100, source="callback")
        service.apply_a5_update_to_operation_sheet(sheet, status="施工中", progress=60, source="daily_report")

        self.assertEqual(sheet.status, OperationStatus.FINISHED)
        self.assertEqual(sheet.progress, 100)
        self.assertEqual(contractor.available_count, 1)

    def test_a5_non_terminal_progress_same_day_applies_but_working_rejection_is_ignored(self):
        contractor = ContractorCapacity(
            contractor_name="测试承包商", team_name="一队", report_date=date(2026, 7, 12),
            available_count=0, status=ContractorCapacityStatus.BUSY, capability_tags={},
        )
        sheet = WorkoverOperationSheet(
            project_id=1, operation_no="OP-A5-PROGRESS", status=OperationStatus.DISPATCHED,
            progress=1, progress_detail={},
        )
        sheet.contractor_capacity = contractor

        service.apply_a5_update_to_operation_sheet(
            sheet, status="施工中", progress="35%", detail={"report_date": "2026-07-12"}, source="daily_report"
        )
        service.apply_a5_update_to_operation_sheet(
            sheet, status="施工中", progress=65, detail={"report_date": "2026-07-12"}, source="daily_report"
        )
        self.assertEqual(sheet.status, OperationStatus.WORKING)
        self.assertEqual(sheet.progress, 65)

        service.apply_a5_update_to_operation_sheet(sheet, status="驳回", source="callback")
        self.assertEqual(sheet.status, OperationStatus.WORKING)
        self.assertEqual(sheet.progress, 65)
        self.assertEqual(contractor.available_count, 0)
        self.assertEqual(sheet.a5_sync_result, "IGNORED")

    def test_invalid_transition_does_not_overwrite_canonical_a5_state_or_progress(self):
        sheet = WorkoverOperationSheet(
            project_id=1, operation_no="OP-INVALID-TRANSITION", status=OperationStatus.WAITING_DISPATCH,
            progress=0, progress_detail={}, a5_status=None,
        )

        service.apply_a5_update_to_operation_sheet(
            sheet, status="施工中", progress=60, detail={"event_id": "unexpected-working"}, source="daily_report"
        )

        self.assertEqual(sheet.status, OperationStatus.WAITING_DISPATCH)
        self.assertEqual(sheet.progress, 0)
        self.assertIsNone(sheet.a5_status)
        self.assertEqual(sheet.a5_sync_result, "IGNORED")

    def test_pending_a5_only_advances_after_a5_dispatch_and_rejection_releases_team(self):
        contractor = ContractorCapacity(
            contractor_name="测试承包商", team_name="一队", report_date=date(2026, 7, 12),
            available_count=0, status=ContractorCapacityStatus.BUSY, capability_tags={},
        )
        sheet = WorkoverOperationSheet(
            project_id=1, operation_no="OP-PENDING-A5", status=OperationStatus.PENDING_A5,
            progress=0, progress_detail={}, a5_status="待措施审核",
        )
        sheet.contractor_capacity = contractor

        service.apply_a5_update_to_operation_sheet(sheet, status="审核中", source="daily_report")
        self.assertEqual(sheet.status, OperationStatus.PENDING_A5)
        service.apply_a5_update_to_operation_sheet(sheet, status="已下发", progress=1, source="daily_report")
        self.assertEqual(sheet.status, OperationStatus.DISPATCHED)

        sheet.status = OperationStatus.PENDING_A5
        service.apply_a5_update_to_operation_sheet(sheet, status="驳回", source="daily_report")
        self.assertEqual(sheet.status, OperationStatus.WAITING_DISPATCH)
        self.assertEqual(contractor.available_count, 1)

    def test_daily_sync_keeps_prior_updates_when_one_record_fails(self):
        class FakeClient:
            async def fetch_daily_reports(self, _sync_date, **_kwargs):
                return ([{"operation_no": "OP-1"}, {"operation_no": "OP-2"}], "next-1")

        with self.SessionLocal() as db:
            with (
                patch.object(service.settings, "a5_base_url", "https://a5.example"),
                patch.object(service.settings, "a5_api_key", "key"),
                patch.object(service.settings, "a5_api_secret", "secret"),
                patch.object(service, "A5Client", return_value=FakeClient()),
                patch.object(service, "clean_daily_report", return_value=[{"operation_no": "OP-1", "status": "WORKING"}, {"operation_no": "OP-2", "status": "WORKING"}]),
                patch.object(service, "validate_operation_data", return_value=True),
                patch.object(service, "apply_a5_update_by_operation_no", side_effect=[(SimpleNamespace(id=1), OperationStatus.DISPATCHED, OperationStatus.WORKING, True), RuntimeError("坏记录")]),
            ):
                result = asyncio.run(service.sync_daily_operations(db, "2026-07-12"))

            self.assertEqual(result, {"total": 2, "updated": 1, "unchanged": 0, "not_found": 0, "failed": 1})
            self.assertEqual(len(db.scalars(select(A5DailyReportRecord)).all()), 2)
            batch = db.scalar(select(A5SyncBatch))
            self.assertEqual(batch.status, "PARTIAL")

    def test_a5_sso_redirect_includes_operation_no_when_provided(self):
        from app.services.a5_auth_service import generate_sso_token

        with (
            patch.object(service.settings, "a5_base_url", "https://a5.example"),
            patch.object(service.settings, "a5_api_key", "key"),
            patch.object(service.settings, "a5_api_secret", "secret"),
        ):
            token = generate_sso_token("WELL-001", "/measure-review", operation_no="OP-TEST-001")

        self.assertIn("well_no=WELL-001", token.redirect_url)
        self.assertIn("operation_no=OP-TEST-001", token.redirect_url)

    def test_local_mock_sso_redirect_targets_review_page_and_token_is_bound_to_well(self):
        from app.services.a5_auth_service import generate_sso_token, verify_a5_sso_token

        with (
            patch.object(service.settings, "environment", "local"),
            patch.object(service.settings, "a5_mock_enabled", True),
            patch.object(service.settings, "a5_mock_frontend_base_url", "http://127.0.0.1:5173"),
        ):
            token = generate_sso_token("WELL-LOCAL", "/measure-review", operation_no="OP-LOCAL-001")
            verify_a5_sso_token(token.token, expected_well_no="WELL-LOCAL")
            with self.assertRaises(BusinessException):
                verify_a5_sso_token(token.token, expected_well_no="WELL-OTHER")

        self.assertIn("/a5-simulator/measure-review", token.redirect_url)
        self.assertIn("operation_no=OP-LOCAL-001", token.redirect_url)

    def test_a5_sso_fails_when_real_integration_is_not_configured(self):
        from app.services.a5_auth_service import generate_sso_token

        with (
            patch.object(service.settings, "a5_base_url", ""),
            patch.object(service.settings, "a5_api_key", ""),
            patch.object(service.settings, "a5_api_secret", ""),
            patch.object(service.settings, "a5_mock_enabled", False),
        ):
            with self.assertRaises(BusinessException):
                generate_sso_token("WELL-001")

    def test_a5_signature_fails_closed_when_secret_missing(self):
        from app.services.a5_auth_service import verify_a5_callback_signature

        with patch.object(service.settings, "a5_api_secret", ""):
            self.assertFalse(verify_a5_callback_signature({"x-a5-signature": "anything"}, "{}"))


if __name__ == "__main__":
    unittest.main()
