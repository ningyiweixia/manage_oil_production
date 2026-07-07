import asyncio
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("POSTGRES_PASSWORD", "test-postgres-password")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.api.v1.endpoints.workover_project_pools import submit_items  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models import *  # noqa: F401,F403,E402
from app.models.workover import ProjectPoolStatus, WorkoverProjectPool  # noqa: E402
from app.schemas.workover_project_pool import WorkoverProjectPoolSubmit  # noqa: E402


class WorkoverProjectSubmitTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        Base.metadata.create_all(engine)
        self.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def test_submit_draft_project_does_not_require_verification_fields(self):
        with self.SessionLocal() as db:
            project = WorkoverProjectPool(
                well_no="TEST-001",
                report_unit="第一采油作业区",
                production_priority=10,
                status=ProjectPoolStatus.DRAFT,
                measures_jsonb={"measures": []},
                photo_urls=[],
                is_deleted=False,
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            response = asyncio.run(
                submit_items(
                    WorkoverProjectPoolSubmit(project_ids=[project.id], comment="提交审批"),
                    SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")),
                    db,
                    SimpleNamespace(id=1),
                )
            )

            submitted = db.scalar(select(WorkoverProjectPool).where(WorkoverProjectPool.id == project.id))
            self.assertEqual(response.msg, "提报成功")
            self.assertEqual(response.data[0].status, ProjectPoolStatus.PENDING_GEOLOGY_VERIFY)
            self.assertEqual(submitted.status, ProjectPoolStatus.PENDING_GEOLOGY_VERIFY)


if __name__ == "__main__":
    unittest.main()
