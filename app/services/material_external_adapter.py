import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.status_codes import BAD_REQUEST, CONFLICT
from app.crud.material import get_material_requirement, update_material_requirement
from app.models.integration import IntegrationEvent, IntegrationEventStatus
from app.models.material import MaterialRequirement, MaterialRequirementStatus
from app.schemas.material import MaterialRequirementUpdate
from app.models.rbac import User


@dataclass(frozen=True)
class MaterialExternalEvent:
    event_id: str
    external_material_id: str
    status: MaterialRequirementStatus
    quantity: float
    source_platform: str = "mock_material"


@dataclass(frozen=True)
class MaterialExternalProcessResult:
    requirement: MaterialRequirement
    duplicate: bool


class MaterialExternalAdapter(Protocol):
    async def fetch_events(self) -> list[MaterialExternalEvent]: ...


class MockMaterialExternalAdapter:
    def __init__(self, scenario: str = "normal") -> None:
        self.scenario = scenario

    async def fetch_events(self) -> list[MaterialExternalEvent]:
        if self.scenario == "empty":
            return []
        if self.scenario == "timeout":
            raise TimeoutError("material adapter timeout")
        if self.scenario == "error":
            raise RuntimeError("material adapter remote error")
        event = MaterialExternalEvent(
            event_id="material-mock-plan-001",
            external_material_id="MAT-MOCK-001",
            status=MaterialRequirementStatus.PLANNED,
            quantity=5,
        )
        return [event, event] if self.scenario == "duplicate" else [event]


def get_material_external_adapter(
    mode: str | None = None,
    scenario: str | None = None,
) -> MaterialExternalAdapter:
    """Return the configured material integration adapter.

    The HTTP implementation is deliberately unavailable until a supplier
    contract is configured; this avoids silently treating a production setup
    as a successful sync.
    """
    selected_mode = mode or settings.material_adapter_mode
    if selected_mode == "mock":
        return MockMaterialExternalAdapter(scenario or settings.material_mock_scenario)
    raise BusinessException(BAD_REQUEST, "material HTTP adapter is not configured")


def _event_payload(event: MaterialExternalEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "external_material_id": event.external_material_id,
        "status": event.status.value,
        "quantity": event.quantity,
        "source_platform": event.source_platform,
    }


def apply_external_material_event(
    db: Session,
    event: MaterialExternalEvent,
    *,
    current_user: User | None = None,
) -> MaterialExternalProcessResult:
    payload = _event_payload(event)
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    existing = db.scalar(
        select(IntegrationEvent).where(
            IntegrationEvent.source == "material",
            IntegrationEvent.event_key == event.event_id,
        )
    )
    requirement = db.scalar(
        select(MaterialRequirement).where(MaterialRequirement.external_material_id == event.external_material_id)
    )
    if requirement is None:
        raise BusinessException(CONFLICT, "外部物料记录未匹配")
    requirement = get_material_requirement(db, requirement.id, current_user=current_user)

    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise BusinessException(CONFLICT, "物料事件键与既有载荷冲突")
        return MaterialExternalProcessResult(requirement=requirement, duplicate=True)

    event_log = IntegrationEvent(
        source="material",
        event_key=event.event_id,
        payload_hash=payload_hash,
        raw_payload=payload,
        operation_no=None,
        attempt_count=1,
    )
    db.add(event_log)
    db.flush()

    quantities: dict[str, float] = {}
    if event.status == MaterialRequirementStatus.PLANNED:
        quantities["planned_quantity"] = event.quantity
    elif event.status == MaterialRequirementStatus.DELIVERED:
        quantities["delivered_quantity"] = event.quantity
    elif event.status == MaterialRequirementStatus.ARRIVED:
        quantities["arrived_quantity"] = event.quantity
    elif event.status == MaterialRequirementStatus.USED:
        quantities["used_quantity"] = event.quantity

    updated = update_material_requirement(
        db,
        requirement.id,
        MaterialRequirementUpdate(status=event.status, source_platform=event.source_platform, **quantities),
        current_user=current_user,
        commit=False,
        validate_link=False,
    )
    event_log.status = IntegrationEventStatus.PROCESSED
    event_log.processed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(updated)
    return MaterialExternalProcessResult(requirement=updated, duplicate=False)
