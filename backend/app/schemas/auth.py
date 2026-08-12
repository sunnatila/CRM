from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: str
    avatar_url: str | None
    is_active: bool
    created_at: datetime


class CreateOperatorRequest(BaseModel):
    full_name: str
    username: str
    password: str
