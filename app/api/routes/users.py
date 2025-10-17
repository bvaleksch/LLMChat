from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RegisterIn
from app.core.security import hash_password

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
