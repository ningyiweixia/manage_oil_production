import os
import unittest
from datetime import date

os.environ.setdefault("POSTGRES_PASSWORD", "test-postgres-password")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.crud.contractor import dispatch_operation, select_priority_sheets  # noqa: E402
from app.crud.completion import create_completion_record, delete_completion_record, update_completion_record  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models import *  # noqa: F401,F403,E402
from app.models.workover import (  # noqa: E402
    ContractorCapacity,
    ContractorCapacityStatus,
    OperationStatus,
    ProjectPoolStatus,
    WorkoverOperationSheet,
    WorkoverProjectPool,
)
from app.schemas.completion import WellCompletionCreate, WellCompletionUpdate  # noqa: E402


class MemoryCache:
    def __init__(self) -> None:
        self.values = {}

    def set_json(self, key, value, expire_seconds=300, *, nx=False):
        if nx and key in self.values:
            return False
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
            self.assertEqual(select_priority_sheets(db), [])

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
