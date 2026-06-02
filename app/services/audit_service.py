from typing import Any

from sqlalchemy.orm import Session

from app.models.approval import ApprovalAction, ApprovalLog


def write_approval_log(
    db: Session,
    *,
    business_type: str,
    business_id: int,
    node_code: str,
    action: ApprovalAction,
    operator_id: int,
    operator_ip: str | None,
    comment: str | None = None,
    before_snapshot: dict[str, Any] | None = None,
    after_snapshot: dict[str, Any] | None = None,
) -> ApprovalLog:
    log = ApprovalLog(
        business_type=business_type,
        business_id=business_id,
        node_code=node_code,
        action=action,
        operator_id=operator_id,
        operator_ip=operator_ip,
        comment=comment,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    db.add(log)
    return log
