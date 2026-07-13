import os
import unittest
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("POSTGRES_PASSWORD", "test-postgres-password")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import BusinessException
from app.core.status_codes import FORBIDDEN
from app.crud.contractor import create_operation_sheet, dispatch_operation, list_operation_sheets, update_sheet_progress
from app.db.base import Base
from app.models import *  # noqa: F401,F403
from app.models.workover import (
    ContractorCapacity,
    ContractorCapacityStatus,
    ContractorCapacitySyncStatus,
    OperationStatus,
    ProjectPoolStatus,
    WorkoverOperationSheet,
    WorkoverProjectPool,
)
from app.schemas.contractor import ProgressPatch, WorkoverOperationSheetCreate, WorkoverOperationSheetQuery
from app.services.workover_operation_service import (
    build_closed_loop_status,
    build_workover_operation_dashboard,
    get_workover_operation_sheet,
)
from app.crud.workover_project_pool import delete_project_pool
from app.crud.material import create_material_requirement, get_material_analytics
from app.crud.completion import get_completion_analytics
from app.models.material import MaterialRequirement
from app.models.completion import WellCompletionRecord
from app.schemas.material import MaterialRequirementCreate


class WorkoverOperationSafetyTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        Base.metadata.create_all(engine)
        self.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    @staticmethod
    def _project(**overrides):
        values = {
            "well_no": "WELL-SAFE",
            "report_unit": "一部",
            "territory_unit": "一部",
            "production_priority": 10,
            "status": ProjectPoolStatus.APPROVED,
            "measures_jsonb": {"measures": [{"measure_type": "major_repair"}]},
            "photo_urls": [],
            "is_deleted": False,
            "created_by_id": 1,
        }
        values.update(overrides)
        return WorkoverProjectPool(**values)

    @staticmethod
    def _contractor(**overrides):
        values = {
            "contractor_name": "安全测试承包商",
            "team_name": "安全测试队",
            "report_date": date.today(),
            "available_count": 1,
            "status": ContractorCapacityStatus.AVAILABLE,
            "sync_status": ContractorCapacitySyncStatus.SYNCED,
            "capability_tags": {"major_repair": True},
            "qualification_expire_at": date.today() + timedelta(days=30),
        }
        values.update(overrides)
        return ContractorCapacity(**values)

    def test_dispatch_rejects_unconfirmed_old_expired_and_mismatched_capacity(self):
        invalid_overrides = [
            {"sync_status": ContractorCapacitySyncStatus.PENDING_CONFIRM},
            {"report_date": date.today() - timedelta(days=1)},
            {"qualification_expire_at": None},
            {"qualification_expire_at": date.today() - timedelta(days=1)},
            {"capability_tags": {"major_repair": False}},
        ]
        for index, overrides in enumerate(invalid_overrides):
            with self.subTest(overrides=overrides), self.SessionLocal() as db:
                project = self._project(well_no=f"WELL-DISPATCH-{index}")
                contractor = self._contractor(team_name=f"安全测试队-{index}", **overrides)
                sheet = WorkoverOperationSheet(
                    project=project,
                    operation_no=f"OP-DISPATCH-{index}",
                    status=OperationStatus.WAITING_DISPATCH,
                    progress=0,
                    progress_detail={},
                )
                db.add_all([project, contractor, sheet])
                db.commit()
                with patch("app.crud.contractor.acquire_dispatch_lock", return_value=True), patch(
                    "app.crud.contractor.release_dispatch_lock"
                ):
                    with self.assertRaises(BusinessException):
                        dispatch_operation(db, sheet.id, contractor.id, operator_id=1, operator_ip=None)

    def test_progress_state_machine_rejects_terminal_changes_and_rollbacks(self):
        cases = [
            (OperationStatus.FINISHED, 100, 50),
            (OperationStatus.CANCELED, 40, 100),
            (OperationStatus.WORKING, 50, 0),
            (OperationStatus.WORKING, 50, 49),
            (OperationStatus.WAITING_DISPATCH, 0, 10),
        ]
        for index, (status, current, requested) in enumerate(cases):
            with self.subTest(status=status, requested=requested), self.SessionLocal() as db:
                project = self._project(well_no=f"WELL-PROGRESS-{index}")
                sheet = WorkoverOperationSheet(
                    project=project,
                    operation_no=f"OP-PROGRESS-{index}",
                    status=status,
                    progress=current,
                    progress_detail={},
                )
                db.add_all([project, sheet])
                db.commit()
                with self.assertRaises(BusinessException):
                    update_sheet_progress(
                        db,
                        sheet.id,
                        ProgressPatch(progress=requested),
                        operator_id=1,
                        operator_ip=None,
                    )

    def test_dispatched_sheet_can_start_manually(self):
        with self.SessionLocal() as db:
            project = self._project()
            sheet = WorkoverOperationSheet(
                project=project,
                operation_no="OP-START",
                status=OperationStatus.DISPATCHED,
                progress=0,
                progress_detail={},
            )
            db.add_all([project, sheet])
            db.commit()
            updated = update_sheet_progress(
                db, sheet.id, ProgressPatch(progress=1), operator_id=1, operator_ip=None
            )
            self.assertEqual(updated.status, OperationStatus.WORKING)
            self.assertIsNotNone(updated.actual_start_at)

    def test_operation_list_and_dashboard_apply_project_data_scope(self):
        regular_user = SimpleNamespace(id=1, is_superuser=False, department="一部", roles=[])
        with self.SessionLocal() as db:
            visible = self._project(well_no="VISIBLE", created_by_id=2, report_unit="一部")
            hidden = self._project(well_no="HIDDEN", created_by_id=2, report_unit="二部", territory_unit="二部")
            db.add_all(
                [
                    visible,
                    hidden,
                    WorkoverOperationSheet(project=visible, operation_no="OP-VISIBLE", status=OperationStatus.WORKING, progress=20, progress_detail={}),
                    WorkoverOperationSheet(project=hidden, operation_no="OP-HIDDEN", status=OperationStatus.FINISHED, progress=100, progress_detail={}),
                ]
            )
            db.commit()
            rows, total = list_operation_sheets(db, WorkoverOperationSheetQuery(), current_user=regular_user)
            dashboard = build_workover_operation_dashboard(db, current_user=regular_user)
            self.assertEqual(total, 1)
            self.assertEqual(rows[0].operation_no, "OP-VISIBLE")
            self.assertEqual(dashboard["total_sheets"], 1)
            self.assertEqual(dashboard["status_distribution"]["finished"], 0)
            hidden_sheet = db.query(WorkoverOperationSheet).filter_by(operation_no="OP-HIDDEN").one()
            with self.assertRaises(BusinessException):
                get_workover_operation_sheet(db, hidden_sheet.id, current_user=regular_user)

    def test_dispatch_applies_operation_and_capacity_data_scope(self):
        outsider = SimpleNamespace(id=2, is_superuser=False, department="二部", roles=[])
        with self.SessionLocal() as db:
            project = self._project(report_unit="一部", territory_unit="一部", created_by_id=1)
            contractor = self._contractor(created_by_id=1)
            sheet = WorkoverOperationSheet(
                project=project,
                operation_no="OP-OUT-OF-SCOPE",
                status=OperationStatus.WAITING_DISPATCH,
                progress=0,
                progress_detail={},
            )
            db.add_all([project, contractor, sheet])
            db.commit()
            with self.assertRaises(BusinessException) as ctx:
                dispatch_operation(
                    db, sheet.id, contractor.id, operator_id=outsider.id, operator_ip=None, current_user=outsider
                )
            self.assertEqual(ctx.exception.code, FORBIDDEN)
            db.refresh(sheet)
            db.refresh(contractor)
            self.assertEqual(sheet.status, OperationStatus.WAITING_DISPATCH)
            self.assertEqual(contractor.available_count, 1)

    def test_closed_loop_cannot_complete_before_operation_finishes(self):
        project = self._project()
        sheet = WorkoverOperationSheet(
            project=project, operation_no="OP-CLOSED-LOOP", status=OperationStatus.WORKING,
            progress=90, progress_detail={}, a5_status="施工中",
        )
        result = build_closed_loop_status(
            sheet,
            {"status": "NONE", "total": 0},
            {"status": "RECORDED", "total": 1},
        )
        self.assertNotEqual(result["overall"], "COMPLETE")

    def test_create_sheet_rejects_capacity_input_and_out_of_scope_project(self):
        with self.assertRaises(ValueError):
            WorkoverOperationSheetCreate(project_id=1, contractor_capacity_id=1)

        outsider = SimpleNamespace(id=2, is_superuser=False, department="二部", roles=[])
        with self.SessionLocal() as db:
            project = self._project(created_by_id=1, report_unit="一部", territory_unit="一部")
            db.add(project)
            db.commit()
            with self.assertRaises(BusinessException) as ctx:
                create_operation_sheet(
                    db,
                    WorkoverOperationSheetCreate(project_id=project.id),
                    operator_id=outsider.id,
                    operator_ip=None,
                    current_user=outsider,
                )
            self.assertEqual(ctx.exception.code, FORBIDDEN)

    def test_project_with_waiting_operation_cannot_be_hidden(self):
        with self.SessionLocal() as db:
            project = self._project(status=ProjectPoolStatus.APPROVED)
            sheet = WorkoverOperationSheet(
                project=project, operation_no="OP-WAITING-LINK", status=OperationStatus.WAITING_DISPATCH,
                progress=0, progress_detail={},
            )
            db.add_all([project, sheet])
            db.commit()
            with self.assertRaises(BusinessException):
                delete_project_pool(db, project.id, operator_id=1, operator_ip=None)
            db.refresh(project)
            self.assertFalse(project.is_deleted)

    def test_material_and_completion_analytics_share_operation_scope(self):
        user = SimpleNamespace(id=1, is_superuser=False, department="一部", roles=[])
        with self.SessionLocal() as db:
            visible = self._project(well_no="VISIBLE-SCOPE", report_unit="一部")
            hidden = self._project(well_no="HIDDEN-SCOPE", report_unit="二部", territory_unit="二部", created_by_id=2)
            visible_sheet = WorkoverOperationSheet(project=visible, operation_no="OP-MAT-V", status=OperationStatus.FINISHED, progress=100, progress_detail={})
            hidden_sheet = WorkoverOperationSheet(project=hidden, operation_no="OP-MAT-H", status=OperationStatus.FINISHED, progress=100, progress_detail={})
            db.add_all([visible, hidden, visible_sheet, hidden_sheet])
            db.flush()
            db.add_all([
                MaterialRequirement(well_no=visible.well_no, operation_sheet_id=visible_sheet.id, material_name="管柱", quantity=1),
                MaterialRequirement(well_no=hidden.well_no, operation_sheet_id=hidden_sheet.id, material_name="泵", quantity=1),
                WellCompletionRecord(well_no=visible.well_no, operation_sheet_id=visible_sheet.id, measure_type="检泵"),
                WellCompletionRecord(well_no=hidden.well_no, operation_sheet_id=hidden_sheet.id, measure_type="酸化"),
            ])
            db.commit()
            self.assertEqual(get_material_analytics(db, current_user=user)["total"], 1)
            self.assertEqual(get_completion_analytics(db, current_user=user)["total"], 1)

    def test_material_creation_requires_matching_operation_sheet(self):
        with self.SessionLocal() as db:
            project = self._project(well_no="WELL-MATERIAL-LINK")
            sheet = WorkoverOperationSheet(
                project=project, operation_no="OP-MATERIAL-LINK", status=OperationStatus.WAITING_DISPATCH,
                progress=0, progress_detail={},
            )
            db.add_all([project, sheet])
            db.commit()
            created = create_material_requirement(
                db,
                MaterialRequirementCreate(
                    well_no=project.well_no, operation_sheet_id=sheet.id, material_name="油管", quantity=2
                ),
            )
            self.assertEqual(created.operation_sheet_id, sheet.id)
            with self.assertRaises(BusinessException):
                create_material_requirement(
                    db,
                    MaterialRequirementCreate(well_no="OTHER-WELL", operation_sheet_id=sheet.id, material_name="泵", quantity=1),
                )

    def test_date_filter_uses_interval_overlap_and_keeps_open_work(self):
        with self.SessionLocal() as db:
            project = self._project()
            open_project = self._project(well_no="WELL-SAFE-OPEN")
            db.add_all(
                [
                    project,
                    open_project,
                    WorkoverOperationSheet(
                        project=open_project,
                        operation_no="OP-SPANS-RANGE",
                        status=OperationStatus.FINISHED,
                        progress=100,
                        actual_start_at=datetime(2026, 7, 1),
                        actual_end_at=datetime(2026, 7, 20),
                        progress_detail={},
                    ),
                    WorkoverOperationSheet(
                        project=project,
                        operation_no="OP-OPEN-RANGE",
                        status=OperationStatus.WORKING,
                        progress=50,
                        actual_start_at=datetime(2026, 7, 5),
                        actual_end_at=None,
                        progress_detail={},
                    ),
                ]
            )
            db.commit()
            rows, total = list_operation_sheets(
                db,
                WorkoverOperationSheetQuery(start_date=date(2026, 7, 10), end_date=date(2026, 7, 12)),
            )
            self.assertEqual(total, 2)
            self.assertEqual({row.operation_no for row in rows}, {"OP-SPANS-RANGE", "OP-OPEN-RANGE"})

    def test_a5_stage_requires_real_sync_timestamp(self):
        project = self._project()
        sheet = WorkoverOperationSheet(
            project=project,
            operation_no="OP-A5",
            status=OperationStatus.DISPATCHED,
            progress=0,
            progress_detail={},
            a5_status="待A5措施审核",
            last_a5_sync_at=None,
        )
        result = build_closed_loop_status(sheet, {"status": "NONE"}, {"status": "NONE"})
        a5_stage = next(item for item in result["stages"] if item["key"] == "a5")
        self.assertFalse(a5_stage["done"])


if __name__ == "__main__":
    unittest.main()
