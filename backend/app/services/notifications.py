from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.services.ws_manager import manager


async def notify(session: AsyncSession, *, user_id: int, message: str, link: str | None = None) -> None:
    """AD-9: written in the same transaction as the event that causes it, then
    pushed immediately over the user's WebSocket connection if they have one
    open. The DB row is still the source of truth (GET /notifications on
    reconnect/cold load) -- the socket is a delivery shortcut, not a second copy."""
    notification = Notification(user_id=user_id, message=message, link=link)
    session.add(notification)
    await session.flush()

    await manager.send_to_user(
        user_id,
        {
            "id": notification.id,
            "message": notification.message,
            "link": notification.link,
            "read": notification.read,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        },
    )
