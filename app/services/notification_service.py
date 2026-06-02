from typing import Any


async def push_geology_todo(payload: dict[str, Any]) -> None:
    """WebSocket TODO hook.

    The concrete connection manager will be wired in the collaboration module.
    Keeping this awaitable makes the project-pool submit flow ready for
    websocket fan-out without coupling CRUD code to transport state.
    """

    return None
