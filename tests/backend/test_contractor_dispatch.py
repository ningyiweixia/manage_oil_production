import os
import unittest
from datetime import date
from types import SimpleNamespace

os.environ.setdefault("POSTGRES_PASSWORD", "test-postgres-password")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.exceptions import BusinessException  # noqa: E402
from app.core.status_codes import FORBIDDEN  # noqa: E402
from app.crud.contractor import (  # noqa: E402
    acquire_dispatch_lock,
    dispatch_operation,
    get_contractor_overview,
    release_dispatch_lock,
    select_priority_sheets,
)
from app.crud.contractor import confirm_contractor_capacity, sync_contractor_capacities  # noqa: E402
from app.crud.contractor import create_contractor_capacity, list_contractor_capacities, update_contractor_capacity, update_sheet_progress  # noqa: E402
from app.crud.completion import create_completion_record, delete_completion_record, update_completion_record  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models import *  # noqa: F401,F403,E402
from app.models.workover import (  # noqa: E402
    ContractorCapacity,
    ContractorCapacitySourceType,
    ContractorCapacitySyncLog,
    ContractorCapacitySyncResultStatus,
    ContractorCapacitySyncStatus,
    ContractorCapacityStatus,
    ContractorCapacitySyncType,
    OperationStatus,
    ProjectPoolStatus,
    WorkoverOperationSheet,
    WorkoverProjectPool,
)
from app.services.contractor_external_client import ContractorExternalClient, ContractorExternalClientError, ExternalContractorTeam  # noqa: E402
from app.schemas.contractor import ContractorCapacityCreate, ContractorCapacityQuery, ContractorCapacityUpdate, ProgressPatch  # noqa: E402
from app.schemas.completion import WellCompletionCreate, WellCompletionUpdate  # noqa: E402


class MemoryCache:
    def __init__(self) -> None:
        self.values = {}
        self.last_expire_seconds = None

    def set_json(self, key, value, expire_seconds=300, *, nx=False):
        if nx and key in self.values:
            return False
        self.last_expire_seconds = expire_seconds
        self.values[key] = value
        return True

    def delete(self, key):
        self.values.pop(key, None)

    def get_json(self, key):
        return self.values.get(key)

    def delete_json_if_matches(self, key, value):
        if self.values.get(key) != value:
            return False
        self.delete(key)
        return True


class ContractorDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        Base.metadata.create_all(engine)
        self.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def test_dispatch_assigns_team_and_marks_sheet_dispatched(self):
        from app.crud import contractor as contractor_crud

        cache = MemoryCache()
        with self.SessionLocal() as db:
            project = WorkoverProjectPool(
                well_no="WELL-001",
                report_unit="第一采油作业区",
                production_priority=10,
                status=ProjectPoolStatus.APPROVED,
                measures_jsonb={"measures": []},
                photo_urls=[],
                is_deleted=False,
            )
            contractor = ContractorCapacity(
                contractor_name="测试承包商",
                team_name="一队",
                report_date=date.today(),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                sync_status=ContractorCapacitySyncStatus.SYNCED,
                capability_tags={},
                qualification_expire_at=date.today(),
            )
            sheet = WorkoverOperationSheet(
                project=project,
                operation_no="OP-TEST-001",
                status=OperationStatus.WAITING_DISPATCH,
                progress=0,
                progress_detail={},
            )
            db.add_all([project, contractor, sheet])
            db.commit()

            original_cache = contractor_crud.cache_client
            contractor_crud.cache_client = cache
            try:
                updated = dispatch_operation(
                    db,
                    sheet.id,
                    contractor.id,
                    operator_id=1,
                    operator_ip="127.0.0.1",
                )
            finally:
                contractor_crud.cache_client = original_cache

            self.assertEqual(updated.contractor_capacity_id, contractor.id)
            self.assertEqual(updated.status, OperationStatus.DISPATCHED)
            self.assertEqual(updated.project.status, ProjectPoolStatus.DISPATCHED)
            self.assertIsNone(updated.a5_status)
            self.assertIsNone(updated.last_a5_sync_at)
            self.assertEqual(contractor.available_count, 0)
            self.assertEqual(contractor.status, ContractorCapacityStatus.BUSY)
            self.assertEqual(cache.last_expire_seconds, 30)
            self.assertEqual(select_priority_sheets(db), [])

    def test_capacity_report_requires_enabled_capability_tag(self):
        with self.assertRaises(ValueError):
            ContractorCapacityCreate(
                contractor_name="测试承包商",
                team_name="无能力队",
                report_date=date(2026, 7, 10),
                available_count=1,
                capability_tags={},
            )

        with self.assertRaises(ValueError):
            ContractorCapacityCreate(
                contractor_name="测试承包商",
                team_name="全关闭队",
                report_date=date(2026, 7, 10),
                available_count=1,
                capability_tags={"major_repair": False},
            )

        with self.assertRaises(ValueError):
            ContractorCapacityCreate(
                contractor_name="伪造同步承包商",
                team_name="伪造同步队",
                report_date=date(2026, 7, 12),
                available_count=1,
                capability_tags={"major_repair": True},
                source_type="EXTERNAL_SYNC",
                sync_status="SYNCED",
            )

    def test_redeclare_same_team_updates_existing_local_report(self):
        with self.SessionLocal() as db:
            first = create_contractor_capacity(
                db,
                ContractorCapacityCreate(
                    contractor_name="重复承包商",
                    team_name="重复队",
                    report_date=date(2026, 7, 10),
                    available_count=1,
                    status=ContractorCapacityStatus.AVAILABLE,
                    capability_tags={"major_repair": True},
                    contact_name="张三",
                ),
                operator_id=1,
                operator_ip="127.0.0.1",
            )
            second = create_contractor_capacity(
                db,
                ContractorCapacityCreate(
                    contractor_name="重复承包商",
                    team_name="重复队",
                    report_date=date(2026, 7, 10),
                    available_count=3,
                    status=ContractorCapacityStatus.AVAILABLE,
                    capability_tags={"fracturing": True},
                    contact_name="李四",
                ),
                operator_id=1,
                operator_ip="127.0.0.1",
            )

            self.assertEqual(first.id, second.id)
            self.assertEqual(db.query(ContractorCapacity).count(), 1)
            self.assertEqual(second.available_count, 3)
            self.assertEqual(second.capability_tags["fracturing"], True)
            self.assertEqual(second.contact_name, "李四")
            self.assertEqual(second.sync_status, ContractorCapacitySyncStatus.PENDING_CONFIRM)
            self.assertEqual(second.created_by_id, 1)

    def test_redeclare_same_team_cannot_take_over_other_users_report(self):
        regular_user = SimpleNamespace(
            id=2,
            is_superuser=False,
            department=None,
            roles=[SimpleNamespace(code="contractor_operator", is_active=True)],
        )
        with self.SessionLocal() as db:
            db.add(
                ContractorCapacity(
                    contractor_name="他人承包商",
                    team_name="他人队",
                    report_date=date(2026, 7, 10),
                    available_count=1,
                    status=ContractorCapacityStatus.AVAILABLE,
                    source_type=ContractorCapacitySourceType.LOCAL_SUPPLEMENT,
                    sync_status=ContractorCapacitySyncStatus.PENDING_CONFIRM,
                    capability_tags={"major_repair": True},
                    created_by_id=1,
                )
            )
            db.commit()

            with self.assertRaises(BusinessException) as ctx:
                create_contractor_capacity(
                    db,
                    ContractorCapacityCreate(
                        contractor_name="他人承包商",
                        team_name="他人队",
                        report_date=date(2026, 7, 10),
                        available_count=3,
                        status=ContractorCapacityStatus.AVAILABLE,
                        capability_tags={"fracturing": True},
                    ),
                    operator_id=2,
                    operator_ip="127.0.0.1",
                    current_user=regular_user,
                )

            row = db.query(ContractorCapacity).one()
            self.assertEqual(ctx.exception.code, FORBIDDEN)
            self.assertEqual(row.available_count, 1)
            self.assertEqual(row.created_by_id, 1)
            self.assertEqual(row.capability_tags["major_repair"], True)

    def test_local_report_cannot_replace_external_snapshot(self):
        with self.SessionLocal() as db:
            db.add(
                ContractorCapacity(
                    contractor_name="外部承包商",
                    team_name="外部队",
                    report_date=date(2026, 7, 10),
                    available_count=1,
                    status=ContractorCapacityStatus.AVAILABLE,
                    source_type=ContractorCapacitySourceType.EXTERNAL_SYNC,
                    capability_tags={"major_repair": True},
                )
            )
            db.commit()

            with self.assertRaises(BusinessException):
                create_contractor_capacity(
                    db,
                    ContractorCapacityCreate(
                        contractor_name="外部承包商",
                        team_name="外部队",
                        report_date=date(2026, 7, 10),
                        available_count=2,
                        status=ContractorCapacityStatus.AVAILABLE,
                        capability_tags={"major_repair": True},
                    ),
                    operator_id=1,
                    operator_ip="127.0.0.1",
                )

    def test_local_report_can_replace_invalid_external_snapshot(self):
        with self.SessionLocal() as db:
            db.add(
                ContractorCapacity(
                    contractor_name="失效外部承包商",
                    team_name="失效外部队",
                    report_date=date(2026, 7, 10),
                    available_count=0,
                    status=ContractorCapacityStatus.OFFLINE,
                    source_type=ContractorCapacitySourceType.EXTERNAL_SYNC,
                    sync_status=ContractorCapacitySyncStatus.INVALID,
                    capability_tags={"major_repair": True},
                    sync_error_message="外部失效",
                )
            )
            db.commit()

            updated = create_contractor_capacity(
                db,
                ContractorCapacityCreate(
                    contractor_name="失效外部承包商",
                    team_name="失效外部队",
                    report_date=date(2026, 7, 10),
                    available_count=2,
                    status=ContractorCapacityStatus.AVAILABLE,
                    capability_tags={"major_repair": True},
                ),
                operator_id=7,
                operator_ip="127.0.0.1",
            )

            self.assertEqual(updated.available_count, 2)
            self.assertEqual(updated.source_type, ContractorCapacitySourceType.LOCAL_SUPPLEMENT)
            self.assertEqual(updated.created_by_id, 7)

    def test_update_local_report_marks_pending_without_exposing_sync_fields(self):
        with self.SessionLocal() as db:
            contractor = ContractorCapacity(
                contractor_name="待改承包商",
                team_name="待改队",
                report_date=date(2026, 7, 10),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                sync_status=ContractorCapacitySyncStatus.SYNCED,
                source_type=ContractorCapacitySourceType.LOCAL_SUPPLEMENT,
                capability_tags={"major_repair": True},
            )
            db.add(contractor)
            db.commit()

            payload = ContractorCapacityUpdate.model_validate(
                {
                    "contact_name": "王五",
                    "sync_status": "SYNCED",
                    "source_type": "EXTERNAL_SYNC",
                }
            )
            updated = update_contractor_capacity(
                db,
                contractor.id,
                payload,
                operator_id=1,
                operator_ip="127.0.0.1",
            )

            self.assertEqual(updated.contact_name, "王五")
            self.assertEqual(updated.sync_status, ContractorCapacitySyncStatus.PENDING_CONFIRM)
            self.assertEqual(updated.source_type, ContractorCapacitySourceType.LOCAL_SUPPLEMENT)

    def test_contractor_capacity_scope_limits_regular_user_to_own_reports(self):
        regular_user = SimpleNamespace(
            id=1,
            is_superuser=False,
            department=None,
            roles=[SimpleNamespace(code="contractor_operator", is_active=True)],
        )
        super_user = SimpleNamespace(id=99, is_superuser=True, department=None, roles=[])
        with self.SessionLocal() as db:
            own = ContractorCapacity(
                contractor_name="本方承包商",
                team_name="本方队",
                report_date=date(2026, 7, 10),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                capability_tags={"major_repair": True},
                created_by_id=1,
            )
            other = ContractorCapacity(
                contractor_name="他方承包商",
                team_name="他方队",
                report_date=date(2026, 7, 10),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                capability_tags={"major_repair": True},
                created_by_id=2,
            )
            db.add_all([own, other])
            db.commit()

            regular_rows, regular_total = list_contractor_capacities(
                db,
                ContractorCapacityQuery(report_date=date(2026, 7, 10)),
                current_user=regular_user,
            )
            super_rows, super_total = list_contractor_capacities(
                db,
                ContractorCapacityQuery(report_date=date(2026, 7, 10)),
                current_user=super_user,
            )

            self.assertEqual(regular_total, 1)
            self.assertEqual(regular_rows[0].id, own.id)
            self.assertEqual(super_total, 2)
            self.assertEqual({row.id for row in super_rows}, {own.id, other.id})

            with self.assertRaises(BusinessException) as ctx:
                update_contractor_capacity(
                    db,
                    other.id,
                    ContractorCapacityUpdate(contact_name="越权"),
                    operator_id=1,
                    operator_ip="127.0.0.1",
                    current_user=regular_user,
                )
            self.assertEqual(ctx.exception.code, FORBIDDEN)

    def test_finish_progress_releases_occupied_capacity_once(self):
        from app.crud import contractor as contractor_crud

        cache = MemoryCache()
        with self.SessionLocal() as db:
            project = WorkoverProjectPool(
                well_no="WELL-FINISH",
                report_unit="第一采油作业区",
                production_priority=10,
                status=ProjectPoolStatus.DISPATCHED,
                measures_jsonb={"measures": []},
                photo_urls=[],
                is_deleted=False,
            )
            contractor = ContractorCapacity(
                contractor_name="完工承包商",
                team_name="完工队",
                report_date=date(2026, 7, 10),
                available_count=0,
                status=ContractorCapacityStatus.BUSY,
                capability_tags={"major_repair": True},
            )
            sheet = WorkoverOperationSheet(
                project=project,
                contractor_capacity=contractor,
                operation_no="OP-FINISH",
                status=OperationStatus.WORKING,
                progress=80,
                progress_detail={},
                a5_status="已下发",
            )
            db.add_all([project, contractor, sheet])
            db.commit()

            original_cache = contractor_crud.cache_client
            contractor_crud.cache_client = cache
            try:
                updated = update_sheet_progress(
                    db,
                    sheet.id,
                    ProgressPatch(progress=100, progress_detail={}),
                    operator_id=1,
                    operator_ip="127.0.0.1",
                )
                update_sheet_progress(
                    db,
                    sheet.id,
                    ProgressPatch(progress=100, progress_detail={}),
                    operator_id=1,
                    operator_ip="127.0.0.1",
                )
            finally:
                contractor_crud.cache_client = original_cache

            self.assertEqual(updated.status, OperationStatus.FINISHED)
            self.assertEqual(contractor.available_count, 1)
            self.assertEqual(contractor.status, ContractorCapacityStatus.AVAILABLE)

    def test_capacity_list_uses_aggregated_occupied_count(self):
        with self.SessionLocal() as db:
            project = WorkoverProjectPool(
                well_no="WELL-LIST",
                report_unit="第一采油作业区",
                production_priority=10,
                status=ProjectPoolStatus.APPROVED,
                measures_jsonb={"measures": []},
                photo_urls=[],
                is_deleted=False,
            )
            finished_project = WorkoverProjectPool(
                well_no="WELL-LIST-FINISHED",
                report_unit="第一采油作业区",
                production_priority=10,
                status=ProjectPoolStatus.APPROVED,
                measures_jsonb={"measures": []},
                photo_urls=[],
                is_deleted=False,
            )
            contractor = ContractorCapacity(
                contractor_name="列表承包商",
                team_name="列表队",
                report_date=date(2026, 7, 10),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                capability_tags={"major_repair": True},
            )
            db.add_all(
                [
                    project,
                    contractor,
                    WorkoverOperationSheet(
                        project=project,
                        contractor_capacity=contractor,
                        operation_no="OP-LIST-1",
                        status=OperationStatus.WORKING,
                        progress=50,
                        progress_detail={},
                    ),
                    WorkoverOperationSheet(
                        project=finished_project,
                        contractor_capacity=contractor,
                        operation_no="OP-LIST-2",
                        status=OperationStatus.FINISHED,
                        progress=100,
                        progress_detail={},
                    ),
                ]
            )
            db.commit()

            rows, total = list_contractor_capacities(db, ContractorCapacityQuery(report_date=date(2026, 7, 10)))

            self.assertEqual(total, 1)
            self.assertEqual(rows[0].occupied_count, 1)

    def test_sync_creates_and_updates_capacity_snapshot(self):
        class FakeClient:
            connection_status = "正常"

            def __init__(self) -> None:
                self.count = 0

            def fetch_capacities(self, *, report_date, external_system_id=None):
                self.count += 1
                return [
                    ExternalContractorTeam(
                        external_system_id="EXT-001",
                        contractor_name="外部承包商",
                        team_name="修井一队",
                        report_date=report_date,
                        available_count=2 if self.count == 1 else 3,
                        status=ContractorCapacityStatus.AVAILABLE,
                        external_status="AVAILABLE",
                        capability_tags={"major_repair": True},
                    )
                ]

        client = FakeClient()
        with self.SessionLocal() as db:
            first = sync_contractor_capacities(
                db,
                report_date=date(2026, 7, 10),
                operator_id=1,
                operator_ip="127.0.0.1",
                client=client,
            )
            self.assertEqual(first.status, ContractorCapacitySyncResultStatus.SUCCESS)
            self.assertEqual(first.created_count, 1)
            row = db.query(ContractorCapacity).one()
            self.assertEqual(row.available_count, 2)
            self.assertEqual(row.sync_status, ContractorCapacitySyncStatus.PENDING_CONFIRM)

            second = sync_contractor_capacities(
                db,
                report_date=date(2026, 7, 10),
                operator_id=1,
                operator_ip="127.0.0.1",
                client=client,
            )
            db.refresh(row)
            self.assertEqual(second.updated_count, 1)
            self.assertEqual(row.available_count, 3)

    def test_sync_failure_writes_failed_log(self):
        class FailingClient:
            connection_status = "异常"

            def fetch_capacities(self, *, report_date, external_system_id=None):
                raise ContractorExternalClientError("外部承包商系统网络异常")

        with self.SessionLocal() as db:
            log = sync_contractor_capacities(
                db,
                report_date=date(2026, 7, 10),
                operator_id=1,
                operator_ip="127.0.0.1",
                client=FailingClient(),
            )
            self.assertEqual(log.status, ContractorCapacitySyncResultStatus.FAILED)
            self.assertEqual(log.failed_count, 1)
            self.assertIn("网络异常", log.error_message)
            self.assertEqual(db.query(ContractorCapacitySyncLog).count(), 1)

    def test_external_client_requires_https_for_real_system(self):
        client = ContractorExternalClient(base_url="http://contractor.example.com", token="token", mock_enabled=False)
        with self.assertRaises(ContractorExternalClientError) as ctx:
            client.fetch_capacities(report_date=date(2026, 7, 10))
        self.assertIn("HTTPS", str(ctx.exception))

    def test_sync_marks_conflict_when_external_unavailable_but_local_occupied(self):
        class BusyExternalClient:
            connection_status = "正常"

            def fetch_capacities(self, *, report_date, external_system_id=None):
                return [
                    ExternalContractorTeam(
                        external_system_id="EXT-CONFLICT",
                        contractor_name="冲突承包商",
                        team_name="冲突队",
                        report_date=report_date,
                        available_count=0,
                        status=ContractorCapacityStatus.OFFLINE,
                        external_status="OFFLINE",
                        capability_tags={"major_repair": True},
                    )
                ]

        with self.SessionLocal() as db:
            project = WorkoverProjectPool(
                well_no="WELL-CONFLICT",
                report_unit="第一采油作业区",
                production_priority=10,
                status=ProjectPoolStatus.APPROVED,
                measures_jsonb={"measures": []},
                photo_urls=[],
                is_deleted=False,
            )
            contractor = ContractorCapacity(
                external_system_id="EXT-CONFLICT",
                contractor_name="冲突承包商",
                team_name="冲突队",
                report_date=date(2026, 7, 10),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                capability_tags={},
            )
            sheet = WorkoverOperationSheet(
                project=project,
                contractor_capacity=contractor,
                operation_no="OP-CONFLICT",
                status=OperationStatus.DISPATCHED,
                progress=0,
                progress_detail={},
            )
            db.add_all([project, contractor, sheet])
            db.commit()

            sync_contractor_capacities(
                db,
                report_date=date(2026, 7, 10),
                operator_id=1,
                operator_ip="127.0.0.1",
                client=BusyExternalClient(),
            )
            db.refresh(contractor)
            self.assertEqual(contractor.sync_status, ContractorCapacitySyncStatus.CONFLICT)
            self.assertIn("未完成关联工单", contractor.sync_error_message)

    def test_sync_deducts_local_active_occupation_from_external_total(self):
        class AvailableExternalClient:
            connection_status = "正常"

            def fetch_capacities(self, *, report_date, external_system_id=None):
                return [
                    ExternalContractorTeam(
                        external_system_id="EXT-OCCUPIED",
                        contractor_name="占用承包商",
                        team_name="占用队",
                        report_date=report_date,
                        available_count=1,
                        status=ContractorCapacityStatus.AVAILABLE,
                        external_status="AVAILABLE",
                        capability_tags={},
                    )
                ]

        with self.SessionLocal() as db:
            project = WorkoverProjectPool(
                well_no="WELL-OCCUPIED",
                report_unit="第一采油作业区",
                production_priority=10,
                status=ProjectPoolStatus.APPROVED,
                measures_jsonb={"measures": []},
                photo_urls=[],
                is_deleted=False,
            )
            contractor = ContractorCapacity(
                external_system_id="EXT-OCCUPIED",
                contractor_name="占用承包商",
                team_name="占用队",
                report_date=date(2026, 7, 10),
                available_count=0,
                status=ContractorCapacityStatus.BUSY,
                source_type=ContractorCapacitySourceType.EXTERNAL_SYNC,
                capability_tags={},
            )
            sheet = WorkoverOperationSheet(
                project=project,
                contractor_capacity=contractor,
                operation_no="OP-OCCUPIED",
                status=OperationStatus.DISPATCHED,
                progress=0,
                progress_detail={},
            )
            db.add_all([project, contractor, sheet])
            db.commit()

            sync_contractor_capacities(
                db,
                report_date=date(2026, 7, 10),
                operator_id=1,
                operator_ip="127.0.0.1",
                client=AvailableExternalClient(),
            )
            db.refresh(contractor)
            self.assertEqual(contractor.available_count, 0)
            self.assertEqual(contractor.status, ContractorCapacityStatus.BUSY)
            self.assertEqual(contractor.sync_status, ContractorCapacitySyncStatus.PENDING_CONFIRM)

    def test_full_sync_keeps_missing_local_supplement_available(self):
        class EmptyExternalClient:
            connection_status = "正常"

            def fetch_capacities(self, *, report_date, external_system_id=None):
                return []

        with self.SessionLocal() as db:
            contractor = ContractorCapacity(
                contractor_name="本地补录承包商",
                team_name="本地补录队",
                report_date=date(2026, 7, 10),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                source_type=ContractorCapacitySourceType.LOCAL_SUPPLEMENT,
                sync_status=ContractorCapacitySyncStatus.PENDING_CONFIRM,
                capability_tags={"major_repair": True},
            )
            db.add(contractor)
            db.commit()

            log = sync_contractor_capacities(
                db,
                report_date=date(2026, 7, 10),
                operator_id=1,
                operator_ip="127.0.0.1",
                client=EmptyExternalClient(),
            )

            db.refresh(contractor)
            self.assertEqual(log.ignored_count, 0)
            self.assertEqual(contractor.available_count, 1)
            self.assertEqual(contractor.status, ContractorCapacityStatus.AVAILABLE)
            self.assertEqual(contractor.sync_status, ContractorCapacitySyncStatus.PENDING_CONFIRM)

    def test_single_team_sync_marks_missing_external_team_invalid(self):
        class EmptyExternalClient:
            connection_status = "正常"

            def fetch_capacities(self, *, report_date, external_system_id=None):
                return []

        with self.SessionLocal() as db:
            contractor = ContractorCapacity(
                external_system_id="EXT-MISSING",
                contractor_name="失效承包商",
                team_name="失效队",
                report_date=date(2026, 7, 10),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                source_type=ContractorCapacitySourceType.EXTERNAL_SYNC,
                capability_tags={},
            )
            db.add(contractor)
            db.commit()

            log = sync_contractor_capacities(
                db,
                report_date=date(2026, 7, 10),
                operator_id=1,
                operator_ip="127.0.0.1",
                client=EmptyExternalClient(),
                sync_type=ContractorCapacitySyncType.SINGLE_TEAM,
                external_system_id="EXT-MISSING",
            )
            db.refresh(contractor)
            self.assertEqual(log.ignored_count, 1)
            self.assertEqual(contractor.available_count, 0)
            self.assertEqual(contractor.status, ContractorCapacityStatus.OFFLINE)
            self.assertEqual(contractor.sync_status, ContractorCapacitySyncStatus.INVALID)

    def test_full_sync_empty_response_preserves_daily_snapshot(self):
        class EmptyExternalClient:
            connection_status = "正常"
            invalid_rows = []

            def fetch_capacities(self, *, report_date, external_system_id=None):
                return []

        with self.SessionLocal() as db:
            contractor = ContractorCapacity(
                external_system_id="EXT-PRESERVE",
                contractor_name="保留承包商",
                team_name="保留队",
                report_date=date(2026, 7, 10),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                source_type=ContractorCapacitySourceType.EXTERNAL_SYNC,
                capability_tags={},
            )
            db.add(contractor)
            db.commit()
            log = sync_contractor_capacities(
                db, report_date=date(2026, 7, 10), operator_id=1, operator_ip=None,
                client=EmptyExternalClient(),
            )
            db.refresh(contractor)
            self.assertEqual(log.status, ContractorCapacitySyncResultStatus.FAILED)
            self.assertEqual(contractor.status, ContractorCapacityStatus.AVAILABLE)
            self.assertEqual(contractor.available_count, 1)

    def test_confirm_sync_updates_confirmation_fields(self):
        with self.SessionLocal() as db:
            contractor = ContractorCapacity(
                contractor_name="待确认承包商",
                team_name="待确认队",
                report_date=date(2026, 7, 10),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                capability_tags={},
            )
            db.add(contractor)
            db.commit()

            updated = confirm_contractor_capacity(
                db,
                contractor.id,
                operator_id=7,
                operator_ip="127.0.0.1",
            )
            self.assertEqual(updated.sync_status, ContractorCapacitySyncStatus.SYNCED)
            self.assertEqual(updated.confirmed_by_id, 7)
            self.assertIsNotNone(updated.confirmed_at)

    def test_confirm_rejects_conflict_invalid_and_exception_capacity(self):
        for index, (sync_status, status) in enumerate(
            [
                (ContractorCapacitySyncStatus.CONFLICT, ContractorCapacityStatus.AVAILABLE),
                (ContractorCapacitySyncStatus.INVALID, ContractorCapacityStatus.OFFLINE),
                (ContractorCapacitySyncStatus.PENDING_CONFIRM, ContractorCapacityStatus.EXCEPTION),
            ]
        ):
            with self.subTest(sync_status=sync_status, status=status), self.SessionLocal() as db:
                contractor = ContractorCapacity(
                    contractor_name=f"不可确认承包商-{index}",
                    team_name=f"不可确认队-{index}",
                    report_date=date(2026, 7, 10),
                    available_count=0,
                    status=status,
                    sync_status=sync_status,
                    capability_tags={},
                )
                db.add(contractor)
                db.commit()
                with self.assertRaises(BusinessException):
                    confirm_contractor_capacity(db, contractor.id, operator_id=7, operator_ip=None)
                db.refresh(contractor)
                self.assertEqual(contractor.sync_status, sync_status)

    def test_exception_resolution_preserves_capacity_provenance(self):
        with self.SessionLocal() as db:
            contractor = ContractorCapacity(
                contractor_name="外部来源承包商", team_name="外部来源队", report_date=date(2026, 7, 12),
                available_count=1, status=ContractorCapacityStatus.AVAILABLE,
                source_type=ContractorCapacitySourceType.EXTERNAL_SYNC, capability_tags={},
            )
            db.add(contractor)
            db.commit()
            from app.crud.contractor import mark_contractor_exception, resolve_contractor_exception

            mark_contractor_exception(db, contractor.id, reason="测试异常", operator_id=1, operator_ip=None)
            resolve_contractor_exception(db, contractor.id, operator_id=1, operator_ip=None)
            self.assertEqual(contractor.source_type, ContractorCapacitySourceType.EXTERNAL_SYNC)

    def test_lock_release_does_not_delete_a_reacquired_lock(self):
        from app.crud import contractor as contractor_crud

        cache = MemoryCache()
        original_cache = contractor_crud.cache_client
        contractor_crud.cache_client = cache
        try:
            first_token = acquire_dispatch_lock(42)
            self.assertIsNotNone(first_token)
            key = contractor_crud._dispatch_lock_key("capacity", 42)
            cache.values[key] = {"token": "new-owner", "locked_at": "later"}
            release_dispatch_lock(42, first_token)
            self.assertEqual(cache.values[key]["token"], "new-owner")
        finally:
            contractor_crud.cache_client = original_cache

    def test_sync_failed_returned_record_is_not_marked_missing(self):
        class OneTeamClient:
            connection_status = "正常"

            def fetch_capacities(self, *, report_date, external_system_id=None):
                return [
                    ExternalContractorTeam(
                        external_system_id="EXT-RETURNED-FAIL",
                        contractor_name="返回但写入失败承包商",
                        team_name="返回但写入失败队",
                        report_date=report_date,
                        available_count=1,
                        status=ContractorCapacityStatus.AVAILABLE,
                        external_status="AVAILABLE",
                        capability_tags={"major_repair": True},
                    )
                ]

        with self.SessionLocal() as db:
            contractor = ContractorCapacity(
                external_system_id="EXT-RETURNED-FAIL",
                contractor_name="返回但写入失败承包商",
                team_name="返回但写入失败队",
                report_date=date(2026, 7, 10),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                sync_status=ContractorCapacitySyncStatus.PENDING_CONFIRM,
                source_type=ContractorCapacitySourceType.EXTERNAL_SYNC,
                capability_tags={"major_repair": True},
            )
            db.add(contractor)
            db.commit()
            from unittest.mock import patch

            with patch("app.crud.contractor._upsert_external_team", side_effect=ValueError("字段不合法")):
                log = sync_contractor_capacities(
                    db,
                    report_date=date(2026, 7, 10),
                    operator_id=1,
                    operator_ip=None,
                    client=OneTeamClient(),
                )
            db.refresh(contractor)
            self.assertEqual(log.failed_count, 1)
            self.assertEqual(log.ignored_count, 0)
            self.assertNotEqual(contractor.sync_status, ContractorCapacitySyncStatus.INVALID)
            self.assertEqual(log.raw_summary["failed_teams"][0]["external_system_id"], "EXT-RETURNED-FAIL")

    def test_overview_sums_available_team_capacity(self):
        with self.SessionLocal() as db:
            db.add_all(
                [
                    ContractorCapacity(
                        contractor_name="多队承包商",
                        team_name="联合队",
                        report_date=date(2026, 7, 10),
                        available_count=3,
                        status=ContractorCapacityStatus.AVAILABLE,
                        capability_tags={},
                    ),
                    ContractorCapacity(
                        contractor_name="忙碌承包商",
                        team_name="作业队",
                        report_date=date(2026, 7, 10),
                        available_count=0,
                        status=ContractorCapacityStatus.BUSY,
                        capability_tags={},
                    ),
                ]
            )
            db.commit()

            overview = get_contractor_overview(db, report_date=date(2026, 7, 10))
            self.assertEqual(overview["reported_team_count"], 2)
            self.assertEqual(overview["available_team_count"], 3)
            self.assertEqual(overview["busy_team_count"], 1)

    def test_completion_records_sync_operation_sheet_closed_loop_detail(self):
        with self.SessionLocal() as db:
            project = WorkoverProjectPool(
                well_no="WELL-CL-001",
                report_unit="第一采油作业区",
                production_priority=8,
                status=ProjectPoolStatus.DISPATCHED,
                measures_jsonb={"measures": [{"measure_type": "pump"}]},
                photo_urls=[],
                is_deleted=False,
            )
            sheet = WorkoverOperationSheet(
                project=project,
                operation_no="OP-CL-001",
                status=OperationStatus.FINISHED,
                progress=100,
                progress_detail={},
            )
            db.add_all([project, sheet])
            db.commit()

            record = create_completion_record(
                db,
                WellCompletionCreate(
                    well_no="WELL-CL-001",
                    operation_sheet_id=sheet.id,
                    measure_type="pump",
                    completion_date=date(2026, 7, 8),
                    team_name="第一作业队",
                ),
            )
            db.refresh(sheet)

            self.assertEqual(sheet.progress_detail["completion"]["status"], "RECORDED")
            self.assertEqual(sheet.progress_detail["completion"]["total"], 1)
            self.assertEqual(sheet.progress_detail["completion"]["latest"]["measure_type"], "pump")

            update_completion_record(
                db,
                record.id,
                WellCompletionUpdate(measure_type="acidizing", team_name="第二作业队"),
            )
            db.refresh(sheet)

            self.assertEqual(sheet.progress_detail["completion"]["latest"]["measure_type"], "acidizing")
            self.assertEqual(sheet.progress_detail["completion"]["latest"]["team_name"], "第二作业队")

            delete_completion_record(db, record.id)
            db.refresh(sheet)

            self.assertEqual(sheet.progress_detail["completion"]["status"], "NONE")
            self.assertEqual(sheet.progress_detail["completion"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
