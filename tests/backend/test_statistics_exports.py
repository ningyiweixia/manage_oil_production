import unittest
from unittest.mock import ANY, Mock, patch

from app.services import report_service
from app.services.statistics_analysis_service import StatisticsAnalysisQuery


class StatisticsExportsTest(unittest.TestCase):
    def test_statistics_analysis_exports_use_query_specific_payload(self):
        payload = {
            "overview_kpis": {"total_projects": 2, "pending_approvals": 1, "approval_rate": 50, "estimated_cost": 20, "operation_sheets": 3, "a5_anomalies": 1, "material_requirements": 4, "completion_records": 5, "data_quality_issues": 2},
            "operation_efficiency": {"total_sheets": 3, "dispatch_rate": 66.7, "completion_rate": 33.3, "team_workload": []},
            "a5_statistics": {"anomaly_total": 1, "special_process_total": 2, "anomaly_distribution": [], "process_distribution": [], "trend": {"days": [], "anomaly_counts": [], "process_counts": []}},
            "material_usage": {"total": 4, "arrived": 2, "used": 1, "usage_rate": 25.0},
            "completion_classification": {"total": 5, "by_measure_type": [{"measure_type": "pump_inspection", "count": 3}]},
            "data_quality_summary": {"checked_at": "2026-07-11T00:00:00", "total_issues": 2, "severity_counts": {"high": 1, "medium": 1, "low": 0}, "issues": [], "scope": {}},
            "trace_sources": ["workover_project_pool"],
            "chart_series": {},
        }
        query = StatisticsAnalysisQuery(well_no="W-1", team_name="Team A")

        with patch.object(report_service, "build_statistics_analysis", return_value=payload) as build:
            excel = report_service.export_statistics_analysis_excel(Mock(), query)
            word = report_service.export_statistics_analysis_word(Mock(), query)

        build.assert_called_with(ANY, query)
        self.assertEqual(excel[:4], b"PK\x03\x04")
        self.assertEqual(word[:4], b"PK\x03\x04")
        self.assertGreater(len(excel), 1024)
        self.assertGreater(len(word), 1024)

    def test_reports_router_exposes_statistics_analysis_exports(self):
        from pathlib import Path

        source = Path(__file__).resolve().parents[2] / "app/api/v1/endpoints/reports.py"
        text = source.read_text(encoding="utf-8")
        self.assertIn('"/statistics-analysis.xlsx"', text)
        self.assertIn('"/statistics-analysis.docx"', text)
        self.assertIn("export_statistics_analysis_excel", text)
        self.assertIn("export_statistics_analysis_word", text)


if __name__ == "__main__":
    unittest.main()
