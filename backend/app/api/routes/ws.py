import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.services.ws_manager import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket) -> None:
    """Auth via ?token=<JWT> -- the browser WebSocket API can't send an
    Authorization header, so the access token travels as a query param instead."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        await websocket.close(code=4401)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # client sends nothing meaningful; just keeps the socket open
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)
