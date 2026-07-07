import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class SystemSupportContractTest(unittest.TestCase):
    def test_backend_exposes_support_overview_endpoint_and_schema(self):
        router = (REPO_ROOT / "app/api/v1/endpoints/rbac.py").read_text(encoding="utf-8")
        schemas = (REPO_ROOT / "app/schemas/rbac.py").read_text(encoding="utf-8")
        service = (REPO_ROOT / "app/services/rbac_service.py").read_text(encoding="utf-8")

        self.assertIn('"/system/support-overview"', router)
        self.assertIn('require_permission("system:support:read")', router)
        self.assertIn("SystemSupportOverviewOut", schemas)
        self.assertIn("build_system_support_overview", service)

        for section in (
            "runtime_monitoring",
            "security_controls",
            "audit_traceability",
            "backup_recovery",
            "message_alerts",
            "data_scope",
        ):
            self.assertIn(section, schemas)
            self.assertIn(section, service)

    def test_seed_registers_support_menu_and_permission(self):
        seed = (REPO_ROOT / "app/db/seed.py").read_text(encoding="utf-8")

        self.assertIn("system_support", seed)
        self.assertIn("/system/support", seed)
        self.assertIn("system:support:read", seed)
        self.assertIn("基础支撑", seed)

    def test_frontend_system_admin_has_support_tab_and_api(self):
        view = (REPO_ROOT / "frontend/src/views/SystemAdminView.vue").read_text(encoding="utf-8")
        api = (REPO_ROOT / "frontend/src/api/rbac.ts").read_text(encoding="utf-8")
        router = (REPO_ROOT / "frontend/src/router/index.ts").read_text(encoding="utf-8")
        layout = (REPO_ROOT / "frontend/src/views/MainLayout.vue").read_text(encoding="utf-8")
        menu_cache = (REPO_ROOT / "frontend/src/utils/menuCache.ts").read_text(encoding="utf-8")

        self.assertIn("基础支撑", view)
        self.assertIn("运行监控", view)
        self.assertIn("接口安全", view)
        self.assertIn("数据权限", view)
        self.assertIn("敏感操作审计", view)
        self.assertIn("备份与恢复", view)
        self.assertIn("消息提醒", view)
        self.assertIn("getSystemSupportOverview", view)
        self.assertIn("getSystemSupportOverview", api)
        self.assertIn("/system/support-overview", api)
        self.assertIn("/system/support", router)
        self.assertIn("/system/support", layout)
        self.assertIn("withSystemSupportMenu", layout)
        self.assertIn("system:support:read", layout)
        self.assertIn("system-support-menu", menu_cache)


if __name__ == "__main__":
    unittest.main()
