import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base
from ..schemas.chat_member import MemberRole


class ChatMember(Base):
    __tablename__ = "chat_members"
    __table_args__ = (
        PrimaryKeyConstraint("chat_id", "user_id", name="pk_chat_user"),
    )

    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    role: Mapped[MemberRole] = mapped_column(
        SQLEnum(MemberRole, name="member_role", native_enum=True), 
        nullable=False,
        default=MemberRole.OWNER,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chat: Mapped["Chat"] = relationship("Chat")

