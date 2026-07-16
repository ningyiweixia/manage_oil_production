from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import CONFLICT
from app.crud.contractor import get_contractor_capacity
from app.models.workover import ContractorCapacityStatus


def check_contractor_availability(db: Session, contractor_capacity_id: int) -> None:
    """检查承包商是否可用，不可用时抛出异常。"""
    contractor = get_contractor_capacity(db, contractor_capacity_id)
    if contractor.status != ContractorCapacityStatus.AVAILABLE:
        raise BusinessException(CONFLICT, f"承包商 {contractor.contractor_name} 当前状态不可用（{contractor.status.value}）")
