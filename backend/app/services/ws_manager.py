from __future__ import annotations

from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """In-memory per-user WebSocket registry. Single-process only (this app runs
    one uvicorn worker) -- fine for AD-9's scope, would need a shared broker
    (e.g. Redis pub/sub) if the backend ever scales to multiple workers/replicas."""

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        conns = self._connections.get(user_id)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, payload: dict[str, Any]) -> None:
        await self._send(self._connections.get(user_id), payload)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Everyone with an open socket. Used for lead status changes so one
        operator claiming a lead makes it disappear from everyone else's queue
        without them refreshing (FR-15). Best-effort: the REST list stays
        authoritative, so a dropped frame costs a stale row, not correctness."""
        for conns in list(self._connections.values()):
            await self._send(conns, payload)

    async def _send(self, conns: set[WebSocket] | None, payload: dict[str, Any]) -> None:
        if not conns:
            return
        dead: list[WebSocket] = []
        for ws in list(conns):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001 -- a dead socket must not break the caller
                dead.append(ws)
        for ws in dead:
            conns.discard(ws)


manager = ConnectionManager()
