import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.exceptions import BusinessException
from app.core.security import decode_token_payload
from app.services.auth_service import is_access_token_revoked
from app.services.notification_service import approval_connection_manager

router = APIRouter()


def _validate_access_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        payload = decode_token_payload(token)
    except BusinessException:
        return False
    return payload.get("typ") == "access" and not is_access_token_revoked(payload.get("jti"))


async def _receive_auth_token(websocket: WebSocket) -> str | None:
    try:
        payload = await asyncio.wait_for(websocket.receive_json(), timeout=10)
    except Exception:
        return None
    if not isinstance(payload, dict) or payload.get("type") != "auth":
        return None
    token = payload.get("token")
    return token if isinstance(token, str) else None


@router.websocket("/ws/approval")
async def approval_socket(websocket: WebSocket) -> None:
    await approval_connection_manager.connect(websocket)
    try:
        token = await _receive_auth_token(websocket)
        if not _validate_access_token(token):
            await websocket.close(code=1008)
            return

        await websocket.send_json(
            {
                "title": "Approval socket connected",
                "message": "Realtime approval notifications are enabled.",
                "type": "success",
            }
        )
        while websocket.application_state == WebSocketState.CONNECTED:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        approval_connection_manager.disconnect(websocket)
