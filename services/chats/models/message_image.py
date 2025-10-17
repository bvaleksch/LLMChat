import uuid
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base

class MessageImage(Base):
    __tablename__ = "message_images"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),  
        primary_key=True,
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    message = relationship("Message", back_populates="message_images")

    __table_args__ = (
        UniqueConstraint("message_id", "image_id", name="uq_message_image"),
    )
