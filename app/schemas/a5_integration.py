from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class A5CallbackPayload(BaseModel):
    """A5 系统回调请求体。"""
    operation_no: str = Field(min_length=1, max_length=64, description="A5 作业编号")
    status: str = Field(max_length=64, description="A5 工单状态（通过/办结/驳回等）")
    remark: str | None = Field(default=None, description="备注说明")


class A5TokenResponse(BaseModel):
    """SSO 跳转令牌响应。"""
    token: str = Field(description="SSO 临时令牌")
    expire_at: datetime = Field(description="令牌过期时间")
    redirect_url: str = Field(description="A5 系统跳转 URL")


class A5DataSyncLog(BaseModel):
    """A5 数据同步日志。"""
    sync_type: str = Field(description="同步类型（daily/anomaly/full）")
    sync_time: datetime = Field(description="同步时间")
    status: str = Field(description="同步状态（success/failed）")
    message: str = Field(default="", description="同步消息")
    raw_data_count: int = Field(default=0, description="原始数据条数")


class A5SyncStatusOut(BaseModel):
    """A5 同步状态查询响应。"""
    last_sync_time: datetime | None = None
    last_sync_status: str = "unknown"
    last_sync_message: str = ""
    sync_count_today: int = 0
    is_running: bool = False


class A5SyncTriggerOut(BaseModel):
    """手动触发同步的响应。"""
    task_id: str = Field(description="Celery 任务 ID")
    message: str = Field(description="描述信息")


class A5AnalyticsQuery(BaseModel):
    """A5 关键信息统计查询。"""
    start_date: date | None = None
    end_date: date | None = None
    category: str | None = Field(default=None, description="异常类型/工序类型")


class A5NameValueOut(BaseModel):
    name: str
    value: int


class A5TrendOut(BaseModel):
    days: list[str] = Field(default_factory=list)
    anomaly_counts: list[int] = Field(default_factory=list)
    process_counts: list[int] = Field(default_factory=list)


class A5AnalyticsOut(BaseModel):
    anomaly_total: int = 0
    special_process_total: int = 0
    anomaly_distribution: list[A5NameValueOut] = Field(default_factory=list)
    process_distribution: list[A5NameValueOut] = Field(default_factory=list)
    trend: A5TrendOut = Field(default_factory=A5TrendOut)


class A5AnalyticsReportOut(BaseModel):
    filename: str
    content_base64: str
    content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
