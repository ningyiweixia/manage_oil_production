import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import *  # noqa: F401,F403
from app.models.analytics import AnalyticsAlertStatus
from app.services.analytics_alert_service import list_alerts, patch_alert, upsert_alert
from app.schemas.analytics_alert import AnalyticsAlertCreate, AnalyticsAlertQuery, AnalyticsAlertUpdate


class AnalyticsAlertWorkflowTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)

    def test_upsert_is_idempotent_by_alert_key(self):
        with self.Session() as db:
            first = upsert_alert(
                db,
                AnalyticsAlertCreate(
                    alert_key="dq-W-1",
                    title="Missing completion",
                    message="Need completion record",
                    severity="high",
                    source_module="data_quality",
                ),
            )
            second = upsert_alert(
                db,
                AnalyticsAlertCreate(
                    alert_key="dq-W-1",
                    title="Missing completion updated",
                    message="Need completion record and review",
                    severity="high",
                    source_module="data_quality",
                    status=AnalyticsAlertStatus.PROCESSING,
                    assignee_name="Alice",
                ),
            )
            rows, total = list_alerts(db, AnalyticsAlertQuery())

        self.assertEqual(first.id, second.id)
        self.assertEqual(total, 1)
        self.assertEqual(rows[0].title, "Missing completion updated")
        self.assertEqual(rows[0].status, AnalyticsAlertStatus.PROCESSING)

    def test_status_transitions_allow_open_processing_closed_only(self):
        with self.Session() as db:
            created = upsert_alert(
                db,
                AnalyticsAlertCreate(
                    alert_key="dq-W-2",
                    title="Sync failure",
                    message="Need review",
                    severity="medium",
                    source_module="data_quality",
                ),
            )
            processing = patch_alert(db, created.id, AnalyticsAlertUpdate(status=AnalyticsAlertStatus.PROCESSING, assignee_name="Bob"), operator_id=7)
            closed = patch_alert(db, created.id, AnalyticsAlertUpdate(status=AnalyticsAlertStatus.CLOSED, remark="resolved"), operator_id=7)

        self.assertEqual(processing.status, AnalyticsAlertStatus.PROCESSING)
        self.assertEqual(closed.status, AnalyticsAlertStatus.CLOSED)
        self.assertIsNotNone(closed.processed_at)
        self.assertIsNotNone(closed.closed_at)


if __name__ == "__main__":
    unittest.main()
