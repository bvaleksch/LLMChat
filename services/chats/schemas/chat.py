import uuid
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from .chat_member import ChatMemberOut

class ChatCreate(BaseModel):
    title: str
    model_config = ConfigDict(from_attributes=True)


class ChatOut(BaseModel):
    id: uuid.UUID
    title: str
    created_by: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatInternal(ChatOut):
    previous_response_id: Optional[str] = None


class ExtendedChatOut(ChatOut):
    is_deleted: bool
    deleted_at: datetime | None


class ChatDetails(BaseModel):
    id: uuid.UUID
    title: str
    created_by: uuid.UUID
    created_at: datetime
    members: List[ChatMemberOut]

    model_config = ConfigDict(from_attributes=True)

