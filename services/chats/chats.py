# app/api/routes/chats.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from .db.session import get_db
from .models.chat import Chat
from .models.chat_member import ChatMember
from schemas.users import UserOut
from .utils import get_current_user
from .schemas.chat import ChatCreate, ChatOut, ChatDetails
from .schemas.chat_member import ChatMemberCreate as ChatMemberAdd
from .schemas.chat_member import ChatMemberOut, MemberRole


router = APIRouter(tags=["chats"])


async def _ensure_member(db: AsyncSession, chat_id: UUID, user_id: UUID) -> ChatMember:
    q = select(ChatMember).where(
        ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
    )
    res = await db.execute(q)
    cm = res.scalar_one_or_none()
    if not cm:
        raise HTTPException(status_code=403, detail="Not a chat member")
    return cm


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
async def create_chat(
    payload: ChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """Create chat and assign current user as owner."""
    chat = Chat(title=payload.title, created_by=current_user.id)
    db.add(chat)
    await db.flush() 

    owner = ChatMember(chat_id=chat.id, user_id=current_user.id, role=MemberRole.OWNER)
    db.add(owner)

    await db.commit()
    await db.refresh(chat)
    return ChatOut(id=chat.id, title=chat.title, created_by=chat.created_by, created_at=chat.created_at)


@router.get("/", response_model=List[ChatOut])
async def list_my_chats(
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """List chats where current user is a member."""
    q = (
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(ChatMember.user_id == current_user.id)
        .order_by(Chat.created_at.desc())
    )
    res = await db.execute(q)
    chats = res.scalars().all()
    return [ChatOut(id=c.id, title=c.title, created_by=c.created_by, created_at=c.created_at) for c in chats]


@router.get("/{chat_id}", response_model=ChatDetails)
async def get_chat(
    chat_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """Get chat info with members (no messages)."""
    res = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = res.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    await _ensure_member(db, chat_id, current_user.id)

    res_m = await db.execute(select(ChatMember).where(ChatMember.chat_id == chat_id))
    members = res_m.scalars().all()

    return ChatDetails(
        id=chat.id,
        title=chat.title,
        created_by=chat.created_by,
        created_at=chat.created_at,
        members=[
            {"chat_id": chat.id, "user_id": m.user_id, "role": m.role.value, "joined_at": m.joined_at}
            for m in members
        ],
    )


@router.post("/{chat_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_member(
    chat_id: UUID,
    payload: ChatMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    cm = await _ensure_member(db, chat_id, current_user.id)
    if (cm.role != MemberRole.OWNER) and (cm.role != MemberRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only owner or admin can add members")

    # avoid duplicates
    q = select(ChatMember).where(
        ChatMember.chat_id == chat_id, ChatMember.user_id == payload.user_id
    )
    res = await db.execute(q)
    exists = res.scalar_one_or_none()
    if exists:
        return

    db.add(
        ChatMember(
            chat_id=chat_id,
            user_id=payload.user_id,
            role=MemberRole(payload.role) if hasattr(payload, "role") else MemberRole.member,
        )
    )
    await db.commit()

@router.get("/{chat_id}/members", response_model=List[ChatMemberOut])
async def list_chat_members(
    chat_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    res = await db.execute(
        select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == current_user.id)
    )
    me = res.scalar_one_or_none()
    if not me:
        raise HTTPException(status_code=403, detail="Not a chat member")

    # list all members
    res = await db.execute(select(ChatMember).where(ChatMember.chat_id == chat_id))
    members = res.scalars().all()
    return [ChatMemberOut.from_orm(m) for m in members]


