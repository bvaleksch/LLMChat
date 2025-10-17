import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from ..core.domain.mytypes import Role as MessageRole

class MessageOut(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    author_id: Optional[uuid.UUID]
    role: MessageRole
    text: str
    created_at: datetime
    media_ids: List[uuid.UUID] = []

    model_config = ConfigDict(from_attributes=True)  


class ExtendedMessageOut(MessageOut):
    is_deleted: bool
    deleted_at: datetime | None


class MessageCreate(BaseModel):
    text: str          
    media_ids: List[uuid.UUID] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)  

