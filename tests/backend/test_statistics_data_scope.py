import unittest
from unittest.mock import Mock, patch

from app.services.data_scope_service import DataScope
from app.services.statistics_analysis_service import StatisticsAnalysisQuery, build_statistics_analysis


class StatisticsDataScopeTest(unittest.TestCase):
    def test_statistics_passes_scope_to_materials_and_reporting_unit_to_all_facts(self):
        scope = DataScope(is_global=False, user_id=7, department="Unit A", reporting_units=("Unit A",))
        workover = Mock()
        workover.kpis = Mock(total_projects=0, pending_approvals=0, approval_rate=0, estimated_cost=0)
        workover.status_counts = []
        workover.measure_distribution = []
        workover.heatmap = Mock(model_dump=lambda **_: {})
        workover.trend = Mock(model_dump=lambda **_: {})
        a5 = Mock(anomaly_total=0, special_process_total=0, anomaly_distribution=[], process_distribution=[], trend=[])

        with (
            patch("app.services.statistics_analysis_service.build_workover_analytics", return_value=workover) as project_adapter,
            patch("app.services.statistics_analysis_service.build_workover_operation_dashboard", return_value={"total_sheets": 0}) as operation_adapter,
            patch("app.services.statistics_analysis_service.get_material_analytics", return_value={"total": 0}) as material_adapter,
            patch("app.services.statistics_analysis_service.get_completion_analytics", return_value={"total": 0, "by_measure_type": []}) as completion_adapter,
            patch("app.services.statistics_analysis_service.build_a5_analytics", return_value=a5),
            patch("app.services.statistics_analysis_service.build_data_quality_summary", return_value=Mock(model_dump=lambda **_: {"total_issues": 0})),
            patch("app.services.statistics_analysis_service.build_integration_status", return_value={}),
        ):
            build_statistics_analysis(Mock(), StatisticsAnalysisQuery(), scope=scope)

        self.assertEqual(project_adapter.call_args.args[1].report_unit, "Unit A")
        self.assertEqual(operation_adapter.call_args.args[1].report_unit, "Unit A")
        self.assertEqual(material_adapter.call_args.kwargs["scope"], scope)
        self.assertEqual(completion_adapter.call_args.args[1].report_unit, "Unit A")


if __name__ == "__main__":
    unittest.main()
