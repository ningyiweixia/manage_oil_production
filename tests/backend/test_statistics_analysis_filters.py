import unittest
from datetime import date, datetime
from unittest.mock import Mock, patch

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.crud import completion, material
from app.db.base import Base
from app.models import *  # noqa: F401,F403
from app.models.completion import WellCompletionRecord
from app.models.material import MaterialRequirement, MaterialRequirementStatus, MaterialRequirementType
from app.models.workover import ContractorCapacity, ContractorCapacityStatus, OperationStatus, ProjectPoolStatus, WorkoverOperationSheet, WorkoverProjectPool
from app.services.statistics_analysis_service import StatisticsAnalysisQuery, build_statistics_analysis
from app.services import workover_operation_service as operation_service


ADAPTER_MODELS_EXIST = all(
    (
        hasattr(completion, "CompletionAnalyticsQuery"),
        hasattr(material, "MaterialAnalyticsQuery"),
        hasattr(operation_service, "OperationAnalyticsQuery"),
    )
)


class _Scalars:
    def all(self):
        return []


class _RecordingSession:
    def __init__(self):
        self.statements = []

    def scalars(self, statement):
        self.statements.append(statement)
        return _Scalars()

    def scalar(self, statement):
        self.statements.append(statement)
        return 0


def _sql(statement) -> str:
    return str(statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))


class StatisticsAnalysisFilterTest(unittest.TestCase):
    def test_analytics_adapters_expose_explicit_query_models(self):
        self.assertTrue(ADAPTER_MODELS_EXIST, "analytics adapters must expose explicit query models")

    def test_query_rejects_reversed_date_range(self):
        with self.assertRaisesRegex(ValidationError, "start_date must be on or before end_date"):
            StatisticsAnalysisQuery(start_date=date(2026, 7, 2), end_date=date(2026, 7, 1))

    def test_statistics_default_query_preserves_existing_operation_aggregates(self):
        query = StatisticsAnalysisQuery()
        workover = Mock()
        workover.kpis = Mock(total_projects=0, pending_approvals=0, approval_rate=0, estimated_cost=0)
        workover.status_counts = []
        workover.measure_distribution = []
        workover.heatmap = Mock(model_dump=lambda **_: {})
        workover.trend = Mock(model_dump=lambda **_: {})
        a5 = Mock(anomaly_total=0, special_process_total=0, anomaly_distribution=[], process_distribution=[], trend=[])
        existing = {"total_sheets": 2, "measure_type_distribution": [{"measure_type": "acidizing", "count": 2}], "anomaly_count": 3}
        with (
            patch("app.services.statistics_analysis_service.build_workover_analytics", return_value=workover),
            patch("app.services.statistics_analysis_service.build_a5_analytics", return_value=a5),
            patch("app.services.statistics_analysis_service.build_workover_operation_dashboard", return_value=existing) as operation,
            patch("app.services.statistics_analysis_service.get_material_analytics", return_value={"total": 0}),
            patch("app.services.statistics_analysis_service.get_completion_analytics", return_value={"total": 0, "by_measure_type": []}),
        ):
            result = build_statistics_analysis(Mock(), query)
        operation.assert_called_once_with(unittest.mock.ANY, None)
        self.assertEqual(result["operation_efficiency"]["measure_type_distribution"], existing["measure_type_distribution"])
        self.assertEqual(result["operation_efficiency"]["anomaly_count"], 3)

    @unittest.skipUnless(ADAPTER_MODELS_EXIST, "adapter query models not implemented")
    def test_statistics_forwards_all_applicable_adapter_filters(self):
        CompletionAnalyticsQuery = completion.CompletionAnalyticsQuery
        MaterialAnalyticsQuery = material.MaterialAnalyticsQuery
        OperationAnalyticsQuery = operation_service.OperationAnalyticsQuery
        query = StatisticsAnalysisQuery(
            start_date=date(2026, 7, 1), end_date=date(2026, 7, 2), well_no="W-1",
            report_unit="Unit A", team_name="Team A", material_status="ARRIVED",
            measure_type="acidizing", block_name="Block A", status="APPROVED",
        )
        workover = Mock()
        workover.kpis = Mock(total_projects=0, pending_approvals=0, approval_rate=0, estimated_cost=0)
        workover.status_counts = []
        workover.measure_distribution = []
        workover.heatmap = Mock(model_dump=lambda **_: {})
        workover.trend = Mock(model_dump=lambda **_: {})
        a5 = Mock(anomaly_total=0, special_process_total=0, anomaly_distribution=[], process_distribution=[], trend=[])

        with (
            patch("app.services.statistics_analysis_service.build_workover_analytics", return_value=workover),
            patch("app.services.statistics_analysis_service.build_a5_analytics", return_value=a5),
            patch("app.services.statistics_analysis_service.build_workover_operation_dashboard", return_value={"total_sheets": 0}) as operation,
            patch("app.services.statistics_analysis_service.get_material_analytics", return_value={"total": 0}) as material_adapter,
            patch("app.services.statistics_analysis_service.get_completion_analytics", return_value={"total": 0, "by_measure_type": []}) as completion_adapter,
        ):
            build_statistics_analysis(Mock(), query)

        operation_query = operation.call_args.args[1]
        self.assertEqual(operation_query, OperationAnalyticsQuery(
            start_date=query.start_date, end_date=query.end_date, well_no="W-1",
            report_unit="Unit A", team_name="Team A", block_name="Block A", status="APPROVED",
            measure_type="acidizing", material_status="ARRIVED",
        ))
        self.assertEqual(material_adapter.call_args.args[1], MaterialAnalyticsQuery(
            start_date=query.start_date, end_date=query.end_date, well_no="W-1", status="ARRIVED",
        ))
        self.assertEqual(completion_adapter.call_args.args[1], CompletionAnalyticsQuery(
            start_date=query.start_date, end_date=query.end_date, well_no="W-1",
            measure_type="acidizing", team_name="Team A",
        ))

    @unittest.skipUnless(ADAPTER_MODELS_EXIST, "adapter query models not implemented")
    def test_material_filters_are_sql_predicates_and_empty_result_is_stable(self):
        MaterialAnalyticsQuery = material.MaterialAnalyticsQuery
        db = _RecordingSession()
        result = material.get_material_analytics(db, MaterialAnalyticsQuery(
            start_date=date(2026, 7, 1), end_date=date(2026, 7, 2), well_no="W-1", status="ARRIVED",
        ))
        sql = _sql(db.statements[0])
        self.assertIn("material_requirement.well_no", sql)
        self.assertIn("material_requirement.status", sql)
        self.assertIn("material_requirement.created_at >=", sql)
        self.assertIn("material_requirement.created_at <", sql)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["usage_rate"], 0.0)

    @unittest.skipUnless(ADAPTER_MODELS_EXIST, "adapter query models not implemented")
    def test_completion_filters_are_sql_predicates_and_empty_result_is_stable(self):
        CompletionAnalyticsQuery = completion.CompletionAnalyticsQuery
        db = _RecordingSession()
        result = completion.get_completion_analytics(db, CompletionAnalyticsQuery(
            start_date=date(2026, 7, 1), end_date=date(2026, 7, 2), well_no="W-1",
            measure_type="acidizing", team_name="Team A",
        ))
        sql = _sql(db.statements[0])
        for column in ("well_no", "measure_type", "team_name", "completion_date"):
            self.assertIn(f"well_completion_record.{column}", sql)
        self.assertEqual(result, {"total": 0, "by_measure_type": []})

    @unittest.skipUnless(ADAPTER_MODELS_EXIST, "adapter query models not implemented")
    def test_operation_filters_are_sql_predicates_and_empty_result_is_stable(self):
        OperationAnalyticsQuery = operation_service.OperationAnalyticsQuery
        db = _RecordingSession()
        result = operation_service.build_workover_operation_dashboard(db, OperationAnalyticsQuery(
            start_date=date(2026, 7, 1), end_date=date(2026, 7, 2), well_no="W-1",
            report_unit="Unit A", team_name="Team A", block_name="Block A", status="APPROVED",
        ))
        sql = _sql(db.statements[0])
        for fragment in (
            "workover_project_pool.well_no", "workover_project_pool.report_unit",
            "workover_project_pool.block_name", "workover_project_pool.status",
            "contractor_capacity.team_name", "workover_operation_sheet.created_at >=",
            "workover_operation_sheet.created_at <",
        ):
            self.assertIn(fragment, sql)
        self.assertEqual(result["total_sheets"], 0)
        self.assertEqual(result["dispatch_rate"], 0)
        self.assertEqual(result["completion_rate"], 0)


class SeededStatisticsAnalysisFilterTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        with self.Session() as db:
            match_project = WorkoverProjectPool(
                well_no="W-1", report_unit="Unit A", block_name="Block A", status=ProjectPoolStatus.APPROVED,
                production_priority=1, measures_jsonb={"measures": [{"measure_type": "acidizing"}]},
                photo_urls=[], attachments=[], related_project_ids=[], is_deleted=False,
                created_at=datetime(2026, 7, 1, 8), updated_at=datetime(2026, 7, 1, 8),
            )
            other_project = WorkoverProjectPool(
                well_no="W-2", report_unit="Unit B", block_name="Block B", status=ProjectPoolStatus.DISPATCHED,
                production_priority=1, measures_jsonb={"measures": [{"measure_type": "pump"}]},
                photo_urls=[], attachments=[], related_project_ids=[], is_deleted=False,
                created_at=datetime(2026, 7, 3, 8), updated_at=datetime(2026, 7, 3, 8),
            )
            team_a = ContractorCapacity(contractor_name="C-A", team_name="Team A", report_date=date(2026, 7, 1), available_count=1, status=ContractorCapacityStatus.AVAILABLE, capability_tags={})
            team_b = ContractorCapacity(contractor_name="C-B", team_name="Team B", report_date=date(2026, 7, 3), available_count=1, status=ContractorCapacityStatus.AVAILABLE, capability_tags={})
            match_sheet = WorkoverOperationSheet(
                project=match_project, contractor_capacity=team_a, operation_no="OP-1", status=OperationStatus.FINISHED,
                progress=100, progress_detail={}, a5_status="ERROR", created_at=datetime(2026, 7, 1, 9), updated_at=datetime(2026, 7, 1, 9),
            )
            other_sheet = WorkoverOperationSheet(
                project=other_project, contractor_capacity=team_b, operation_no="OP-2", status=OperationStatus.WORKING,
                progress=50, progress_detail={}, created_at=datetime(2026, 7, 3, 9), updated_at=datetime(2026, 7, 3, 9),
            )
            db.add_all([match_sheet, other_sheet])
            db.flush()
            db.add_all([
                MaterialRequirement(well_no="W-1", operation_sheet_id=match_sheet.id, material_name="M-1", quantity=1, unit="item", status=MaterialRequirementStatus.ARRIVED, requirement_type=MaterialRequirementType.NORMAL, created_at=datetime(2026, 7, 1, 10), updated_at=datetime(2026, 7, 1, 10)),
                MaterialRequirement(well_no="W-2", operation_sheet_id=other_sheet.id, material_name="M-2", quantity=1, unit="item", status=MaterialRequirementStatus.USED, requirement_type=MaterialRequirementType.NORMAL, created_at=datetime(2026, 7, 3, 10), updated_at=datetime(2026, 7, 3, 10)),
                WellCompletionRecord(well_no="W-1", operation_sheet_id=match_sheet.id, measure_type="acidizing", team_name="Team A", completion_date=date(2026, 7, 1), pre_repair_data={}, post_repair_data={}, created_at=datetime(2026, 7, 1, 11), updated_at=datetime(2026, 7, 1, 11)),
                WellCompletionRecord(well_no="W-2", operation_sheet_id=other_sheet.id, measure_type="pump", team_name="Team B", completion_date=date(2026, 7, 3), pre_repair_data={}, post_repair_data={}, created_at=datetime(2026, 7, 3, 11), updated_at=datetime(2026, 7, 3, 11)),
            ])
            db.commit()

    def test_material_legacy_positional_well_no_remains_supported(self):
        with self.Session() as db:
            result = material.get_material_analytics(db, "W-1")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["arrived"], 1)

    def test_material_seeded_filters_change_aggregate(self):
        with self.Session() as db:
            all_rows = material.get_material_analytics(db)
            filtered = material.get_material_analytics(db, material.MaterialAnalyticsQuery(
                well_no="W-1", status="ARRIVED", start_date=date(2026, 7, 1), end_date=date(2026, 7, 1),
            ))
        self.assertEqual(all_rows["total"], 2)
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(filtered["arrived"], 1)

    def test_completion_seeded_filters_change_aggregate(self):
        with self.Session() as db:
            all_rows = completion.get_completion_analytics(db)
            filtered = completion.get_completion_analytics(db, completion.CompletionAnalyticsQuery(
                well_no="W-1", measure_type="acidizing", team_name="Team A",
                start_date=date(2026, 7, 1), end_date=date(2026, 7, 1),
            ))
        self.assertEqual(all_rows["total"], 2)
        self.assertEqual(filtered, {"total": 1, "by_measure_type": [{"measure_type": "acidizing", "count": 1}]})

    def test_operation_seeded_filters_change_all_aggregates_and_runtime_focus(self):
        query = operation_service.OperationAnalyticsQuery(
            well_no="W-1", report_unit="Unit A", team_name="Team A", block_name="Block A",
            status="APPROVED", measure_type="acidizing", material_status="ARRIVED",
            start_date=date(2026, 7, 1), end_date=date(2026, 7, 1),
        )
        with self.Session() as db:
            all_rows = operation_service.build_workover_operation_dashboard(db)
            filtered = operation_service.build_workover_operation_dashboard(db, query)
        self.assertEqual(all_rows["total_sheets"], 2)
        self.assertEqual(filtered["total_sheets"], 1)
        self.assertEqual(filtered["runtime_focus"]["material_total"], 1)
        self.assertEqual(filtered["runtime_focus"]["completion_total"], 1)
        self.assertEqual(filtered["runtime_focus"]["a5_synced"], 1)
        self.assertEqual(filtered["measure_type_distribution"], [{"measure_type": "acidizing", "count": 1}])
        self.assertEqual(filtered["anomaly_count"], 1)
        self.assertEqual(filtered["team_workload"], [{"team_name": "Team A", "sheet_count": 1}])


if __name__ == "__main__":
    unittest.main()
