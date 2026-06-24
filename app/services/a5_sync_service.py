"""A5 数据同步服务。

包含日报同步、异常同步、全量同步的核心业务逻辑。
每 30 分钟由 Celery 定时任务触发。
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.status_codes import A5_LINK_FAILED
from app.models.workover import OperationStatus, WorkoverOperationSheet
from app.services.a5_client import A5Client
from app.services.a5_data_cleaner import clean_daily_report, validate_operation_data

logger = logging.getLogger(__name__)


async def sync_daily_operations(db: Session, sync_date: str | None = None) -> dict[str, Any]:
    """同步 A5 日报数据到修井运行表。

    Args:
        db: 数据库会话
        sync_date: 同步日期（YYYY-MM-DD），默认当天

    Returns:
        同步统计：{total, updated, failed}
    """
    if sync_date is None:
        sync_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = A5Client()
    try:
        raw_data = await client.fetch_daily_reports(sync_date)
    except BusinessException as exc:
        logger.error(f"A5 日报拉取失败: {exc.msg}")
        return {"total": 0, "updated": 0, "failed": 0, "error": exc.msg}

    cleaned = clean_daily_report(raw_data)
    stats = {"total": len(cleaned), "updated": 0, "failed": 0}

    for record in cleaned:
        if not validate_operation_data(record):
            stats["failed"] += 1
            continue
        try:
            operation_no = record.get("operation_no", "")
            existing = db.query(WorkoverOperationSheet).filter(
                WorkoverOperationSheet.operation_no == operation_no
            ).first()
            if existing:
                existing.status = OperationStatus.WORKING
                stats["updated"] += 1
        except Exception as exc:
            logger.exception(f"日报同步更新失败: {exc}")
            db.rollback()
            stats["failed"] += 1

    if stats["updated"] > 0 or stats["total"] > 0:
        db.commit()

    logger.info(f"A5 日报同步完成: {stats}")
    return stats


async def sync_anomalies(db: Session, sync_date: str | None = None) -> dict[str, Any]:
    """同步 A5 施工异常数据。"""
    if sync_date is None:
        sync_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = A5Client()
    try:
        raw_data = await client.fetch_construction_anomalies(sync_date)
    except BusinessException as exc:
        logger.error(f"A5 异常数据拉取失败: {exc.msg}")
        return {"total": 0, "synced": 0, "error": exc.msg}

    cleaned = clean_daily_report(raw_data)
    logger.info(f"A5 异常同步完成: {len(cleaned)} 条")
    return {"total": len(cleaned), "synced": len(cleaned)}


async def full_sync(db: Session) -> dict[str, Any]:
    """全量同步 - 组合日报 + 异常 + 工序进度。"""
    sync_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    daily_stats = await sync_daily_operations(db, sync_date)
    anomaly_stats = await sync_anomalies(db, sync_date)

    result = {
        "sync_time": datetime.now(timezone.utc).isoformat(),
        "daily": daily_stats,
        "anomaly": anomaly_stats,
        "overall": "success",
    }

    # 检查是否有失败情况
    if daily_stats.get("error") or anomaly_stats.get("error"):
        result["overall"] = "partial_failure"

    return result


def _trigger_alert(message: str) -> None:
    """触发企业微信/内部通告警（预留接口）。

    当前实现记录日志，后续可对接企业微信 Webhook。
    """
    logger.error(f"[A5 告警] {message}")
    # TODO: 对接企业微信 Webhook
    # import requests
    # requests.post(WECHAT_WEBHOOK_URL, json={"msgtype": "text", "text": {"content": message}})
