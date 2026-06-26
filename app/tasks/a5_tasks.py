"""A5 系统数据同步 Celery 定时任务。

方案强制要求：
- 每 30 分钟自动轮询拉取 A5 系统数据
- 连续失败 3 次触发告警
"""

import asyncio
import logging

from celery import shared_task

from app.db.session import SessionLocal
from app.core.redis import cache_client
from app.services.a5_sync_service import A5_SYNC_STATUS_KEY, _trigger_alert, full_sync

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, name="app.tasks.a5_tasks.sync_a5_data_task")
def sync_a5_data_task(self) -> dict:
    """Celery 定时任务：每 30 分钟同步 A5 日报/异常/工序数据。

    失败重试机制：
    - 最多重试 3 次
    - 重试间隔 60 秒
    - 连续失败 3 次触发企业微信告警
    """
    db = SessionLocal()
    cache_client.set_json(
        A5_SYNC_STATUS_KEY,
        {
            "last_sync_status": "running",
            "last_sync_message": "A5 数据同步任务运行中",
            "is_running": True,
        },
        expire_seconds=604800,
    )
    try:
        # Celery 任务运行在同步上下文中，需要手动运行 async 函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(full_sync(db))
        finally:
            loop.close()

        if result.get("overall") == "partial_failure":
            logger.warning(f"A5 数据同步部分失败: {result}")

        return result

    except Exception as exc:
        logger.exception(f"A5 数据同步失败（第 {self.request.retries + 1} 次重试）")

        # 连续失败 3 次触发告警（方案强制要求）
        if self.request.retries >= 2:
            _trigger_alert(f"A5 数据同步连续失败 3 次，请检查 A5 系统连接: {exc}")
            cache_client.set_json(
                A5_SYNC_STATUS_KEY,
                {
                    "last_sync_status": "failed",
                    "last_sync_message": str(exc),
                    "is_running": False,
                },
                expire_seconds=604800,
            )

        raise self.retry(exc=exc)

    finally:
        db.close()


@shared_task(name="app.tasks.a5_tasks.sync_anomaly_task")
def sync_anomaly_task() -> dict:
    """Celery 任务：手动触发异常数据同步。"""
    db = SessionLocal()
    try:
        from app.services.a5_sync_service import sync_anomalies

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(sync_anomalies(db))
        finally:
            loop.close()
        return result
    finally:
        db.close()
