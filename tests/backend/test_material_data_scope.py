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


class MaterialDataScopeTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        with self.Session() as db:
            material_ids = []
            for unit, suffix in (("Unit A", "A"), ("Unit B", "B")):
                project = WorkoverProjectPool(
                    well_no=f"WELL-{suffix}", report_unit=unit, production_priority=1,
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


if __name__ == "__main__":
    unittest.main()
