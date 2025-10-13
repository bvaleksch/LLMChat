import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from strenum import StrEnum


class MemberRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ChatMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: MemberRole = MemberRole.MEMBER
    model_config = ConfigDict(from_attributes=True)


class ChatMemberOut(BaseModel):
    chat_id: uuid.UUID
    user_id: uuid.UUID
    role: MemberRole
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)

