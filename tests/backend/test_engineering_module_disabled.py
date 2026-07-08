import unittest
from pathlib import Path

from app.db import seed


REPO_ROOT = Path(__file__).resolve().parents[2]


class EngineeringModuleDisabledTest(unittest.TestCase):
    def test_seed_no_longer_exposes_engineering_menu_or_permissions(self):
        menu_routes = {route_path for *_prefix, route_path, _component, _icon, _sort in seed.MENU_DEFINITIONS}
        permission_codes = {code for code, *_ in seed.PERMISSION_DEFINITIONS}
        dictionary_items = {(dict_type, item_value) for dict_type, _label, item_value in seed.DICTIONARY_DEFINITIONS}

        self.assertNotIn("/engineering", menu_routes)
        self.assertNotIn("/engineering/designs", menu_routes)
        self.assertFalse(any(code.startswith("engineering:") for code in permission_codes))
        self.assertNotIn(("system_menu", "engineering"), dictionary_items)

    def test_api_router_does_not_register_engineering_endpoint(self):
        source = (REPO_ROOT / "app/api/v1/router.py").read_text(encoding="utf-8")

        self.assertNotIn("engineering,", source)
        self.assertNotIn("include_router(engineering.router)", source)

    def test_frontend_routes_and_fallback_do_not_show_engineering(self):
        router_source = (REPO_ROOT / "frontend/src/router/index.ts").read_text(encoding="utf-8")
        layout_source = (REPO_ROOT / "frontend/src/views/MainLayout.vue").read_text(encoding="utf-8")

        self.assertNotIn("EngineeringDesignView", router_source)
        self.assertNotIn("/engineering/designs", router_source)
        self.assertNotIn("/engineering/designs", layout_source)
        self.assertNotIn("工程设计管理", layout_source)


if __name__ == "__main__":
    unittest.main()
