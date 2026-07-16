import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendIntegrationModesContractTest(unittest.TestCase):
    def test_a5_view_displays_adapter_mode_from_sync_status(self):
        api = (REPO_ROOT / "frontend/src/api/a5.ts").read_text(encoding="utf-8")
        view = (REPO_ROOT / "frontend/src/views/A5IntegrationView.vue").read_text(encoding="utf-8")

        self.assertIn("adapter_mode", api)
        self.assertIn("adapter_mode", view)
        self.assertIn("模拟接口", view)
        self.assertIn("正式接口", view)


if __name__ == "__main__":
    unittest.main()
