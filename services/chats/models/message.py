import uuid
from typing import List
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .message_image import MessageImage
from ..core.domain.mytypes import Role 


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chats.id"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    role: Mapped[Role] = mapped_column(
        SQLEnum(Role, name="message_role", native_enum=True),
        nullable=False,
    )

    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    chat: Mapped["Chat"] = relationship("Chat")
    message_images: Mapped[List[MessageImage]] = relationship("MessageImage", back_populates="message", lazy="selectin")

    @property
    def media_ids(self) -> List[uuid.UUID]:
        return [img.image_id for img in (self.message_images or [])]

