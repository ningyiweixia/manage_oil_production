import asyncio
import base64
import unittest
from datetime import date
from unittest.mock import patch

from app.core.exceptions import BusinessException
from app.core.status_codes import A5_LINK_FAILED
from app.models.workover import ContractorCapacity, ContractorCapacityStatus, OperationStatus, WorkoverOperationSheet
from app.schemas.a5_integration import A5AnalyticsQuery
from app.services import a5_sync_service as service


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


class A5SyncServiceTest(unittest.TestCase):
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
        self.assertEqual(sheet.status, OperationStatus.CANCELED)
        self.assertEqual(contractor.available_count, 1)


if __name__ == "__main__":
    unittest.main()
