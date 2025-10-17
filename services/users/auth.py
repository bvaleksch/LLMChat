# app/api/routes/auth.py
import uuid
import os
from datetime import timedelta
from fastapi import APIRouter, Depends, Body, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .db.session import get_db
from .models.user import User
from .models.refresh_token import RefreshToken
from ..schemas.auth import TokenPairOut, RefreshIn, VerifyAccessIn
from .security import (
    verify_password, create_access_token,
    create_refresh_token_raw, hash_refresh_token,
    verify_refresh_token, now_utc,
    jwt_decode, require_token_type)
from .deps import get_current_user


REFRESH_EXPIRES_DAYS = int(os.getenv("REFRESH_EXPIRES_DAYS", "14"))
USERS_SERVICE_BASE = os.getenv("USERS_SERVICE_BASE", "http://185.106.95.104:8000/v1")

router = APIRouter(tags=["auth"])

async def verify_access(user_id: str, access_key: str) -> bool:
    """
    Universal user access verification via Users service.
    This avoids code duplication between microservices.
    """
    url = f"{USERS_SERVICE_BASE}/users/verify-access"
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.post(url, json={"user_id": user_id, "access_key": access_key})
            return response.status_code == 200
        except httpx.RequestError:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Users service unavailable")

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
async def refresh(payload: RefreshIn = Body(...), db: AsyncSession = Depends(get_db)):
    candidates = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == payload.user_id,
                RefreshToken.revoked == False,           
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

@router.post("/verify-access", status_code=200)
async def verify_access(payload: VerifyAccessIn, db: AsyncSession = Depends(get_db)):
    """
    Single source of truth for user verification.
    - Verifies the access JWT (signature, exp, token_type)
    - Verifies that sub in the token equals provided user_id
    - Verifies that the user exists
    """
    # 1) fully validate token (signature, exp)
    claims = jwt_decode(payload.access_key)
    require_token_type(claims, expected="access")

    # 2) sub must match user_id
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    try:
        if uuid.UUID(sub) != payload.user_id:
            raise HTTPException(status_code=401, detail="Subject mismatch")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid subject format")

    # 3) user must exist
    res = await db.execute(select(User).where(User.id == payload.user_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    return {"ok": True}

@router.post("/logout")
async def logout(payload: RefreshIn = Body(...), db: AsyncSession = Depends(get_db)):
    # 1) Get all active tokens for this user
    candidates = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == payload.user_id,
                RefreshToken.revoked == False,        
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

