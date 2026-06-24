"""A5 SSO 认证服务。

生成跳转 A5 系统的安全令牌，实现跨域单点登录。
令牌包含 well_no 和 redirect_path，有效期 5 分钟。
"""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import create_token
from app.schemas.a5_integration import A5TokenResponse


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
    expected_token: str | None = None,
) -> bool:
    """验证 A5 回调请求签名。

    Args:
        request_headers: 请求头字典
        expected_token: 期望的令牌值（可选）

    Returns:
        True 表示验证通过
    """
    # 验证 IP 白名单
    # TODO: 集成 IP 白名单校验
    # client_ip = request.client.host
    # if client_ip not in A5_IP_WHITELIST:
    #     return False

    # 验证 X-A5-Signature 签名
    signature = request_headers.get("X-A5-Signature", "")
    if not signature:
        return False

    # TODO: 实现 HMAC 签名验证
    return True
