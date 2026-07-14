import os
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("POSTGRES_PASSWORD", "test-postgres-password")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.exceptions import BusinessException
from app.core.security import create_token
from app.core.status_codes import A5_LINK_FAILED
from app.db.session import get_db
from main import app


class ModuleApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.user = SimpleNamespace(id=77, is_active=True, is_superuser=False, roles=[])
        token, _ = create_token("77", "access", timedelta(minutes=5))
        self.headers = {"Authorization": f"Bearer {token}"}
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_db] = lambda: SimpleNamespace()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_legacy_read_permission_can_use_new_workover_api(self):
        with patch("app.api.deps.get_user_permission_codes", return_value={"operation-sheet:read"}), patch(
            "app.api.v1.endpoints.workover_operations.list_workover_operation_sheets",
            return_value=([], 0),
        ):
            response = TestClient(app, raise_server_exceptions=False).get(
                "/api/v1/workover-operations/sheets/", headers=self.headers
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["items"], [])

    def test_workover_api_rejects_unrelated_permission(self):
        with patch("app.api.deps.get_user_permission_codes", return_value={"contractor:read"}):
            response = TestClient(app, raise_server_exceptions=False).get(
                "/api/v1/workover-operations/sheets/", headers=self.headers
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], 40300)

    def test_new_dispatch_permission_is_accepted_and_token_failure_is_atomic(self):
        with patch("app.api.deps.get_user_permission_codes", return_value={"workover_operation:dispatch"}), patch(
            "app.api.v1.endpoints.contractors.get_workover_operation_sheet",
            return_value={"operation_no": "OP-API-1", "project_well_no": "WELL-API-1"},
        ), patch(
            "app.api.v1.endpoints.contractors.generate_sso_token",
            side_effect=BusinessException(A5_LINK_FAILED, "A5令牌生成失败"),
        ), patch("app.api.v1.endpoints.contractors.dispatch_operation") as dispatch:
            response = TestClient(app, raise_server_exceptions=False).patch(
                "/api/v1/contractors/dispatch",
                headers=self.headers,
                json={"operation_sheet_id": 1, "contractor_capacity_id": 2},
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], A5_LINK_FAILED)
        dispatch.assert_not_called()

    def test_partial_a5_sync_exposes_failure_count(self):
        with patch(
            "app.api.deps.get_user_permission_codes", return_value={"workover_operation:a5_sync"}
        ), patch(
            "app.api.v1.endpoints.workover_operations.sync_daily_operations",
            new=AsyncMock(return_value={"updated": 2, "failed": 1}),
        ):
            response = TestClient(app, raise_server_exceptions=False).post(
                "/api/v1/workover-operations/a5-sync", headers=self.headers
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["msg"], "A5 日报同步部分完成")
        self.assertEqual(payload["data"]["updated_count"], 2)
        self.assertEqual(payload["data"]["failed_count"], 1)


if __name__ == "__main__":
    unittest.main()
