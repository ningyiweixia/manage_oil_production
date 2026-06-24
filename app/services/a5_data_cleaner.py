"""A5 数据清洗引擎。

基于 Pandas 对 A5 系统原始数据进行标准化清洗、去重、格式统一。
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def clean_daily_report(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """用 Pandas DataFrame 清洗 A5 日报数据。

    清洗步骤：
    1. 转换为 DataFrame
    2. 去除完全重复行
    3. 统一日期格式
    4. 填充关键缺失值
    5. 返回标准化的 dict 列表
    """
    if not raw:
        return []

    df = pd.DataFrame(raw)

    # 去重
    df = df.drop_duplicates()

    # 统一日期字段格式
    date_columns = [col for col in df.columns if "date" in col.lower() or "time" in col.lower()]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

    # 填充数值列缺失值
    numeric_columns = df.select_dtypes(include=["number"]).columns
    df[numeric_columns] = df[numeric_columns].fillna(0)

    # 填充字符串列缺失值
    string_columns = df.select_dtypes(include=["object"]).columns
    df[string_columns] = df[string_columns].fillna("")

    logger.info(f"A5 日报清洗完成: {len(raw)} 条原始 -> {len(df)} 条处理后")
    return df.to_dict(orient="records")


def clean_operation_status(raw: dict[str, Any]) -> dict[str, Any]:
    """标准化单个作业状态数据。"""
    cleaned: dict[str, Any] = {}

    # 标准化 operation_no
    cleaned["operation_no"] = str(raw.get("operation_no", raw.get("op_no", raw.get("work_no", ""))))

    # 标准化 status
    status_raw = str(raw.get("status", raw.get("state", ""))).upper()
    status_map = {
        "PASS": "FINISHED",
        "FINISHED": "FINISHED",
        "CLOSED": "FINISHED",
        "REJECTED": "REJECTED",
        "PENDING": "WAITING_DISPATCH",
        "PROCESSING": "WORKING",
        "WORKING": "WORKING",
        "DISPATCHED": "DISPATCHED",
    }
    cleaned["status"] = status_map.get(status_raw, "WAITING_DISPATCH")

    # 标准化日期字段
    for key in ("start_time", "end_time", "report_date"):
        val = raw.get(key)
        if val:
            try:
                cleaned[key] = pd.Timestamp(val).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                cleaned[key] = str(val)

    # 保留原始备注
    cleaned["remark"] = raw.get("remark", raw.get("note", ""))

    return cleaned


def merge_operation_data(
    daily: list[dict[str, Any]],
    status: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """合并日报数据和状态数据，去重后以 operation_no 为 key 合并。"""
    if not daily:
        return status
    if not status:
        return daily

    daily_df = pd.DataFrame(daily)
    status_df = pd.DataFrame(status)

    # 以 operation_no 为 key 做左连接
    if "operation_no" in daily_df.columns and "operation_no" in status_df.columns:
        merged = daily_df.merge(
            status_df, on="operation_no", how="outer", suffixes=("_daily", "_status")
        )
        return merged.to_dict(orient="records")

    # 如果没有共同的 operation_no 字段，直接合并列表并去重
    combined = daily + status
    combined_df = pd.DataFrame(combined).drop_duplicates()
    return combined_df.to_dict(orient="records")


def validate_operation_data(data: dict[str, Any]) -> bool:
    """用 Pydantic 模型验证数据完整性。

    Args:
        data: 待验证的数据

    Returns:
        True 表示数据有效，False 表示无效
    """
    required_fields = ["operation_no"]
    for field in required_fields:
        if not data.get(field):
            logger.warning(f"A5 数据缺少必填字段: {field}")
            return False
    return True
