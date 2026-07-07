import unittest
from pathlib import Path
from unittest.mock import Mock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]


class StatisticsAnalysisContractTest(unittest.TestCase):
    def test_statistics_service_matches_plan_required_sections(self):
        service = REPO_ROOT / "app/services/statistics_analysis_service.py"
        self.assertTrue(service.exists())
        source = service.read_text(encoding="utf-8")

        for symbol in (
            "build_statistics_analysis",
            "StatisticsAnalysisQuery",
            "report_key_data",
            "completion_classification",
            "a5_statistics",
            "material_usage",
            "operation_efficiency",
            "trace_sources",
        ):
            self.assertIn(symbol, source)

        for query_field in ("well_no", "report_unit", "measure_type", "team_name", "process_type", "material_status"):
            self.assertIn(query_field, source)

    def test_reports_router_exposes_statistics_analysis_endpoint(self):
        source = (REPO_ROOT / "app/api/v1/endpoints/reports.py").read_text(encoding="utf-8")

        self.assertIn('"/statistics-analysis"', source)
        self.assertIn("StatisticsAnalysisQuery", source)
        self.assertIn("build_statistics_analysis", source)
        self.assertIn('require_permission("report:read")', source)

    def test_statistics_analysis_aggregates_a5_completion_material_and_traceability(self):
        from app.services import statistics_analysis_service as service

        db = Mock()
        query = service.StatisticsAnalysisQuery(
            well_no="CY2",
            report_unit="采油一队",
            measure_type="pump_inspection",
            team_name="作业一队",
            process_type="检泵",
            material_status="ARRIVED",
        )
        workover = Mock()
        workover.kpis.total_projects = 10
        workover.kpis.pending_approvals = 2
        workover.kpis.approval_rate = 80
        workover.kpis.estimated_cost = 120
        workover.measure_distribution = [Mock(name="pump_inspection", value=4)]
        a5 = Mock(
            anomaly_total=3,
            special_process_total=5,
            anomaly_distribution=[],
            process_distribution=[],
        )

        with (
            patch.object(service, "build_workover_analytics", return_value=workover),
            patch.object(service, "build_workover_operation_dashboard", return_value={"total_sheets": 6, "completion_rate": 50, "team_workload": [{"team_name": "作业一队", "sheet_count": 3}]}),
            patch.object(service, "get_material_analytics", return_value={"total": 7, "arrived": 4, "used": 2, "emergency_count": 1}),
            patch.object(service, "get_completion_analytics", return_value={"total": 8, "by_measure_type": [{"measure_type": "pump_inspection", "count": 5}]}),
            patch.object(service, "build_a5_analytics", return_value=a5),
        ):
            result = service.build_statistics_analysis(db, query)

        self.assertEqual(result["report_key_data"]["total_projects"], 10)
        self.assertEqual(result["a5_statistics"]["anomaly_total"], 3)
        self.assertEqual(result["completion_classification"]["total"], 8)
        self.assertEqual(result["material_usage"]["arrived"], 4)
        self.assertIn("workover_project_pool", result["trace_sources"])
        self.assertEqual(result["query"]["team_name"], "作业一队")

    def test_frontend_dashboard_uses_statistics_analysis_contract_and_plan_labels(self):
        dashboard = (REPO_ROOT / "frontend/src/views/AnalyticsDashboard.vue").read_text(encoding="utf-8")
        reports_api = (REPO_ROOT / "frontend/src/api/reports.ts").read_text(encoding="utf-8")

        for text in (
            "数据统计分析",
            "报告关键数据",
            "完井分类台账",
            "A5数据统计",
            "物料使用统计",
            "多条件查询",
            "统计结果可追溯",
        ):
            self.assertIn(text, dashboard)

        for field in ("wellNoFilter", "reportUnitFilter", "teamNameFilter", "processTypeFilter", "materialStatusFilter"):
            self.assertIn(field, dashboard)

        self.assertIn("getStatisticsAnalysis", reports_api)
        self.assertIn("/reports/statistics-analysis", reports_api)


if __name__ == "__main__":
    unittest.main()
