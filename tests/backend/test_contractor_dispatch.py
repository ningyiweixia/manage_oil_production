import os
import unittest
from datetime import date

os.environ.setdefault("POSTGRES_PASSWORD", "test-postgres-password")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.crud.contractor import dispatch_operation, get_contractor_overview, select_priority_sheets  # noqa: E402
from app.crud.contractor import confirm_contractor_capacity, sync_contractor_capacities  # noqa: E402
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
from app.services.contractor_external_client import ContractorExternalClientError, ExternalContractorTeam  # noqa: E402
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

    def test_dispatch_assigns_team_but_waits_for_a5_to_issue(self):
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
                report_date=date(2026, 7, 8),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                capability_tags={},
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
            self.assertEqual(updated.status, OperationStatus.WAITING_DISPATCH)
            self.assertEqual(updated.project.status, ProjectPoolStatus.APPROVED)
            self.assertEqual(updated.a5_status, "待A5措施审核")
            self.assertEqual(contractor.available_count, 0)
            self.assertEqual(contractor.status, ContractorCapacityStatus.BUSY)
            self.assertEqual(cache.last_expire_seconds, 30)
            self.assertEqual(select_priority_sheets(db), [])

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
                status=OperationStatus.WAITING_DISPATCH,
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

    def test_sync_deducts_local_occupation_from_external_available_count(self):
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
                status=OperationStatus.WAITING_DISPATCH,
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

    def test_overview_sums_available_capacity_counts(self):
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
                status=ProjectPoolStatus.APPROVED,
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
