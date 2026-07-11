import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import *  # noqa: F401,F403
from app.models.completion import WellCompletionRecord
from app.models.material import MaterialRequirement, MaterialRequirementStatus, MaterialRequirementType
from app.models.workover import ContractorCapacity, ContractorCapacityStatus, ContractorCapacitySyncStatus, OperationStatus, ProjectPoolStatus, WorkoverOperationSheet, WorkoverProjectPool
from app.services.data_quality_service import build_data_quality_summary
from app.services.statistics_analysis_service import StatisticsAnalysisQuery


class DataQualityServiceTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        with self.Session() as db:
            project = WorkoverProjectPool(
                well_no="W-1",
                report_unit="Unit A",
                block_name="Block A",
                status=ProjectPoolStatus.APPROVED,
                approved_at=datetime(2026, 7, 5, 10),
                measures_jsonb={"measures": [{"measure_type": "acidizing"}]},
                photo_urls=[],
                attachments=[],
                related_project_ids=[],
                is_deleted=False,
                created_at=datetime(2026, 7, 1, 8),
                updated_at=datetime(2026, 7, 1, 8),
            )
            contractor = ContractorCapacity(
                contractor_name="C-A",
                team_name="Team A",
                report_date=date(2026, 7, 1),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                sync_status=ContractorCapacitySyncStatus.INVALID,
                sync_error_message="sync failed",
                qualification_expire_at=date.today() + timedelta(days=5),
                capability_tags={},
            )
            sheet = WorkoverOperationSheet(
                project=project,
                contractor_capacity=contractor,
                operation_no="OP-1",
                status=OperationStatus.FINISHED,
                planned_start_at=datetime(2026, 7, 4, 10),
                planned_end_at=datetime(2026, 7, 3, 10),
                actual_start_at=datetime(2026, 7, 4, 12),
                actual_end_at=datetime(2026, 7, 4, 11),
                progress=100,
                progress_detail={},
                a5_status=None,
                created_at=datetime(2026, 7, 4, 9),
                updated_at=datetime(2026, 7, 4, 9),
            )
            other_project = WorkoverProjectPool(
                well_no="W-2",
                report_unit="Unit B",
                block_name="Block B",
                status=ProjectPoolStatus.DISPATCHED,
                approved_at=datetime(2026, 7, 2, 10),
                measures_jsonb={"measures": [{"measure_type": "pump"}]},
                photo_urls=[],
                attachments=[],
                related_project_ids=[],
                is_deleted=False,
                created_at=datetime(2026, 7, 2, 8),
                updated_at=datetime(2026, 7, 2, 8),
            )
            other_contractor = ContractorCapacity(
                contractor_name="C-B",
                team_name="Team B",
                report_date=date(2026, 7, 2),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                sync_status=ContractorCapacitySyncStatus.SYNCED,
                capability_tags={},
                qualification_expire_at=date.today() + timedelta(days=90),
            )
            other_sheet = WorkoverOperationSheet(
                project=other_project,
                contractor_capacity=other_contractor,
                operation_no="OP-2",
                status=OperationStatus.WORKING,
                planned_start_at=datetime(2026, 7, 2, 10),
                planned_end_at=datetime(2026, 7, 2, 20),
                actual_start_at=datetime(2026, 7, 2, 10),
                progress=40,
                progress_detail={"material": {"status": "ARRIVED", "total": 1, "counts": {"ARRIVED": 1}}},
                a5_status="SYNCED",
                last_a5_sync_at=datetime(2026, 7, 2, 11),
                created_at=datetime(2026, 7, 2, 9),
                updated_at=datetime(2026, 7, 2, 9),
            )
            db.add_all([sheet, other_sheet])
            db.flush()
            db.add_all(
                [
                    MaterialRequirement(
                        well_no="W-1",
                        operation_sheet_id=sheet.id,
                        material_name="M-1",
                        quantity=10,
                        unit="item",
                        planned_quantity=5,
                        delivered_quantity=6,
                        arrived_quantity=2,
                        used_quantity=3,
                        status=MaterialRequirementStatus.USED,
                        requirement_type=MaterialRequirementType.NORMAL,
                        source_platform="internal",
                        created_at=datetime(2026, 7, 4, 9),
                        updated_at=datetime(2026, 7, 4, 9),
                    ),
                    MaterialRequirement(
                        well_no="W-2",
                        operation_sheet_id=other_sheet.id,
                        material_name="M-2",
                        quantity=5,
                        unit="item",
                        planned_quantity=5,
                        delivered_quantity=5,
                        arrived_quantity=5,
                        used_quantity=5,
                        status=MaterialRequirementStatus.USED,
                        requirement_type=MaterialRequirementType.NORMAL,
                        source_platform="internal",
                        created_at=datetime(2026, 7, 2, 9),
                        updated_at=datetime(2026, 7, 2, 9),
                    ),
                    WellCompletionRecord(
                        well_no="W-2",
                        operation_sheet_id=other_sheet.id,
                        measure_type="pump",
                        completion_date=date(2026, 7, 2),
                        team_name="Team B",
                        pre_repair_data={},
                        post_repair_data={},
                        created_at=datetime(2026, 7, 2, 10),
                        updated_at=datetime(2026, 7, 2, 10),
                    ),
                ]
            )
            db.commit()

    def test_build_data_quality_summary_finds_core_issues(self):
        with self.Session() as db:
            summary = build_data_quality_summary(db, StatisticsAnalysisQuery())

        codes = {issue.rule_code for issue in summary.issues}
        self.assertGreaterEqual(summary.total_issues, 5)
        self.assertIn("A5_LINK_MISSING", codes)
        self.assertIn("PLAN_TIME_ORDER", codes)
        self.assertIn("ACTUAL_TIME_ORDER", codes)
        self.assertIn("MISSING_COMPLETION", codes)
        self.assertIn("MATERIAL_USAGE_EXCEEDED", codes)
        self.assertIn("QUALIFICATION_EXPIRING", codes)
        self.assertIn("CONTRACTOR_SYNC_FAILURE", codes)
        self.assertGreaterEqual(summary.severity_counts["high"], 3)
        self.assertEqual(summary.total_issues, len(summary.issues))

    def test_build_data_quality_summary_respects_well_filter(self):
        with self.Session() as db:
            summary = build_data_quality_summary(db, StatisticsAnalysisQuery(well_no="W-2"))

        self.assertTrue(summary.issues)
        self.assertTrue(all(issue.well_no == "W-2" or issue.entity_type == "contractor_capacity" for issue in summary.issues))


if __name__ == "__main__":
    unittest.main()
