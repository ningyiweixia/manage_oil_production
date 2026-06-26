import os
import unittest
from unittest.mock import patch

from sqlalchemy.exc import OperationalError

os.environ.setdefault("POSTGRES_PASSWORD", "test-postgres-password")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")

from fastapi.testclient import TestClient  # noqa: E402

import app.db.session as db_session  # noqa: E402
from main import app  # noqa: E402


class FailingSession:
    def scalar(self, *_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("database unavailable"))

    def close(self):
        pass


class DatabaseUnavailableTest(unittest.TestCase):
    def test_login_returns_503_when_database_is_unavailable(self):
        with patch.object(db_session, "SessionLocal", return_value=FailingSession()):
            response = TestClient(app, raise_server_exceptions=False).post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "ChangeMe_123!"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"code": 50300, "msg": "Database unavailable", "data": None},
        )


if __name__ == "__main__":
    unittest.main()
