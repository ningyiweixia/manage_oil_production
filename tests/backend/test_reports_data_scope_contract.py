import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class ReportsDataScopeContractTest(unittest.TestCase):
    def test_statistics_and_exports_build_scope_from_current_user(self):
        source = (REPO_ROOT / "app/api/v1/endpoints/reports.py").read_text(encoding="utf-8")

        self.assertIn("build_data_scope", source)
        self.assertGreaterEqual(source.count("scope=build_data_scope(current_user)"), 6)


if __name__ == "__main__":
    unittest.main()
