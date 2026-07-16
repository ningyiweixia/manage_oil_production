import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class WorkoverOperationManagementContractTest(unittest.TestCase):
    def test_operation_router_exposes_independent_runtime_management_endpoints(self):
        router_source = (REPO_ROOT / "app/api/v1/router.py").read_text(encoding="utf-8")
        endpoint = REPO_ROOT / "app/api/v1/endpoints/workover_operations.py"

        self.assertIn("workover_operations", router_source)
        self.assertIn("include_router(workover_operations.router)", router_source)
        self.assertTrue(endpoint.exists())

        source = endpoint.read_text(encoding="utf-8")
        self.assertIn('prefix="/workover-operations"', source)
        self.assertIn('"/sheets/"', source)
        self.assertIn('"/priority-sheets"', source)
        self.assertIn('"/dashboard"', source)
        self.assertIn('"/a5-sync"', source)
        self.assertIn('"/sheets/{sheet_id}/progress"', source)
        self.assertIn("list_workover_operation_sheets", source)
        self.assertIn("build_workover_operation_dashboard", source)

    def test_operation_service_is_independent_from_contractor_dispatch_boundary(self):
        service = REPO_ROOT / "app/services/workover_operation_service.py"
        self.assertTrue(service.exists())
        source = service.read_text(encoding="utf-8")

        for symbol in (
            "list_workover_operation_sheets",
            "list_priority_operation_sheets",
            "build_workover_operation_dashboard",
            "update_workover_operation_progress",
            "sync_approved_projects_to_operation_sheets",
        ):
            self.assertIn(symbol, source)

        self.assertIn("workover_operation_sheet", source)
        self.assertIn("material_status", source)
        self.assertIn("completion_status", source)
        self.assertIn("a5_status", source)
        self.assertIn("closed_loop_status", source)
        self.assertIn("build_closed_loop_status", source)

    def test_legacy_contractor_operation_endpoints_delegate_to_operation_service(self):
        source = (REPO_ROOT / "app/api/v1/endpoints/contractors.py").read_text(encoding="utf-8")

        self.assertIn("workover_operation_service", source)
        self.assertIn("list_workover_operation_sheets", source)
        self.assertIn("update_workover_operation_progress", source)
        self.assertNotIn("from app.crud.contractor import (\n    create_contractor_capacity,\n    create_operation_sheet,", source)

    def test_seed_exposes_operation_management_as_independent_core_menu(self):
        source = (REPO_ROOT / "app/db/seed.py").read_text(encoding="utf-8")

        self.assertIn('"workover_operation"', source)
        self.assertIn('"/workover/operation-sheets"', source)
        self.assertIn('"修井运行管理"', source)
        self.assertIn('"workover_operation:read"', source)
        self.assertIn('"workover_operation:update"', source)
        self.assertIn('"workover_operation:dashboard"', source)
        self.assertIn('"workover_operation:a5_sync"', source)
        self.assertIn('menus_by_key["workover_operation"]', source)
        self.assertIn('("contractor_dispatch", None, "运力同步确认"', source)
        self.assertNotIn('("contractor", None, "承包商管理"', source)
        self.assertNotIn('("contractor_sheets"', source)
        process_role = source.split('"process_reviewer": {', 1)[1].split('},', 1)[0]
        for permission in ('"operation-sheet:dispatch"', '"contractor:read"', '"a5:sso"', '"workover_operation:a5_sync"'):
            self.assertIn(permission, process_role)
        scope_source = (REPO_ROOT / "app/services/data_scope_service.py").read_text(encoding="utf-8")
        self.assertIn('"process_reviewer"', scope_source)

    def test_runtime_menu_normalization_places_dispatch_before_operation(self):
        auth_source = (REPO_ROOT / "app/services/auth_service.py").read_text(encoding="utf-8")
        layout_source = (REPO_ROOT / "frontend/src/views/MainLayout.vue").read_text(encoding="utf-8")

        self.assertIn('"contractor_capacity": 22', auth_source)
        self.assertIn('"contractor_dispatch": 23', auth_source)
        self.assertIn('"workover_operation": 24', auth_source)
        self.assertIn('"contractor"', auth_source)
        self.assertIn('"/contractor/operation-sheets"', auth_source)
        self.assertIn("normalizeCoreMenuOrder", layout_source)
        self.assertIn("sort_order: 23", layout_source)
        self.assertIn("sort_order: 24", layout_source)

    def test_frontend_has_standalone_operation_management_page_and_api(self):
        view = REPO_ROOT / "frontend/src/views/WorkoverOperationManageView.vue"
        api = REPO_ROOT / "frontend/src/api/workoverOperation.ts"
        route_source = (REPO_ROOT / "frontend/src/router/index.ts").read_text(encoding="utf-8")
        layout_source = (REPO_ROOT / "frontend/src/views/MainLayout.vue").read_text(encoding="utf-8")
        cache_source = (REPO_ROOT / "frontend/src/utils/menuCache.ts").read_text(encoding="utf-8")

        self.assertTrue(view.exists())
        self.assertTrue(api.exists())
        self.assertIn("WorkoverOperationManageView", route_source)
        self.assertIn("/workover/operation-sheets", route_source)
        self.assertIn("/workover/operation-sheets", layout_source)
        self.assertIn("withWorkoverOperationMenu", layout_source)
        self.assertIn("2026-07-07-phase3-operation-menu", cache_source)

        view_source = view.read_text(encoding="utf-8")
        for text in ("修井运行表", "总工单", "待派工", "待A5审核", "已下发", "施工中", "已完工", "完工率", "井号", "区块", "承包商/队伍", "时间节点", "分配队伍", "统一同步 A5", "同步 A5 日报"):
            self.assertIn(text, view_source)
        self.assertIn("listWorkoverOperationSheets", view_source)
        self.assertIn("getWorkoverOperationDashboard", view_source)
        self.assertNotIn("updateWorkoverOperationProgress", view_source)
        self.assertNotIn("更新进度", view_source)
        self.assertIn("dispatchOperation", view_source)
        self.assertIn("A5与闭环信息", view_source)
        self.assertIn("closed_loop_status", view_source)
        self.assertNotIn('label="项目ID"', view_source)
        self.assertNotIn('label="A5同步"', view_source)
        self.assertNotIn('label="A5备注"', view_source)
        self.assertNotIn('label="更新时间"', view_source)

        api_source = api.read_text(encoding="utf-8")
        self.assertIn("/workover-operations/sheets/", api_source)
        self.assertIn("/workover-operations/priority-sheets", api_source)
        self.assertIn("/workover-operations/dashboard", api_source)
        self.assertIn("/workover-operations/a5-sync", api_source)
        self.assertNotIn("/workover-operations/sheets/${id}/progress", api_source)
        self.assertIn("closed_loop_status", api_source)

    def test_contractor_dispatch_page_no_longer_owns_operation_management(self):
        source = (REPO_ROOT / "frontend/src/views/ContractorDispatchView.vue").read_text(encoding="utf-8")

        self.assertNotIn("修井运行管理", source)
        self.assertNotIn("getOperationAnalytics", source)
        self.assertNotIn("listOperationSheets", source)
        self.assertNotIn("createOperationSheet", source)
        self.assertNotIn("A5同步", source)
        self.assertIn("承包商系统对接", source)


if __name__ == "__main__":
    unittest.main()
