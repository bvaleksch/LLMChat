import uuid
from datetime import datetime
from pydantic import BaseModel, constr

class RegisterIn(BaseModel):
    username: constr(min_length=3, max_length=64)
    password: constr(min_length=8, max_length=128)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MeOut(BaseModel):
    id: uuid.UUID
    username: str
    is_active: bool
    created_at: datetime
