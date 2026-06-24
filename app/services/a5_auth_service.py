"""A5 SSO 认证服务。

生成跳转 A5 系统的安全令牌，实现跨域单点登录。
令牌包含 well_no 和 redirect_path，有效期 5 分钟。
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import create_token
from app.schemas.a5_integration import A5TokenResponse

logger = logging.getLogger(__name__)


def generate_sso_token(well_no: str, redirect_path: str = "/workorder") -> A5TokenResponse:
    """生成 A5 系统 SSO 跳转令牌。

    方案要求：
    - 前端页面与 A5 系统通过安全令牌 + 唯一 URL 参数双向绑定校验
    - 令牌有效期 5 分钟

    Args:
        well_no: 井号
        redirect_path: A5 系统内的重定向路径

    Returns:
        A5TokenResponse 包含 token, expire_at, redirect_url
    """
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    # 使用 JWT 签发临时令牌
    token, _ = create_token(
        subject=f"sso:{well_no}",
        token_type="a5_sso",
        expires_delta=timedelta(minutes=5),
    )

    # 构建 A5 跳转 URL
    a5_base = settings.a5_base_url.rstrip("/") if settings.a5_base_url else "http://a5-system"
    redirect_url = f"{a5_base}{redirect_path}?token={token}&well_no={well_no}"

    return A5TokenResponse(
        token=token,
        expire_at=expire_at,
        redirect_url=redirect_url,
    )


def verify_a5_callback_signature(
    request_headers: dict[str, str],
    request_body: str = "",
    *,
    expected_token: str | None = None,
) -> bool:
    """验证 A5 回调请求签名。

    方案要求：
    - A5 系统回调使用 HMAC-SHA256 对请求体签名
    - 签名置于 X-A5-Signature 请求头
    - 使用 A5_API_SECRET 作为 HMAC 密钥

    Args:
        request_headers: 请求头字典
        request_body: 请求体原始字符串（JSON）
        expected_token: 不用于签名验证，保留兼容旧调用方

    Returns:
        True 表示签名验证通过
    """
    # 1. 验证 IP 白名单（如果配置了的话）
    # client_ip = request_headers.get("x-forwarded-for", "").split(",")[0].strip()
    # a5_ip_whitelist = getattr(settings, "a5_ip_whitelist", "")
    # if a5_ip_whitelist and client_ip not in a5_ip_whitelist.split(","):
    #     logger.warning(f"A5 回调 IP 不在白名单: {client_ip}")
    #     return False

    # 2. 获取请求签名
    signature = request_headers.get("X-A5-Signature", "")
    if not signature:
        logger.warning("A5 回调缺少 X-A5-Signature 请求头")
        return False

    # 3. HMAC-SHA256 验证请求体签名
    secret = settings.a5_api_secret
    if not secret:
        # 未配置 secret 时，回退为宽松模式（开发环境）
        logger.warning("A5_API_SECRET 未配置，签名验证降级为仅检查签名头存在性")
        return True

    expected = hmac.new(
        secret.encode("utf-8"),
        request_body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # 4. 常数时间比对，防止时序攻击
    if not hmac.compare_digest(expected, signature):
        logger.warning(f"A5 回调签名不匹配: expected={expected[:8]}..., got={signature[:8]}...")
        return False

    return True
