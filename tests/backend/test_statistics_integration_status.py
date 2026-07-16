import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.models import *  # noqa: F401,F403
from app.models.integration import IntegrationEvent, IntegrationEventStatus
from app.services.statistics_analysis_service import build_integration_status


class StatisticsIntegrationStatusTest(unittest.TestCase):
    def test_status_exposes_adapter_modes_and_a5_event_counts(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        with Session() as db:
            db.add_all([
                IntegrationEvent(source="a5", event_key="done", payload_hash="a" * 64, status=IntegrationEventStatus.PROCESSED, raw_payload={}),
                IntegrationEvent(source="a5", event_key="review", payload_hash="b" * 64, status=IntegrationEventStatus.PENDING_REVIEW, raw_payload={}),
                IntegrationEvent(source="material", event_key="material", payload_hash="c" * 64, status=IntegrationEventStatus.PROCESSED, raw_payload={}),
            ])
            db.commit()
            with patch.object(settings, "a5_adapter_mode", "mock"), patch.object(settings, "material_adapter_mode", "mock"):
                result = build_integration_status(db)

        self.assertEqual(result["a5_adapter_mode"], "mock")
        self.assertEqual(result["material_adapter_mode"], "mock")
        self.assertEqual(result["a5_processed"], 1)
        self.assertEqual(result["a5_pending_review"], 1)


if __name__ == "__main__":
    unittest.main()
