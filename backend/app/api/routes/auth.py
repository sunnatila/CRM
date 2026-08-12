import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

_AVATAR_DIR = Path(__file__).resolve().parents[2] / "static" / "avatars"
_ALLOWED_AVATAR_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post("/login", response_model=TokenOut)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenOut:
    user = (await session.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="incorrect username or password")

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    if file.content_type not in _ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=400, detail="only PNG/JPEG/WEBP images are allowed")

    _AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[file.content_type]
    filename = f"{uuid.uuid4().hex}.{ext}"
    contents = await file.read()
    (_AVATAR_DIR / filename).write_bytes(contents)

    user.avatar_url = f"/static/avatars/{filename}"
    await session.commit()
    await session.refresh(user)
    return user
