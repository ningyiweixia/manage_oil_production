import unittest
from unittest.mock import Mock, patch

from app.models.material import MaterialRequirementStatus
from app.models.workover import WorkoverOperationSheet
from app.schemas.rbac import OperationLogOut


class RemainingOptimizationContractsTest(unittest.TestCase):
    def test_operation_log_schema_exposes_trace_id_for_audit_tracking(self):
        self.assertIn("trace_id", OperationLogOut.model_fields)

    def test_report_service_builds_integrated_delivery_summary(self):
        from app.services import report_service

        project_analytics = Mock()
        project_analytics.kpis.total_projects = 8
        project_analytics.kpis.pending_approvals = 2
        project_analytics.kpis.approval_rate = 75.0
        project_analytics.kpis.estimated_cost = 120.5
        project_analytics.status_counts = []
        project_analytics.measure_distribution = []

        with (
            patch.object(report_service, "build_workover_analytics", return_value=project_analytics),
            patch.object(report_service, "get_operation_analytics", return_value={"total_sheets": 5, "dispatch_rate": 60.0, "completion_rate": 20.0, "team_workload": []}),
            patch.object(report_service, "get_material_analytics", return_value={"total": 4, "delivered": 2, "arrived": 1, "used": 1, "emergency_count": 1}),
            patch.object(report_service, "get_completion_analytics", return_value={"total": 3, "by_measure_type": [{"measure_type": "pump_inspection", "count": 2}]}),
        ):
            summary = report_service.build_delivery_summary(Mock())

        self.assertEqual(summary["projects"]["total"], 8)
        self.assertEqual(summary["operations"]["total_sheets"], 5)
        self.assertEqual(summary["materials"]["emergency_count"], 1)
        self.assertEqual(summary["completions"]["total"], 3)

    def test_project_pool_scope_limits_non_privileged_users_to_department_or_owner(self):
        from app.services.data_scope_service import project_pool_scope_predicate

        user = Mock()
        user.id = 7
        user.department = "采油一队"
        user.is_superuser = False
        user.roles = [Mock(code="base_entry_clerk")]

        predicate = project_pool_scope_predicate(user)

        self.assertEqual(predicate["created_by_id"], 7)
        self.assertEqual(predicate["department"], "采油一队")

    def test_material_status_rollup_updates_operation_sheet_detail(self):
        from app.crud.material import apply_material_rollup_to_operation_sheet

        sheet = WorkoverOperationSheet(project_id=1, operation_no="OP-TEST")
        sheet.progress_detail = {"existing": {"keep": True}}

        apply_material_rollup_to_operation_sheet(
            sheet,
            [
                Mock(status=MaterialRequirementStatus.APPROVED),
                Mock(status=MaterialRequirementStatus.ARRIVED),
                Mock(status=MaterialRequirementStatus.USED),
            ],
        )

        self.assertEqual(sheet.progress_detail["existing"], {"keep": True})
        self.assertEqual(sheet.progress_detail["material"]["status"], "ARRIVED")
        self.assertEqual(sheet.progress_detail["material"]["total"], 3)
        self.assertEqual(sheet.progress_detail["material"]["counts"]["USED"], 1)

    def test_material_fixed_routes_are_registered_before_dynamic_detail_route(self):
        from app.api.v1.endpoints.materials import router

        paths = [route.path for route in router.routes]

        self.assertLess(paths.index("/materials/analytics/summary"), paths.index("/materials/{req_id}"))

    def test_completion_fixed_routes_are_registered_before_dynamic_detail_route(self):
        from app.api.v1.endpoints.completions import router

        paths = [route.path for route in router.routes]

        self.assertLess(paths.index("/well-completions/analytics/summary"), paths.index("/well-completions/{record_id}"))


if __name__ == "__main__":
    unittest.main()
