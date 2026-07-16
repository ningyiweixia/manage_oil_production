import asyncio
import unittest
from datetime import date

from app.services.a5_adapter import ExternalIntegrationError, MockA5Adapter


class A5AdapterTest(unittest.TestCase):
    def test_normal_mock_scenario_is_deterministic_and_covers_all_feeds(self):
        async def run():
            adapter = MockA5Adapter("normal")
            first = await adapter.fetch_daily_reports(date(2026, 7, 16))
            second = await adapter.fetch_daily_reports(date(2026, 7, 16))
            anomalies = await adapter.fetch_anomalies(date(2026, 7, 16))
            processes = await adapter.fetch_process_progress(date(2026, 7, 16))
            return first, second, anomalies, processes

        first, second, anomalies, processes = asyncio.run(run())

        self.assertEqual(first, second)
        self.assertEqual(first[0]["operation_no"], "OP-MOCK-001")
        self.assertEqual(anomalies[0]["anomaly_type"], "PRESSURE_HIGH")
        self.assertEqual(processes[0]["process_type"], "ACIDIZING")

    def test_empty_scenario_returns_no_records(self):
        reports = asyncio.run(MockA5Adapter("empty").fetch_daily_reports(date(2026, 7, 16)))
        self.assertEqual(reports, [])

    def test_timeout_scenario_is_classified_for_retry(self):
        with self.assertRaisesRegex(ExternalIntegrationError, "TIMEOUT"):
            asyncio.run(MockA5Adapter("timeout").fetch_daily_reports(date(2026, 7, 16)))


if __name__ == "__main__":
    unittest.main()
