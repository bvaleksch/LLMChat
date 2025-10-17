# app/api/routes/messages.py
import httpx
import time
import base64
import jwt
import uuid
import os
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, exists
from sqlalchemy.orm import selectinload

from .utils import get_current_user
from .db.session import get_db
from ..schemas.users import UserOut
from .schemas.chat_member import ChatMemberOut
from .models.chat_member import ChatMember
from .models.message_image import MessageImage
from .models.message import Message as MessageModel
from .core.domain.message import Message
from .core.domain.media_images import MediaImage
from .core.domain.images import GenImage
from .core.domain.chat import Chat
from .core.domain.mytypes import Role as MessageRole
from .models.chat import Chat as ChatModel
from .schemas.message import MessageCreate, MessageOut


NONCE_SERVICE_BASE = os.getenv("NONCE_SERVICE_BASE", "http://nonce-service:8000")
JWT_DEV_SECRET = os.getenv("JWT_DEV_SECRET", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
MEDIA_SERVICE_BASE = os.getenv("MEDIA_SERVICE_BASE", "http://media-service:8000")


router = APIRouter(prefix="/{chat_id}/messages", tags=["messages"])


async def _ensure_member(db: AsyncSession, chat_id: UUID, user_id: UUID) -> None:
    """
    Ensure that user is a member of the given chat.
    Raises 403 if not.
    Uses EXISTS for efficiency.
    """
    stmt = select(
        exists().where(
            (ChatMember.chat_id == chat_id) &
            (ChatMember.user_id == user_id)
        )
    )
    result = await db.execute(stmt)
    is_member = result.scalar()

    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a chat member")

@router.get("", response_model=List[MessageOut])
async def list_messages(
    chat_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    after: Optional[UUID] = Query(None, description="Return messages created after this message id"),
) -> List[MessageOut]:
    """List messages in a chat (newest first). Only for chat members."""
    await _ensure_member(db, chat_id, current_user.id)

    base = select(MessageModel).where(
        MessageModel.chat_id == chat_id,
        MessageModel.is_deleted == False,  # safety: if soft-delete exists
    )

    if after:
        anchor_res = await db.execute(select(MessageModel).where(MessageModel.id == after, MessageModel.chat_id == chat_id))
        anchor = anchor_res.scalar_one_or_none()
        if not anchor:
            raise HTTPException(status_code=404, detail="Anchor message not found")
        base = base.where(MessageModel.created_at > anchor.created_at)

    q = base.order_by(desc(MessageModel.created_at)).limit(limit)
    res = await db.execute(q)

    items = res.scalars().all()
    return [MessageOut.model_validate(m) for m in items]

async def gen_img2media_id(
    img: "GenImage",
    chat_id: UUID,
    prompt: Optional[str] = None,
    service_name: str = "chat-service",
    jwt_ttl_sec: int = 60,
) -> UUID:
    """
    Uploads a generated image to the media service as a SERVICE
    and returns the media_id (UUID).
    """

    async with httpx.AsyncClient(base_url=NONCE_SERVICE_BASE, timeout=5.0, trust_env=False) as client:
        resp = await client.post("/nonce")
        resp.raise_for_status()
        nonce = resp.json()["nonce"]

    now = int(time.time())
    claims = {
        "typ": "service",
        "service": service_name,
        "nonce": nonce,
        "iat": now,
        "exp": now + jwt_ttl_sec,
    }
    token = jwt.encode(claims, JWT_DEV_SECRET, algorithm=JWT_ALG)

    try:
        image_bytes = base64.b64decode(img.data)
    except Exception as e:
        raise RuntimeError(f"Failed to decode base64 image data: {e}") from e

    output_fmt = (img.output_format or "png").lower()
    files = {
        "file": (f"{uuid.uuid4().hex}.{output_fmt}", image_bytes, f"image/{output_fmt}"),
    }
    data = {
        "prompt": (prompt or getattr(img, "prompt", None) or ""),
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Chat-Id": str(chat_id),
    }

    async with httpx.AsyncClient(base_url=MEDIA_SERVICE_BASE, timeout=30.0, trust_env=False) as client:
        resp = await client.post("/media", headers=headers, files=files, data=data)
        if resp.is_error:
            raise RuntimeError(f"Media upload failed: {resp.status_code} {resp.text}")

        data = resp.json()
        mid = data.get("id") or data.get("media_id")
        if not mid:
            raise RuntimeError(f"Malformed response: {data}")

    return UUID(mid)

async def generate_model_answer(
    chat_id: UUID,
    message: MessageCreate,
    db: AsyncSession,
) -> MessageOut:
    """
    Generate assistant reply with the domain Chat/Message,
    upload generated images to Media service, persist assistant message,
    and return it.
    """
    res = await db.execute(select(ChatModel).where(ChatModel.id == chat_id))
    chat_model = res.scalar_one_or_none()
    if not chat_model:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat = Chat(chat_model.title, chat_model.previous_response_id)
    user_msg = Message(MessageRole.USER, message.text)
    for media_id in (message.media_ids or []):
        user_msg.attach_image(MediaImage(media_id))

    response = await chat.send(user_msg)

    gen_media_ids: List[UUID] = []
    for gen_img in (getattr(response, "images", None) or []):
        mid = await gen_img2media_id(gen_img, chat_id=chat_model.id)
        gen_media_ids.append(mid)

    assistant_msg = MessageModel(
        chat_id=chat_id,
        author_id=None,
        role=MessageRole.ASSISTANT,
        text=response.text,
    )
    db.add(assistant_msg)
    await db.flush()

    chat_model.previous_response_id = chat.previous_response_id
    for mid in gen_media_ids:
        db.add(MessageImage(message_id=assistant_msg.id, image_id=mid))

    await db.commit()
    await db.refresh(assistant_msg)

    return MessageOut.model_validate(assistant_msg)

@router.post("/send", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """
    Send a message in a chat.

    - role is enforced by server: 'user'
    - text length is unrestricted
    - image/media attachments handled separately by Media service
    """
    # Ensure current user is member of chat
    await _ensure_member(db, chat_id, current_user.id)

    msg = MessageModel(
        chat_id=chat_id,
        author_id=current_user.id,
        role=MessageRole.USER,
        text=payload.text,
    )
    db.add(msg)
    await db.flush()

    for mid in payload.media_ids:
        db.add(MessageImage(message_id=msg.id, image_id=mid))

    await db.commit()

    return await generate_model_answer(chat_id, payload, db)

@router.get("/{message_id}", response_model=MessageOut)
async def get_message(
    chat_id: UUID,
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """Get a single message by id. Only for chat members."""
    await _ensure_member(db, chat_id, current_user.id)

    res = await db.execute(
        select(MessageModel).where(MessageModel.id == message_id, MessageModel.chat_id == chat_id, MessageModel.is_deleted == False)
    )
    msg = res.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return MessageOut.from_orm(msg)

