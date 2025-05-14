from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    refresh_token: str  # Added refresh token
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None  # Subject (usually username or user ID)
    user_id: Optional[int] = None
