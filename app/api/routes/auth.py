from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ../../db.session import get_db
from ../../models.user import User
from ../../schemas.auth import TokenOut, MeOut
from ../../core.security import verify_password, jwt_create
from ..deps import get_current_user

router = APIRouter(tags=["auth"])

@router.post("/token", response_model=TokenOut)
async def token(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return TokenOut(access_token=jwt_create(sub=user.id.hex))

@router.get("/me", response_model=MeOut)
async def me(current: User = Depends(get_current_user)):
    return MeOut(
        id=current.id,
        username=current.username,
        is_active=current.is_active,
        created_at=current.created_at,
    )
