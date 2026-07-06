import unittest

from app.db import seed


class Phase1DemoReadinessTest(unittest.TestCase):
    def test_seed_menus_have_phase1_entries_and_readable_titles(self):
        menus = {code: title for code, _parent, title, *_rest in seed.MENU_DEFINITIONS}

        self.assertEqual(menus["workover_project_pool"], "项目池台账")
        self.assertEqual(menus["analytics"], "统计分析")
        self.assertEqual(menus["material"], "物料管理")
        self.assertEqual(menus["material_requirements"], "物料需求")
        self.assertEqual(menus["material_delivery"], "物料配送")
        self.assertEqual(menus["completion"], "完井台账")
        self.assertEqual(menus["system_logs"], "操作日志")

    def test_seed_roles_and_permissions_have_readable_names(self):
        roles = {code: name for code, name, _description in seed.ROLE_DEFINITIONS}
        permissions = {code: name for code, name, *_rest in seed.PERMISSION_DEFINITIONS}

        self.assertEqual(roles["super_admin"], "超级管理员")
        self.assertEqual(roles["project_pool_admin"], "项目池管理员")
        self.assertEqual(roles["contractor_operator"], "承包商操作员")
        self.assertEqual(permissions["material:read"], "查看物料需求")
        self.assertEqual(permissions["completion:read"], "查看完井台账")
        self.assertEqual(permissions["system:operation_log:read"], "查看操作日志")

    def test_seed_dictionaries_have_phase1_readable_names(self):
        dictionary_items = {
            (dict_type, value): label
            for dict_type, label, value in seed.DICTIONARY_DEFINITIONS
        }

        self.assertEqual(dictionary_items[("material_status", "PENDING")], "待处理")
        self.assertEqual(dictionary_items[("material_status", "DELIVERED")], "已出库")
        self.assertEqual(dictionary_items[("material_status", "ARRIVED")], "已到场")
        self.assertEqual(dictionary_items[("material_status", "USED")], "已使用")
        self.assertEqual(dictionary_items[("system_menu", "completion")], "完井台账")


if __name__ == "__main__":
    unittest.main()
