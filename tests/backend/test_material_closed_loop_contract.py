import unittest
from unittest.mock import Mock

from app.models.material import MaterialRequirement, MaterialRequirementStatus


class MaterialClosedLoopContractTest(unittest.TestCase):
    def test_material_schema_exposes_closed_loop_fields(self):
        from app.schemas.material import MaterialRequirementOut

        expected_fields = {
            "plan_no",
            "warehouse",
            "supplier_or_team",
            "planned_quantity",
            "delivered_quantity",
            "arrived_quantity",
            "used_quantity",
            "delivery_contact",
            "delivery_phone",
            "expected_arrival_at",
            "exception_reason",
            "source_platform",
            "external_material_id",
        }

        self.assertTrue(expected_fields.issubset(MaterialRequirementOut.model_fields))

    def test_quantity_validation_rejects_usage_greater_than_arrival(self):
        from app.crud.material import validate_material_quantities

        item = MaterialRequirement(
            well_no="JH-001",
            material_name="油管",
            quantity=10,
            unit="件",
            planned_quantity=10,
            delivered_quantity=10,
            arrived_quantity=8,
            used_quantity=9,
        )

        with self.assertRaisesRegex(Exception, "使用数量不能大于到场数量"):
            validate_material_quantities(item)

    def test_exception_reason_is_counted_without_changing_rollup_status(self):
        from app.crud.material import apply_material_rollup_to_operation_sheet, build_material_analytics
        from app.models.workover import WorkoverOperationSheet

        sheet = WorkoverOperationSheet(project_id=1, operation_no="OP-MAT-001")
        sheet.progress_detail = {}
        items = [
            Mock(status=MaterialRequirementStatus.ARRIVED, requirement_type=Mock(value="NORMAL"), exception_reason="配送延误"),
            Mock(status=MaterialRequirementStatus.USED, requirement_type=Mock(value="EMERGENCY"), exception_reason=None),
        ]

        apply_material_rollup_to_operation_sheet(sheet, items)
        summary = build_material_analytics(items)

        self.assertEqual(sheet.progress_detail["material"]["status"], "ARRIVED")
        self.assertEqual(summary["exception_count"], 1)
        self.assertEqual(summary["usage_rate"], 50.0)

    def test_material_permissions_match_existing_roles(self):
        from app.db import seed

        self.assertIn("material:create", seed.ROLE_PERMISSION_CODES["contractor_operator"])
        self.assertIn("material:update", seed.ROLE_PERMISSION_CODES["contractor_operator"])
        self.assertIn("material:update", seed.ROLE_PERMISSION_CODES["project_pool_admin"])
        self.assertIn("material:update", seed.ROLE_PERMISSION_CODES["business_reviewer"])
        self.assertNotIn("material:create", seed.ROLE_PERMISSION_CODES["base_entry_clerk"])

    def test_contractor_status_actions_are_limited_to_field_confirmation(self):
        from app.api.v1.endpoints.materials import ensure_material_update_allowed

        contractor = Mock(is_superuser=False, roles=[Mock(code="contractor_operator")])
        manager = Mock(is_superuser=False, roles=[Mock(code="project_pool_admin")])

        ensure_material_update_allowed(contractor, MaterialRequirementStatus.ARRIVED)
        ensure_material_update_allowed(contractor, MaterialRequirementStatus.USED)
        ensure_material_update_allowed(manager, MaterialRequirementStatus.APPROVED)

        with self.assertRaisesRegex(Exception, "承包商只能确认物料到场或使用"):
            ensure_material_update_allowed(contractor, MaterialRequirementStatus.APPROVED)


if __name__ == "__main__":
    unittest.main()
