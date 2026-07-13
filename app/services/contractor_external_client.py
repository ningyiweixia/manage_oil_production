from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.models.workover import ContractorCapacityStatus

logger = logging.getLogger(__name__)


class ContractorExternalClientError(RuntimeError):
    """Raised when the formal contractor system API cannot be used."""


@dataclass(frozen=True)
class ExternalContractorTeam:
    external_system_id: str
    contractor_name: str
    team_name: str
    report_date: date
    available_count: int
    status: ContractorCapacityStatus
    external_status: str
    capability_tags: dict[str, Any]
    contact_name: str | None = None
    contact_phone: str | None = None
    qualification_expire_at: date | None = None
    equipment_summary: str | None = None


def _parse_date(value: Any, field_name: str) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ContractorExternalClientError(f"外部承包商系统返回的 {field_name} 格式异常")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ContractorExternalClientError(f"外部承包商系统返回的 {field_name} 不是有效日期") from exc


def _normalize_status(value: Any) -> ContractorCapacityStatus:
    raw = str(value or "").upper()
    mapping = {
        "AVAILABLE": ContractorCapacityStatus.AVAILABLE,
        "BUSY": ContractorCapacityStatus.BUSY,
        "OFFLINE": ContractorCapacityStatus.OFFLINE,
        "EXCEPTION": ContractorCapacityStatus.EXCEPTION,
        "可用": ContractorCapacityStatus.AVAILABLE,
        "忙碌": ContractorCapacityStatus.BUSY,
        "离线": ContractorCapacityStatus.OFFLINE,
        "异常": ContractorCapacityStatus.EXCEPTION,
    }
    return mapping.get(raw, ContractorCapacityStatus.EXCEPTION)


class ContractorExternalClient:
    """REST client for the external contractor system.

    The production path only calls the formal REST API. Local development can
    use deterministic mock rows when the external system is not configured.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float | None = None,
        mock_enabled: bool | None = None,
    ) -> None:
        self.base_url = (settings.contractor_system_base_url if base_url is None else base_url).rstrip("/")
        self.token = settings.contractor_system_token if token is None else token
        self.timeout = settings.contractor_system_timeout if timeout is None else timeout
        self.mock_enabled = settings.contractor_system_mock_enabled if mock_enabled is None else mock_enabled
        self.invalid_rows: list[dict[str, str]] = []

    @property
    def connection_status(self) -> str:
        if self.base_url and self.token:
            return "正常"
        if self.mock_enabled:
            return "演示模式"
        return "异常"

    def fetch_capacities(self, *, report_date: date, external_system_id: str | None = None) -> list[ExternalContractorTeam]:
        self.invalid_rows = []
        if not self.base_url:
            if self.mock_enabled:
                return self._mock_capacities(report_date, external_system_id=external_system_id)
            raise ContractorExternalClientError("外部承包商系统未配置 base_url")
        if not self.base_url.startswith("https://"):
            raise ContractorExternalClientError("外部承包商系统 base_url 必须使用 HTTPS")
        if not self.token:
            raise ContractorExternalClientError("外部承包商系统未配置 token")

        params: dict[str, str] = {"report_date": report_date.isoformat()}
        if external_system_id:
            params["external_system_id"] = external_system_id
        url = f"{self.base_url}/api/capacities?{urlencode(params)}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"})
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise ContractorExternalClientError("外部承包商系统鉴权失败") from exc
            raise ContractorExternalClientError(f"外部承包商系统请求失败：HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise ContractorExternalClientError("外部承包商系统网络异常") from exc
        except json.JSONDecodeError as exc:
            raise ContractorExternalClientError("外部承包商系统响应不是有效 JSON") from exc

        rows = payload.get("items") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ContractorExternalClientError("外部承包商系统响应格式异常：缺少 items 列表")
        teams: list[ExternalContractorTeam] = []
        for index, row in enumerate(rows):
            try:
                teams.append(self._parse_team(row, default_report_date=report_date))
            except (ContractorExternalClientError, TypeError, ValueError) as exc:
                logger.warning("忽略外部承包商坏数据: %s", exc)
                self.invalid_rows.append({"row_index": str(index), "error": str(exc)})
        return teams

    def _parse_team(self, row: Any, *, default_report_date: date) -> ExternalContractorTeam:
        if not isinstance(row, dict):
            raise ContractorExternalClientError("外部承包商系统队伍数据格式异常")
        required = ["external_system_id", "contractor_name", "team_name"]
        missing = [key for key in required if not row.get(key)]
        if missing:
            raise ContractorExternalClientError(f"外部承包商系统队伍数据缺少字段：{', '.join(missing)}")
        capability_tags = row.get("capability_tags") or {}
        if not isinstance(capability_tags, dict):
            raise ContractorExternalClientError("外部承包商系统能力标签格式异常")
        expire_at = row.get("qualification_expire_at")
        row_report_date = _parse_date(row.get("report_date") or default_report_date, "report_date")
        if row_report_date != default_report_date:
            raise ContractorExternalClientError("外部承包商运力日期与请求日期不一致")
        return ExternalContractorTeam(
            external_system_id=str(row["external_system_id"]),
            contractor_name=str(row["contractor_name"]),
            team_name=str(row["team_name"]),
            report_date=row_report_date,
            available_count=max(int(row.get("available_count") or 0), 0),
            status=_normalize_status(row.get("status")),
            external_status=str(row.get("external_status") or row.get("status") or ""),
            capability_tags=capability_tags,
            contact_name=row.get("contact_name"),
            contact_phone=row.get("contact_phone"),
            qualification_expire_at=_parse_date(expire_at, "qualification_expire_at") if expire_at else None,
            equipment_summary=row.get("equipment_summary"),
        )

    def _mock_capacities(self, report_date: date, *, external_system_id: str | None) -> list[ExternalContractorTeam]:
        rows = [
            ExternalContractorTeam(
                external_system_id="EXT-WORKOVER-001",
                contractor_name="胜利油服井下一公司",
                team_name="修井一队",
                report_date=report_date,
                available_count=2,
                status=ContractorCapacityStatus.AVAILABLE,
                external_status="AVAILABLE",
                capability_tags={"major_repair": True, "acidizing": True, "deep_well": False},
                contact_name="张队长",
                contact_phone="13800000001",
                qualification_expire_at=date(report_date.year + 1, 12, 31),
                equipment_summary="通井机2台，泵车1台，井控装备齐套",
            ),
            ExternalContractorTeam(
                external_system_id="EXT-WORKOVER-002",
                contractor_name="渤海钻探井下作业队",
                team_name="措施二队",
                report_date=report_date,
                available_count=0,
                status=ContractorCapacityStatus.BUSY,
                external_status="BUSY",
                capability_tags={"major_repair": False, "fracturing": True, "sand_control": True},
                contact_name="李队长",
                contact_phone="13800000002",
                qualification_expire_at=date(report_date.year + 1, 10, 31),
                equipment_summary="压裂辅助设备1套，连续油管保障车辆1台",
            ),
        ]
        if external_system_id:
            return [row for row in rows if row.external_system_id == external_system_id]
        return rows
