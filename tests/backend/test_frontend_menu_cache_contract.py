import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendMenuCacheContractTest(unittest.TestCase):
    def test_menu_cache_version_is_centralized(self):
        source = (REPO_ROOT / "frontend/src/utils/menuCache.ts").read_text(encoding="utf-8")

        self.assertIn("MENU_SCHEMA_VERSION", source)
        self.assertIn("storeSessionMenus", source)
        self.assertIn("loadCachedMenus", source)

    def test_login_stores_menu_cache_version(self):
        source = (REPO_ROOT / "frontend/src/views/LoginView.vue").read_text(encoding="utf-8")

        self.assertIn("storeSessionMenus", source)
        self.assertNotIn("localStorage.setItem('menus'", source)

    def test_main_layout_refreshes_menus_from_current_user(self):
        source = (REPO_ROOT / "frontend/src/views/MainLayout.vue").read_text(encoding="utf-8")

        self.assertIn("getCurrentUser", source)
        self.assertIn("refreshSessionMenus", source)
        self.assertIn("loadCachedMenus", source)


if __name__ == "__main__":
    unittest.main()
