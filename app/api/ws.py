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


@router.websocket("/ws/approval")
async def approval_socket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not _validate_access_token(token):
        await websocket.close(code=1008)
        return

    await approval_connection_manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "title": "审批待办监听已连接",
                "message": "实时待办提醒已开启",
                "type": "success",
            }
        )
        while websocket.application_state == WebSocketState.CONNECTED:
            await websocket.receive_text()
    except WebSocketDisconnect:
        approval_connection_manager.disconnect(websocket)
    except Exception:
        approval_connection_manager.disconnect(websocket)
