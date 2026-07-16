import asyncio
import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.crud.completion import create_completion_record
from app.crud.contractor import BUSINESS_TZ, dispatch_operation
from app.db.base import Base
from app.models import *  # noqa: F401,F403
from app.models.completion import WellCompletionRecord
from app.models.integration import IntegrationEvent, IntegrationEventStatus
from app.models.material import MaterialRequirement, MaterialRequirementStatus, MaterialRequirementType
from app.models.workover import (
    ContractorCapacity,
    ContractorCapacityStatus,
    ContractorCapacitySyncStatus,
    OperationStatus,
    ProjectPoolStatus,
    WorkoverOperationSheet,
    WorkoverProjectPool,
)
from app.schemas.completion import WellCompletionCreate
from app.services.a5_sync_service import process_a5_callback_event
from app.services.data_scope_service import DataScope
from app.services.material_external_adapter import (
    MaterialExternalEvent,
    MockMaterialExternalAdapter,
    apply_external_material_event,
)
from app.services.statistics_analysis_service import StatisticsAnalysisQuery, build_statistics_analysis


class CrossModuleClosedLoopTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        with self.Session() as db:
            project = WorkoverProjectPool(
                well_no="WELL-CLOSED-001",
                report_unit="Unit Closed Loop",
                production_priority=1,
                status=ProjectPoolStatus.APPROVED,
                measures_jsonb={"measures": [{"measure_type": "acidizing"}]},
                photo_urls=[],
                attachments=[],
                related_project_ids=[],
                is_deleted=False,
            )
            contractor = ContractorCapacity(
                contractor_name="Closed Loop Contractor",
                team_name="Closed Loop Team",
                report_date=datetime.now(BUSINESS_TZ).date(),
                available_count=1,
                status=ContractorCapacityStatus.AVAILABLE,
                sync_status=ContractorCapacitySyncStatus.SYNCED,
                capability_tags={"acidizing": True},
                qualification_expire_at=datetime.now(BUSINESS_TZ).date() + timedelta(days=30),
            )
            sheet = WorkoverOperationSheet(
                project=project,
                operation_no="OP-CLOSED-001",
                status=OperationStatus.WAITING_DISPATCH,
                progress=0,
                progress_detail={},
            )
            db.add_all([project, contractor, sheet])
            db.flush()
            material = MaterialRequirement(
                well_no=project.well_no,
                operation_sheet_id=sheet.id,
                material_name="Tubing",
                quantity=5,
                unit="item",
                external_material_id="MAT-MOCK-001",
                source_platform="mock_material",
                status=MaterialRequirementStatus.APPROVED,
                requirement_type=MaterialRequirementType.NORMAL,
            )
            other_project = WorkoverProjectPool(
                well_no="WELL-OTHER-001",
                report_unit="Unit Other",
                production_priority=1,
                status=ProjectPoolStatus.DISPATCHED,
                measures_jsonb={"measures": [{"measure_type": "pump"}]},
                photo_urls=[],
                attachments=[],
                related_project_ids=[],
                is_deleted=False,
            )
            other_sheet = WorkoverOperationSheet(
                project=other_project,
                operation_no="OP-OTHER-001",
                status=OperationStatus.FINISHED,
                progress=100,
                progress_detail={},
            )
            db.add_all([other_project, other_sheet])
            db.flush()
            db.add_all([
                material,
                MaterialRequirement(
                    well_no=other_project.well_no,
                    operation_sheet_id=other_sheet.id,
                    material_name="Other Tubing",
                    quantity=5,
                    unit="item",
                    planned_quantity=5,
                    delivered_quantity=5,
                    arrived_quantity=5,
                    used_quantity=5,
                    status=MaterialRequirementStatus.USED,
                    requirement_type=MaterialRequirementType.NORMAL,
                ),
                WellCompletionRecord(
                    well_no=other_project.well_no,
                    operation_sheet_id=other_sheet.id,
                    measure_type="pump",
                    completion_date=date(2026, 7, 1),
                    pre_repair_data={},
                    post_repair_data={},
                ),
            ])
            db.commit()
            self.project_id = project.id
            self.sheet_id = sheet.id
            self.contractor_id = contractor.id
            self.material_id = material.id

    def test_closed_loop_events_feed_well_filtered_statistics(self):
        with self.Session() as db:
            dispatched = dispatch_operation(
                db,
                self.sheet_id,
                self.contractor_id,
                operator_id=1,
                operator_ip="127.0.0.1",
            )
            self.assertEqual(dispatched.project.status, ProjectPoolStatus.DISPATCHED)
            self.assertEqual(dispatched.status, OperationStatus.PENDING_A5)
            finished = process_a5_callback_event(
                db,
                {"operation_no": "OP-CLOSED-001", "status": "FINISHED", "remark": "completed"},
                event_id="a5-closed-loop-001",
            )
            duplicate = process_a5_callback_event(
                db,
                {"operation_no": "OP-CLOSED-001", "status": "FINISHED", "remark": "completed"},
                event_id="a5-closed-loop-001",
            )

            planned_event = asyncio.run(MockMaterialExternalAdapter("normal").fetch_events())[0]
            planned = apply_external_material_event(db, planned_event)
            for event in (
                MaterialExternalEvent("material-closed-loop-delivered", "MAT-MOCK-001", MaterialRequirementStatus.DELIVERED, 5),
                MaterialExternalEvent("material-closed-loop-arrived", "MAT-MOCK-001", MaterialRequirementStatus.ARRIVED, 5),
                MaterialExternalEvent("material-closed-loop-used", "MAT-MOCK-001", MaterialRequirementStatus.USED, 5),
            ):
                apply_external_material_event(db, event)

            completion = create_completion_record(
                db,
                WellCompletionCreate(
                    well_no="WELL-CLOSED-001",
                    operation_sheet_id=self.sheet_id,
                    measure_type="acidizing",
                    completion_date=date(2026, 7, 1),
                    team_name="Closed Loop Team",
                ),
            )
            result = build_statistics_analysis(db, StatisticsAnalysisQuery(well_no="WELL-CLOSED-001"))
            material = db.get(MaterialRequirement, self.material_id)
            sheet = db.get(WorkoverOperationSheet, self.sheet_id)
            a5_events = db.scalars(select(IntegrationEvent).where(IntegrationEvent.event_key == "a5-closed-loop-001")).all()

        self.assertTrue(finished.matched)
        self.assertFalse(finished.duplicate)
        self.assertTrue(duplicate.duplicate)
        self.assertFalse(planned.duplicate)
        self.assertEqual(len(a5_events), 1)
        self.assertEqual(sheet.status, OperationStatus.FINISHED)
        self.assertEqual(material.status, MaterialRequirementStatus.USED)
        self.assertEqual(material.used_quantity, 5)
        self.assertEqual(completion.operation_sheet_id, self.sheet_id)
        # The second well is intentionally complete with a used material; the
        # well filter must keep it out of every closed-loop aggregate below.
        self.assertEqual(result["material_usage"]["used"], 1)
        self.assertEqual(result["completion_classification"]["total"], 1)

    def test_a5_replay_is_duplicate_and_unknown_operation_stays_pending_with_two_source_events(self):
        payload = {"operation_no": "OP-CLOSED-001", "status": "WORKING", "remark": "started"}
        with self.Session() as db:
            first = process_a5_callback_event(db, payload, event_id="a5-replay-boundary-001")
            duplicate = process_a5_callback_event(db, payload, event_id="a5-replay-boundary-001")
            unmatched = process_a5_callback_event(
                db,
                {"operation_no": "OP-NOT-FOUND", "status": "WORKING"},
                event_id="a5-unmatched-boundary-001",
            )
            source_count = db.scalar(
                select(func.count()).select_from(IntegrationEvent).where(IntegrationEvent.source == "a5")
            )

        self.assertFalse(first.duplicate)
        self.assertTrue(first.matched)
        self.assertTrue(duplicate.duplicate)
        self.assertTrue(duplicate.matched)
        self.assertFalse(unmatched.matched)
        self.assertEqual(unmatched.event.status, IntegrationEventStatus.PENDING_REVIEW)
        self.assertEqual(source_count, 2)

    def test_territory_scope_includes_only_territory_project_material_and_completion_facts(self):
        with self.Session() as db:
            visible_project = WorkoverProjectPool(
                well_no="WELL-TERRITORY-VISIBLE",
                report_unit="Field Unit A",
                territory_unit="Territory Closed Loop",
                production_priority=1,
                status=ProjectPoolStatus.DISPATCHED,
                measures_jsonb={"measures": [{"measure_type": "acidizing"}]},
                photo_urls=[],
                attachments=[],
                related_project_ids=[],
                is_deleted=False,
            )
            hidden_project = WorkoverProjectPool(
                well_no="WELL-TERRITORY-HIDDEN",
                report_unit="Field Unit B",
                territory_unit="Territory Other",
                production_priority=1,
                status=ProjectPoolStatus.DISPATCHED,
                measures_jsonb={"measures": [{"measure_type": "pump"}]},
                photo_urls=[],
                attachments=[],
                related_project_ids=[],
                is_deleted=False,
            )
            visible_sheet = WorkoverOperationSheet(
                project=visible_project,
                operation_no="OP-TERRITORY-VISIBLE",
                status=OperationStatus.FINISHED,
                progress=100,
                progress_detail={},
            )
            hidden_sheet = WorkoverOperationSheet(
                project=hidden_project,
                operation_no="OP-TERRITORY-HIDDEN",
                status=OperationStatus.FINISHED,
                progress=100,
                progress_detail={},
            )
            db.add_all([visible_sheet, hidden_sheet])
            db.flush()
            db.add_all([
                MaterialRequirement(
                    well_no=visible_project.well_no,
                    operation_sheet_id=visible_sheet.id,
                    material_name="Visible Pipe",
                    quantity=1,
                    unit="item",
                    status=MaterialRequirementStatus.USED,
                    requirement_type=MaterialRequirementType.NORMAL,
                ),
                MaterialRequirement(
                    well_no=hidden_project.well_no,
                    operation_sheet_id=hidden_sheet.id,
                    material_name="Hidden Pipe",
                    quantity=1,
                    unit="item",
                    status=MaterialRequirementStatus.USED,
                    requirement_type=MaterialRequirementType.NORMAL,
                ),
                WellCompletionRecord(
                    well_no=visible_project.well_no,
                    operation_sheet_id=visible_sheet.id,
                    measure_type="acidizing",
                    completion_date=date(2026, 7, 2),
                    pre_repair_data={},
                    post_repair_data={},
                ),
                WellCompletionRecord(
                    well_no=hidden_project.well_no,
                    operation_sheet_id=hidden_sheet.id,
                    measure_type="pump",
                    completion_date=date(2026, 7, 2),
                    pre_repair_data={},
                    post_repair_data={},
                ),
            ])
            db.commit()
            scope = DataScope(
                is_global=False,
                user_id=1,
                department="Territory Closed Loop",
                reporting_units=("Territory Closed Loop",),
            )
            process_a5_callback_event(
                db,
                {"operation_no": visible_sheet.operation_no, "status": "FINISHED"},
                event_id="a5-territory-visible-001",
            )
            process_a5_callback_event(
                db,
                {"operation_no": hidden_sheet.operation_no, "status": "FINISHED"},
                event_id="a5-territory-hidden-001",
            )
            result = build_statistics_analysis(db, StatisticsAnalysisQuery(), scope=scope)

        self.assertEqual(result["overview_kpis"]["total_projects"], 1)
        self.assertEqual(result["overview_kpis"]["material_requirements"], 1)
        self.assertEqual(result["overview_kpis"]["completion_records"], 1)
        self.assertEqual(result["completion_classification"]["by_measure_type"], [{"measure_type": "acidizing", "count": 1}])
        self.assertEqual(result["integration_status"]["a5_processed"], 1)


if __name__ == "__main__":
    unittest.main()
