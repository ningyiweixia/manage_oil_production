import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import BusinessException
from app.db.base import Base
from app.models import *  # noqa: F401,F403
from app.models.integration import IntegrationEvent, IntegrationEventStatus
from app.models.workover import OperationStatus, ProjectPoolStatus, WorkoverOperationSheet, WorkoverProjectPool
from app.services.a5_sync_service import process_a5_callback_event


class A5EventWorkflowTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        with self.Session() as db:
            project = WorkoverProjectPool(
                well_no="WELL-001",
                report_unit="Unit A",
                production_priority=1,
                status=ProjectPoolStatus.APPROVED,
                measures_jsonb={},
                photo_urls=[],
                attachments=[],
                related_project_ids=[],
                is_deleted=False,
            )
            db.add(WorkoverOperationSheet(project=project, operation_no="OP-001", status=OperationStatus.DISPATCHED, progress=0, progress_detail={}))
            db.commit()

    def test_repeated_event_id_with_same_payload_updates_operation_once(self):
        payload = {"operation_no": "OP-001", "status": "WORKING", "remark": "started"}
        with self.Session() as db:
            first = process_a5_callback_event(db, payload, event_id="evt-001")
            second = process_a5_callback_event(db, payload, event_id="evt-001")
            rows = db.scalars(select(IntegrationEvent).where(IntegrationEvent.event_key == "evt-001")).all()
            sheet = db.scalar(select(WorkoverOperationSheet).where(WorkoverOperationSheet.operation_no == "OP-001"))

        self.assertFalse(first.duplicate)
        self.assertTrue(second.duplicate)
        self.assertEqual(len(rows), 1)
        self.assertEqual(sheet.status, OperationStatus.WORKING)

    def test_same_event_id_with_different_payload_is_rejected(self):
        with self.Session() as db:
            process_a5_callback_event(db, {"operation_no": "OP-001", "status": "WORKING"}, event_id="evt-002")
            with self.assertRaises(BusinessException):
                process_a5_callback_event(db, {"operation_no": "OP-001", "status": "FINISHED"}, event_id="evt-002")

    def test_unknown_operation_is_retained_for_manual_review(self):
        with self.Session() as db:
            result = process_a5_callback_event(db, {"operation_no": "OP-MISSING", "status": "WORKING"}, event_id="evt-003")
            event = db.scalar(select(IntegrationEvent).where(IntegrationEvent.event_key == "evt-003"))

        self.assertFalse(result.matched)
        self.assertEqual(event.status, IntegrationEventStatus.PENDING_REVIEW)


if __name__ == "__main__":
    unittest.main()
