import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from strenum import StrEnum


class ImageKind(StrEnum):
    INPUT = "input"
    GEN = "gen"


class MediaOut(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    owner_id: uuid.UUID | None
    mime_type: str
    size_bytes: int 
    width: int 
    height: int 
    kind: ImageKind
    prompt: str | None

    model_config = ConfigDict(from_attributes=True)  


class MediaUrl(BaseModel):
    media_id: uuid.UUID
    url: str

