import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class FrontendMaterialClosedLoopContractTest(unittest.TestCase):
    def test_material_view_uses_readable_closed_loop_labels(self):
        source = (REPO_ROOT / "frontend/src/views/MaterialManageView.vue").read_text(encoding="utf-8")

        for label in [
            "物料需求台账",
            "物料配送跟踪",
            "需求数量",
            "计划数量",
            "出库数量",
            "到场数量",
            "使用数量",
            "异常情况",
            "预计到场",
        ]:
            self.assertIn(label, source)

        self.assertNotIn("鐗", source)
        self.assertNotIn("浜曞彿", source)

    def test_material_view_exposes_status_actions(self):
        source = (REPO_ROOT / "frontend/src/views/MaterialManageView.vue").read_text(encoding="utf-8")

        for action in ["审核", "计划", "出库", "到场", "使用", "取消"]:
            self.assertIn(action, source)

    def test_material_api_types_include_closed_loop_fields(self):
        source = (REPO_ROOT / "frontend/src/api/material.ts").read_text(encoding="utf-8")

        for field in [
            "planned_quantity",
            "delivered_quantity",
            "arrived_quantity",
            "used_quantity",
            "exception_reason",
            "source_platform",
            "usage_rate",
        ]:
            self.assertIn(field, source)


if __name__ == "__main__":
    unittest.main()
