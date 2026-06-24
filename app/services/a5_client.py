"""A5 系统 HTTP 客户端。

对接 A5 系统的 REST API / 数据库只读中间表（Views）。
严禁使用 WebScraping。必须通过 A5 提供的正式接口进行数据拉取。
"""

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.status_codes import A5_LINK_FAILED

logger = logging.getLogger(__name__)


class A5Client:
    """A5 系统 API 客户端，封装所有与 A5 系统的 HTTP 通信。"""

    def __init__(self) -> None:
        self.base_url = settings.a5_base_url.rstrip("/") if settings.a5_base_url else ""
        self.api_key = settings.a5_api_key
        self.api_secret = settings.a5_api_secret
        self.timeout = 30

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-A5-Secret": self.api_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """通用请求方法，统一异常处理。"""
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, headers=self._headers(), **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                logger.error(f"A5 请求超时: {method} {url} -> {exc}")
                raise BusinessException(A5_LINK_FAILED, f"A5 系统请求超时: {path}")
            except httpx.HTTPStatusError as exc:
                logger.error(f"A5 请求失败: {method} {url} -> {exc.response.status_code}")
                raise BusinessException(A5_LINK_FAILED, f"A5 系统返回错误: {exc.response.status_code}")
            except httpx.RequestError as exc:
                logger.error(f"A5 连接失败: {method} {url} -> {exc}")
                raise BusinessException(A5_LINK_FAILED, f"A5 系统连接失败: {path}")

    async def fetch_daily_reports(self, date: str) -> list[dict[str, Any]]:
        """获取 A5 日报数据。

        Args:
            date: 日期字符串 YYYY-MM-DD

        Returns:
            日报数据列表
        """
        result = await self._request("GET", f"/api/daily-reports?date={date}")
        return result.get("data", [])

    async def fetch_operation_status(self, operation_no: str) -> dict[str, Any]:
        """获取单个作业最新状态。

        Args:
            operation_no: A5 作业编号

        Returns:
            作业状态数据
        """
        return await self._request("GET", f"/api/operations/{operation_no}/status")

    async def fetch_construction_anomalies(self, date: str) -> list[dict[str, Any]]:
        """获取施工异常数据。

        Args:
            date: 日期字符串 YYYY-MM-DD

        Returns:
            异常数据列表
        """
        result = await self._request("GET", f"/api/anomalies?date={date}")
        return result.get("data", [])

    async def fetch_process_progress(self, date: str) -> list[dict[str, Any]]:
        """获取工序进度数据。

        Args:
            date: 日期字符串 YYYY-MM-DD

        Returns:
            工序进度数据列表
        """
        result = await self._request("GET", f"/api/process-progress?date={date}")
        return result.get("data", [])

    async def health_check(self) -> bool:
        """检查 A5 系统是否可用。"""
        try:
            await self._request("GET", "/health")
            return True
        except BusinessException:
            return False
