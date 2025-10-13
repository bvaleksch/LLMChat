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


class VerifyAccessIn(BaseModel):
    user_id: UUID
    access_key: str


# -------- Output --------

class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

