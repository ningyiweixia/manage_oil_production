import asyncio
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.crud.material import get_material_requirement
from app.core.exceptions import BusinessException
from app.db.base import Base
from app.models import *  # noqa: F401,F403
from app.models.material import MaterialRequirement, MaterialRequirementStatus, MaterialRequirementType
from app.services.material_external_adapter import (
    MockMaterialExternalAdapter,
    apply_external_material_event,
    get_material_external_adapter,
)


class MaterialExternalAdapterTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        with self.Session() as db:
            requirement = MaterialRequirement(
                well_no="WELL-001", material_name="Pipe", quantity=5, unit="item",
                external_material_id="MAT-MOCK-001", source_platform="mock_material",
                status=MaterialRequirementStatus.APPROVED, requirement_type=MaterialRequirementType.NORMAL,
            )
            db.add(requirement)
            db.commit()
            self.requirement_id = requirement.id

    def test_mock_plan_event_advances_only_the_next_legal_state(self):
        event = asyncio.run(MockMaterialExternalAdapter("normal").fetch_events())[0]
        with self.Session() as db:
            result = apply_external_material_event(db, event)
            requirement = get_material_requirement(db, self.requirement_id)

        self.assertFalse(result.duplicate)
        self.assertEqual(requirement.status, MaterialRequirementStatus.PLANNED)
        self.assertEqual(requirement.planned_quantity, 5)

    def test_replayed_material_event_does_not_apply_quantities_twice(self):
        event = asyncio.run(MockMaterialExternalAdapter("normal").fetch_events())[0]
        with self.Session() as db:
            apply_external_material_event(db, event)
            replay = apply_external_material_event(db, event)
            requirement = get_material_requirement(db, self.requirement_id)

        self.assertTrue(replay.duplicate)
        self.assertEqual(requirement.planned_quantity, 5)

    def test_mock_mode_exposes_a_fetchable_adapter(self):
        adapter = get_material_external_adapter("mock", "empty")

        self.assertEqual(asyncio.run(adapter.fetch_events()), [])

    def test_http_mode_returns_a_typed_configuration_error(self):
        with self.assertRaises(BusinessException):
            get_material_external_adapter("http")


if __name__ == "__main__":
    unittest.main()
