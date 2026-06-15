from typing import Any

from fastapi import WebSocket


class ApprovalConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for websocket in list(self._connections):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)


approval_connection_manager = ApprovalConnectionManager()


async def push_geology_todo(payload: dict[str, Any]) -> None:
    await approval_connection_manager.broadcast(
        {
            "title": "审批待办提醒",
            "message": "、".join(payload.get("well_nos", [])) + " 已提交至地质核实",
            "node_code": "PENDING_GEOLOGY_VERIFY",
            "type": "info",
            **payload,
        }
    )


async def push_status_changed(payload: dict[str, Any]) -> None:
    await approval_connection_manager.broadcast(
        {
            "title": "审批状态更新",
            "message": f"{payload.get('well_no', '项目')} 已流转至 {payload.get('node_code', '新节点')}",
            "type": "success",
            **payload,
        }
    )
