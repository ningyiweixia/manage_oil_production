from typing import Any

from fastapi import WebSocket

STATUS_LABELS = {
    "DRAFT": "草稿",
    "PENDING_GEOLOGY_VERIFY": "待地质核实",
    "PENDING_PROCESS_VERIFY": "待工艺核实",
    "APPROVED": "入运行库",
    "REJECTED": "已驳回",
    "DISPATCHED": "已派工",
    "VOIDED": "已作废",
}

STATUS_MESSAGES = {
    "DRAFT": "{well_no} 已退回草稿",
    "PENDING_GEOLOGY_VERIFY": "{well_no} 已提交至地质核实",
    "PENDING_PROCESS_VERIFY": "{well_no} 已流转至工艺核实",
    "APPROVED": "{well_no} 已通过审批，进入运行库",
    "REJECTED": "{well_no} 已驳回，待补充修改",
    "DISPATCHED": "{well_no} 已派工",
    "VOIDED": "{well_no} 已作废",
}


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


def _status_label(node_code: Any) -> str:
    return STATUS_LABELS.get(str(node_code), "新节点")


def _status_message(well_no: Any, node_code: Any) -> str:
    code = str(node_code)
    project_name = str(well_no or "项目")
    template = STATUS_MESSAGES.get(code, "{well_no} 状态已更新")
    return template.format(well_no=project_name)


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
    node_label = _status_label(payload.get("node_code"))
    await approval_connection_manager.broadcast(
        {
            "title": "审批状态更新",
            "message": _status_message(payload.get("well_no"), payload.get("node_code")),
            "type": "success",
            **payload,
            "node_label": node_label,
        }
    )
