from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .deps import get_current_user, resolve_user_from_token
from .db.session import get_db
from .models.user import User
from ..schemas.users import UserOut, TokenIn
from ..schemas.auth import RegisterIn
from .security import hash_password

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

@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """
    Return info about the currently authenticated user.
    Uses the Authorization: Bearer <token> header.
    """
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )

@router.post("/get_user", response_model=UserOut)
async def get_user(
    payload: TokenIn,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """
    Return user info by access_token provided in JSON body:
    {
        "access_token": "<token>"
    }
    """
    user = await resolve_user_from_token(payload.access_token, db)
    return UserOut(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        created_at=user.created_at,
    )
