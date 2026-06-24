"""防偏磨设计系统 HTTP 客户端。

从防偏磨系统获取偏磨参数和历史数据。
"""

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.status_codes import A5_LINK_FAILED

logger = logging.getLogger(__name__)


class FpmClient:
    """防偏磨设计系统 API 客户端。"""

    def __init__(self) -> None:
        self.base_url = settings.fpm_base_url.rstrip("/") if settings.fpm_base_url else ""

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.base_url:
            logger.warning("防偏磨系统未配置（FPM_BASE_URL 为空），返回模拟数据")
            return {}
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as exc:
                logger.error(f"防偏磨系统请求失败: {url} -> {exc}")
                raise BusinessException(A5_LINK_FAILED, f"防偏磨系统连接失败: {path}")

    async def fetch_parameters(self, well_no: str) -> dict[str, Any]:
        """获取指定井号的偏磨参数。

        Args:
            well_no: 井号

        Returns:
            偏磨参数，包含 casing_diameter, tubing_size, wear_level 等
        """
        if not self.base_url:
            return {
                "well_no": well_no,
                "casing_diameter": 177.8,
                "tubing_size": 73.0,
                "wear_level": "MODERATE",
                "max_deviation": 3.5,
            }
        return await self._request("GET", f"/api/parameters?well_no={well_no}")

    async def fetch_history(self, well_no: str) -> list[dict[str, Any]]:
        """获取历史偏磨数据。"""
        if not self.base_url:
            return []
        return await self._request("GET", f"/api/history?well_no={well_no}")
