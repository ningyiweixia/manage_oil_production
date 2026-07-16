"""A5 SSO 认证服务。

生成跳转 A5 系统的安全令牌，实现跨域单点登录。
令牌包含 well_no 和 redirect_path，有效期 5 分钟。
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.core.security import create_token, decode_token_payload
from app.core.status_codes import A5_LINK_FAILED
from app.schemas.a5_integration import A5TokenResponse

logger = logging.getLogger(__name__)


def ensure_a5_integration_configured() -> None:
    """Fail closed unless a real A5 endpoint or explicit local mock is configured."""
    if settings.a5_mock_enabled and settings.environment == "local":
        return
    if not settings.a5_base_url or not settings.a5_api_key or not settings.a5_api_secret:
        raise BusinessException(A5_LINK_FAILED, "A5系统未接入，请先配置A5地址及认证信息")
    if not settings.a5_base_url.lower().startswith("https://"):
        raise BusinessException(A5_LINK_FAILED, "A5生产联动必须使用HTTPS地址")


def ensure_local_a5_mock_enabled() -> None:
    """Allow the built-in A5 simulator only for an explicit local demo."""
    if settings.environment != "local" or not settings.a5_mock_enabled:
        raise BusinessException(A5_LINK_FAILED, "本地A5模拟服务未启用")


def verify_a5_sso_token(token: str, *, expected_well_no: str) -> None:
    """Verify that a short-lived A5 SSO token belongs to the requested well."""
    payload = decode_token_payload(token)
    if payload.get("typ") != "a5_sso" or payload.get("sub") != f"sso:{expected_well_no}":
        raise BusinessException(A5_LINK_FAILED, "A5模拟登录凭据无效")


def generate_sso_token(
    well_no: str,
    redirect_path: str = "/workorder",
    *,
    operation_no: str | None = None,
) -> A5TokenResponse:
    """生成 A5 系统 SSO 跳转令牌。

    方案要求：
    - 前端页面与 A5 系统通过安全令牌 + 唯一 URL 参数双向绑定校验
    - 令牌有效期 5 分钟

    Args:
        well_no: 井号
        redirect_path: A5 系统内的重定向路径
        operation_no: 本系统修井运行表作业编号，用于 A5 回调精准匹配

    Returns:
        A5TokenResponse 包含 token, expire_at, redirect_url
    """
    ensure_a5_integration_configured()
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    # 使用 JWT 签发临时令牌
    token, _ = create_token(
        subject=f"sso:{well_no}",
        token_type="a5_sso",
        expires_delta=timedelta(minutes=5),
    )

    # The built-in page is deliberately local-only.  It gives demonstrations a
    # real review/issue loop without creating a fake production A5 URL.
    if settings.a5_mock_enabled and settings.environment == "local":
        a5_base = settings.a5_mock_frontend_base_url.rstrip("/")
        redirect_path = "/a5-simulator/measure-review"
    else:
        a5_base = settings.a5_base_url.rstrip("/")
    params = {"token": token, "well_no": well_no}
    if operation_no:
        params["operation_no"] = operation_no
    redirect_url = f"{a5_base}{redirect_path}?{urlencode(params)}"

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
    headers = {str(key).lower(): value for key, value in request_headers.items()}
    # 1. 验证 IP 白名单（如果配置了的话）
    client_ip = headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    if not client_ip:
        client_ip = headers.get("x-real-ip", "").strip()
    if settings.a5_allowed_ips and client_ip not in settings.a5_allowed_ips:
        logger.warning(f"A5 回调 IP 不在白名单: {client_ip or 'unknown'}")
        return False

    # 2. 获取请求签名
    signature = headers.get("x-a5-signature", "")
    if not signature:
        logger.warning("A5 回调缺少 X-A5-Signature 请求头")
        return False

    timestamp = headers.get("x-a5-timestamp", "")
    try:
        timestamp_value = int(timestamp)
    except (TypeError, ValueError):
        logger.warning("A5 callback missing or invalid timestamp")
        return False
    if abs(int(datetime.now(timezone.utc).timestamp()) - timestamp_value) > settings.a5_callback_max_skew_seconds:
        logger.warning("A5 callback timestamp outside permitted window")
        return False

    # 3. HMAC-SHA256 验证时间戳和请求体签名
    secret = settings.a5_api_secret
    if not secret:
        logger.error("A5_API_SECRET 未配置，拒绝 A5 回调")
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp_value}.{request_body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # 4. 常数时间比对，防止时序攻击
    if not hmac.compare_digest(expected, signature):
        logger.warning(f"A5 回调签名不匹配: expected={expected[:8]}..., got={signature[:8]}...")
        return False

    return True
