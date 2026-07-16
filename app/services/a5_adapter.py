from datetime import date
from typing import Any, Protocol

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.status_codes import A5_LINK_FAILED
from app.services.a5_client import A5Client


class ExternalIntegrationError(BusinessException):
    def __init__(self, category: str):
        super().__init__(A5_LINK_FAILED, category)
        self.category = category


class A5Adapter(Protocol):
    async def fetch_daily_reports(self, report_date: date) -> list[dict[str, Any]]: ...
    async def fetch_anomalies(self, report_date: date) -> list[dict[str, Any]]: ...
    async def fetch_process_progress(self, report_date: date) -> list[dict[str, Any]]: ...


class HttpA5Adapter:
    def __init__(self, client: A5Client | None = None) -> None:
        self.client = client or A5Client()

    async def fetch_daily_reports(self, report_date: date) -> list[dict[str, Any]]:
        return await self.client.fetch_daily_reports(report_date.isoformat())

    async def fetch_anomalies(self, report_date: date) -> list[dict[str, Any]]:
        return await self.client.fetch_construction_anomalies(report_date.isoformat())

    async def fetch_process_progress(self, report_date: date) -> list[dict[str, Any]]:
        return await self.client.fetch_process_progress(report_date.isoformat())


class MockA5Adapter:
    def __init__(self, scenario: str = "normal") -> None:
        self.scenario = scenario

    def _records(self, report_date: date, kind: str) -> list[dict[str, Any]]:
        if self.scenario == "empty":
            return []
        if self.scenario == "timeout":
            raise ExternalIntegrationError("TIMEOUT")
        if self.scenario == "error":
            raise ExternalIntegrationError("REMOTE_UNAVAILABLE")
        day = report_date.isoformat()
        records = {
            "daily": [{"operation_no": "OP-MOCK-001", "status": "WORKING", "progress": 45, "report_date": day, "remark": "mock daily report"}],
            "anomaly": [{"operation_no": "OP-MOCK-001", "date": day, "anomaly_type": "PRESSURE_HIGH", "remark": "mock anomaly"}],
            "process": [{"operation_no": "OP-MOCK-001", "date": day, "process_type": "ACIDIZING", "progress": 45}],
        }
        result = records[kind]
        return result + result if self.scenario == "duplicate" else result

    async def fetch_daily_reports(self, report_date: date) -> list[dict[str, Any]]:
        return self._records(report_date, "daily")

    async def fetch_anomalies(self, report_date: date) -> list[dict[str, Any]]:
        return self._records(report_date, "anomaly")

    async def fetch_process_progress(self, report_date: date) -> list[dict[str, Any]]:
        return self._records(report_date, "process")


def get_a5_adapter() -> A5Adapter:
    if settings.a5_adapter_mode == "mock":
        return MockA5Adapter(settings.a5_mock_scenario)
    if settings.environment == "prod" and (not settings.a5_base_url or not settings.a5_api_key or not settings.a5_api_secret):
        raise ExternalIntegrationError("CONFIGURATION_ERROR")
    return HttpA5Adapter()
