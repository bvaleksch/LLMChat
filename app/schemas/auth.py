from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, constr


# -------- Input --------

class RegisterIn(BaseModel):
    username: constr(min_length=3, max_length=64)
    password: constr(min_length=8, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str
    user_id: UUID


# -------- Output --------

class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    id: UUID
    username: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
