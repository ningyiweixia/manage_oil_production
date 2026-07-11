import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendAnalyticsContractTest(unittest.TestCase):
    def test_dashboard_exposes_data_quality_alert_workflow(self):
        dashboard = (REPO_ROOT / "frontend/src/views/AnalyticsDashboard.vue").read_text(encoding="utf-8")
        alerts_api = (REPO_ROOT / "frontend/src/api/analyticsAlerts.ts").read_text(encoding="utf-8")

        for symbol in (
            "analyticsAlerts",
            "loadAlerts",
            "createAlertFromIssue",
            "startAlertHandling",
            "closeAlert",
            "数据质量待办",
            "纳入待办",
            "开始处理",
            "关闭待办",
        ):
            self.assertIn(symbol, dashboard)

        for symbol in (
            "listAnalyticsAlerts",
            "createAnalyticsAlert",
            "updateAnalyticsAlert",
            "/analytics-alerts",
        ):
            self.assertIn(symbol, alerts_api)


if __name__ == "__main__":
    unittest.main()
