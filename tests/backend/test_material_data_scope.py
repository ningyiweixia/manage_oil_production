import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import BusinessException
from app.crud.material import get_material_analytics, get_material_requirement
from app.db.base import Base
from app.models import *  # noqa: F401,F403
from app.models.material import MaterialRequirement, MaterialRequirementStatus, MaterialRequirementType
from app.models.workover import OperationStatus, ProjectPoolStatus, WorkoverOperationSheet, WorkoverProjectPool
from app.services.data_scope_service import DataScope
from app.schemas.workover_project_pool import WorkoverAnalyticsQuery
from app.services.workover_analytics_service import build_workover_analytics
from app.services.workover_operation_service import OperationAnalyticsQuery, build_workover_operation_dashboard


class MaterialDataScopeTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        with self.Session() as db:
            material_ids = []
            for unit, suffix, territory in (("Unit A", "A", "Territory A"), ("Unit B", "B", None)):
                project = WorkoverProjectPool(
                    well_no=f"WELL-{suffix}", report_unit=unit, territory_unit=territory, production_priority=1,
                    status=ProjectPoolStatus.APPROVED, measures_jsonb={}, photo_urls=[], attachments=[],
                    related_project_ids=[], is_deleted=False,
                )
                sheet = WorkoverOperationSheet(project=project, operation_no=f"OP-{suffix}", status=OperationStatus.WORKING, progress=50, progress_detail={})
                db.add(sheet)
                db.flush()
                material = MaterialRequirement(
                    well_no=f"WELL-{suffix}", operation_sheet_id=sheet.id, material_name="Pipe", quantity=1,
                    unit="item", status=MaterialRequirementStatus.ARRIVED, requirement_type=MaterialRequirementType.NORMAL,
                )
                db.add(material)
                db.flush()
                material_ids.append(material.id)
            db.commit()
        self.unit_a_material_id, self.unit_b_material_id = material_ids
        self.unit_a_scope = DataScope(is_global=False, user_id=1, department="Unit A", reporting_units=("Unit A",))

    def test_material_analytics_is_limited_to_reporting_unit(self):
        with self.Session() as db:
            result = get_material_analytics(db, scope=self.unit_a_scope)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["arrived"], 1)

    def test_material_detail_outside_scope_is_not_returned(self):
        with self.Session() as db:
            with self.assertRaises(BusinessException):
                get_material_requirement(db, self.unit_b_material_id, scope=self.unit_a_scope)

    def test_territory_scope_is_applied_consistently_to_project_and_operation_analytics(self):
        territory_scope = DataScope(is_global=False, user_id=2, department="Territory A", reporting_units=("Territory A",))
        with self.Session() as db:
            projects = build_workover_analytics(db, WorkoverAnalyticsQuery(), scope=territory_scope)
            operations = build_workover_operation_dashboard(db, OperationAnalyticsQuery(), scope=territory_scope)

        self.assertEqual(projects.kpis.total_projects, 1)
        self.assertEqual(operations["total_sheets"], 1)


if __name__ == "__main__":
    unittest.main()
