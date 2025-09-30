# app/api/routes/auth.py
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import TokenPairOut, RefreshIn
from app.core.security import (
    verify_password, create_access_token,
    create_refresh_token_raw, hash_refresh_token,
    verify_refresh_token, now_utc)
from app.api.deps import get_current_user
from app.core.config import REFRESH_EXPIRES_DAYS

router = APIRouter(tags=["auth"])

@router.post("/token", response_model=TokenPairOut)
async def token(form: OAuth2PasswordRequestForm = Depends(),
                db: AsyncSession = Depends(get_db)):
    # username/password login
    user = (await db.execute(select(User).where(User.username == form.username))).scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    # issue access
    access = create_access_token(sub=str(user.id))

    # issue refresh (rotate any existing if you want single-session)
    raw = create_refresh_token_raw()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw),
        expires_at=now_utc() + timedelta(days=REFRESH_EXPIRES_DAYS)  
    )
    db.add(rt)
    await db.commit()
    return TokenPairOut(access_token=access, refresh_token=raw)

@router.post("/token/refresh", response_model=TokenPairOut)
async def refresh(payload: RefreshIn, db: AsyncSession = Depends(get_db)):
    candidates = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == payload.user_id,
                RefreshToken.revoked == False,            # noqa: E712
                RefreshToken.expires_at >= now_utc(),
            )
        )
    ).scalars().all()

    matched = None
    for t in candidates:
        if verify_refresh_token(payload.refresh_token, t.token_hash):
            matched = t
            break

    if not matched:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Rotate only the matched token
    matched.revoked = True
    new_secret = create_refresh_token_raw()
    db.add(
        RefreshToken(
            user_id=matched.user_id,
            parent_id=matched.id,
            token_hash=hash_refresh_token(new_secret),
            expires_at=now_utc() + timedelta(days=REFRESH_EXPIRES_DAYS),
        )
    )

    access = create_access_token(sub=str(matched.user_id))
    await db.commit()
    return TokenPairOut(access_token=access, refresh_token=new_secret)


@router.post("/logout")
async def logout(payload: RefreshIn, db: AsyncSession = Depends(get_db)):
    # 1) Get all active tokens for this user
    candidates = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == payload.user_id,
                RefreshToken.revoked == False,        # noqa: E712
                RefreshToken.expires_at >= now_utc(),
            )
        )
    ).scalars().all()

    # 2) Find the one matching the provided secret
    matched = None
    for t in candidates:
        if verify_refresh_token(payload.refresh_token, t.token_hash):
            matched = t
            break

    if not matched:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token not found or already revoked",
        )

    # 3) Revoke just this token
    matched.revoked = True
    await db.commit()

    return {"message": "Logged out"}

