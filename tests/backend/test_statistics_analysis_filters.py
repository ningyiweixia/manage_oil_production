import unittest
from datetime import date
from unittest.mock import Mock, patch

from pydantic import ValidationError
from sqlalchemy.dialects import sqlite

from app.crud import completion, material
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


if __name__ == "__main__":
    unittest.main()
