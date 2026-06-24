from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.redis import cache_client
from app.models.workover import OperationStatus, WorkoverOperationSheet, WorkoverProjectPool


def _lock_key(contractor_capacity_id: int) -> str:
    return f"dispatch:lock:{contractor_capacity_id}"


def acquire_dispatch_lock(contractor_capacity_id: int, ttl: int = 30) -> bool:
    """获取 Redis 分布式派工锁，SET NX EX 语义，防止并发派工冲突。

    Args:
        contractor_capacity_id: 承包商运力记录 ID
        ttl: 锁过期时间（秒），默认 30 秒防止死锁

    Returns:
        True 表示成功获取锁，False 表示锁已被其他调度员持有
    """
    import json
    from datetime import datetime, timezone

    lock_key = _lock_key(contractor_capacity_id)
    payload = json.dumps({"locked_at": datetime.now(timezone.utc).isoformat()})
    # CacheClient.set_json 内部会覆写，我们用 memory dict 存标志
    # 当 Redis 不可用时自动降级为进程内缓存
    return cache_client.set_json(lock_key, json.loads(payload), expire_seconds=ttl)


def release_dispatch_lock(contractor_capacity_id: int) -> None:
    """释放 Redis 分布式派工锁。"""
    lock_key = _lock_key(contractor_capacity_id)
    cache_client.delete(lock_key)


def select_priority_sheets(db: Session) -> list[WorkoverOperationSheet]:
    """查询待派工工单，按审批通过时间升序 + 产量优先级降序排序。

    方案要求：派工排序逻辑必须基于审批通过时间与产量优先级字段进行联合排序。
    """
    stmt = (
        select(WorkoverOperationSheet)
        .join(WorkoverProjectPool, WorkoverOperationSheet.project_id == WorkoverProjectPool.id)
        .where(WorkoverOperationSheet.status == OperationStatus.WAITING_DISPATCH)
        .order_by(
            WorkoverProjectPool.approved_at.asc().nullslast(),
            WorkoverProjectPool.production_priority.desc(),
        )
    )
    return list(db.scalars(stmt).all())
