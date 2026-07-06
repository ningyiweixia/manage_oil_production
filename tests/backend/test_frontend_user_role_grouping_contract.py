import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendUserRoleGroupingContractTest(unittest.TestCase):
    def test_user_management_groups_users_by_role_and_supports_sorting(self):
        source = (REPO_ROOT / "frontend/src/views/SystemAdminView.vue").read_text(encoding="utf-8")

        self.assertIn("按角色分组", source)
        self.assertIn("系统管理信息总览", source)
        self.assertIn("人员总数", source)
        self.assertIn("角色总数", source)
        self.assertIn("权限总数", source)
        self.assertIn("菜单总数", source)
        self.assertIn("userRoleGroups", source)
        self.assertIn("systemAdminStats", source)
        self.assertIn("sortUsersForRole", source)
        self.assertIn("userSortMode", source)
        self.assertIn("首字母升序", source)
        self.assertIn("首字母降序", source)
        self.assertIn("录入时间从新到旧", source)
        self.assertIn("录入时间从旧到新", source)
        self.assertIn("created_at", source)

    def test_system_admin_detail_tables_are_loaded_independently(self):
        source = (REPO_ROOT / "frontend/src/views/SystemAdminView.vue").read_text(encoding="utf-8")

        self.assertIn("Promise.allSettled", source)
        self.assertNotIn("Promise.all([", source)
        self.assertIn("权限明细", source)
        self.assertIn("permissionStats", source)
        self.assertIn('prop="description" label="说明"', source)
        self.assertIn('description="暂无权限数据"', source)


if __name__ == "__main__":
    unittest.main()
