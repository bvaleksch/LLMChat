from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: UUID = Field(..., description="Unique user ID")
    username: str = Field(..., max_length=64, description="Username")
    is_active: bool = Field(..., description="Whether the user account is active")
    created_at: datetime = Field(..., description="Datetime of user creation (UTC)")


class TokenIn(BaseModel):
    access_token: str

    