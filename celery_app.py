"""Celery 分布式任务队列配置。

定时任务：
- sync-a5-data-every-30min: 每 30 分钟拉取 A5 系统数据（方案强制要求）

启动方式：
    celery -A celery_app worker --loglevel=info --beat
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "manage_factory",
    broker=settings.redis_url or "redis://127.0.0.1:6379/0",
    backend=settings.redis_url or "redis://127.0.0.1:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    beat_schedule={
        "sync-a5-data-every-30min": {
            "task": "app.tasks.a5_tasks.sync_a5_data_task",
            "schedule": 1800.0,  # 30 分钟，方案强制要求
        },
    },
)
