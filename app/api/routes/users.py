from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...models.user import User
from ...schemas.auth import RegisterIn
from ...core.security import hash_password
from app.schemas.auth import MeOut
from app.api.deps import get_current_user

router = APIRouter(tags=["users"])

@router.post("/register", status_code=201)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    exists = await db.scalar(select(func.count()).select_from(User).where(User.username == payload.username))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    await db.commit()
    return {"message": "User created"}

@router.get("/me", response_model=MeOut)
async def read_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    """
    Return info about the currently authenticated user.
    Uses the access token for authentication.
    """
    return MeOut(
        id=current_user.id,
        username=current_user.username,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )

