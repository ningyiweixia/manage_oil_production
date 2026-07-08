from pathlib import Path
import unittest
from unittest.mock import Mock

from app.core.exceptions import BusinessException
from app.models.workover import ProjectPoolStatus


REPO_ROOT = Path(__file__).resolve().parents[2]


class ApprovalWorkflowContractTest(unittest.TestCase):
    def test_service_defines_node_role_rules_and_reject_requires_comment(self):
        from app.services.approval_workflow_service import (
            APPROVAL_NODE_RULES,
            ApprovalActionCode,
            ApprovalDecision,
            ensure_node_actor_allowed,
            validate_approval_decision,
        )

        self.assertIn(ProjectPoolStatus.PENDING_GEOLOGY_VERIFY, APPROVAL_NODE_RULES)
        self.assertIn(ProjectPoolStatus.PENDING_PROCESS_VERIFY, APPROVAL_NODE_RULES)
        self.assertIn("geology_reviewer", APPROVAL_NODE_RULES[ProjectPoolStatus.PENDING_GEOLOGY_VERIFY].role_codes)
        self.assertIn("process_reviewer", APPROVAL_NODE_RULES[ProjectPoolStatus.PENDING_PROCESS_VERIFY].role_codes)

        process_user = Mock(is_superuser=False, roles=[Mock(code="process_reviewer", is_active=True)])
        geology_user = Mock(is_superuser=False, roles=[Mock(code="geology_reviewer", is_active=True)])
        ensure_node_actor_allowed(geology_user, ProjectPoolStatus.PENDING_GEOLOGY_VERIFY)
        with self.assertRaises(BusinessException):
            ensure_node_actor_allowed(process_user, ProjectPoolStatus.PENDING_GEOLOGY_VERIFY)

        with self.assertRaises(BusinessException):
            validate_approval_decision(ApprovalDecision(action=ApprovalActionCode.REJECT, comment=""))

    def test_approval_router_exposes_tasks_process_and_timeline_endpoints(self):
        router_source = (REPO_ROOT / "app/api/v1/router.py").read_text(encoding="utf-8")
        endpoint_source = (REPO_ROOT / "app/api/v1/endpoints/approvals.py").read_text(encoding="utf-8")

        self.assertIn("approvals", router_source)
        self.assertIn("include_router(approvals.router)", router_source)
        self.assertIn('"/approvals/tasks"', endpoint_source)
        self.assertIn('"/approvals/{business_type}/{business_id}/timeline"', endpoint_source)
        self.assertIn('"/approvals/workover-project-pools/{project_id}"', endpoint_source)

    def test_legacy_project_status_endpoint_delegates_to_approval_service(self):
        source = (REPO_ROOT / "app/api/v1/endpoints/workover_project_pools.py").read_text(encoding="utf-8")

        self.assertIn("process_workover_project_approval", source)
        self.assertNotIn("patch_project_status(", source)

    def test_seed_exposes_approval_permissions_and_dedicated_reviewer_roles(self):
        from app.db import seed

        permissions = {code for code, *_ in seed.PERMISSION_DEFINITIONS}
        roles = {code for code, *_ in seed.ROLE_DEFINITIONS}

        self.assertIn("approval:task:read", permissions)
        self.assertIn("approval:process", permissions)
        self.assertIn("approval:timeline:read", permissions)
        self.assertIn("geology_reviewer", roles)
        self.assertIn("process_reviewer", roles)
        self.assertIn("production_command_reviewer", roles)

    def test_frontend_approval_workbench_uses_approval_api_and_tabs(self):
        source = (REPO_ROOT / "frontend/src/views/ApprovalWorkbench.vue").read_text(encoding="utf-8")
        api_source = (REPO_ROOT / "frontend/src/api/approval.ts").read_text(encoding="utf-8")

        for text in ("我的待办", "已处理", "已驳回", "已通过", "审批轨迹", "停留时长"):
            self.assertIn(text, source)
        self.assertIn("listApprovalTasks", source)
        self.assertIn("processProjectApproval", source)
        self.assertIn("getApprovalTimeline", source)
        self.assertIn("/approvals/tasks", api_source)
        self.assertIn("/approvals/workover-project-pools", api_source)
        self.assertIn("/approvals/${businessType}/${businessId}/timeline", api_source)

    def test_frontend_approval_workbench_syncs_scope_card_counts_from_task_totals(self):
        source = (REPO_ROOT / "frontend/src/views/ApprovalWorkbench.vue").read_text(encoding="utf-8")

        self.assertIn("scopeTotals", source)
        self.assertIn("loadScopeTotals", source)
        for scope in ("pending", "processed", "rejected", "approved"):
            self.assertIn(f"{scope}: 0", source)
            self.assertIn(f"scopeTotals.{scope}", source)
            self.assertIn(f"scope: '{scope}'", source)
        self.assertNotIn("activeScope.value === 'pending' ? total.value : 0", source)

    def test_project_pool_ledger_does_not_directly_approve_or_reject(self):
        source = (REPO_ROOT / "frontend/src/views/ProjectPoolLedgerView.vue").read_text(encoding="utf-8")

        self.assertNotIn("patchProjectStatus", source)
        self.assertNotIn("通过</el-button>", source)
        self.assertNotIn("驳回</el-button>", source)


if __name__ == "__main__":
    unittest.main()
