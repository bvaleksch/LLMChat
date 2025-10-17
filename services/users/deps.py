# deps.py
import uuid
import os
import jwt
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db.session import get_db
from .models.user import User

auth_scheme = OAuth2PasswordBearer(tokenUrl="/token")
USERS_SERVICE_BASE = os.getenv("USERS_SERVICE_BASE", "http://95.81.117.253:8000")

async def _users_verify_access(user_id: uuid.UUID, access_key: str) -> None:
    url = f"{USERS_SERVICE_BASE}/users/verify-access"
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.post(url, json={"user_id": str(user_id), "access_key": access_key})
        except httpx.RequestError:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Users service unavailable")
    if r.status_code != 200:
        if r.status_code in (400, 401, 403, 404):
            raise HTTPException(status_code=r.status_code, detail=r.json().get("detail", "Access denied"))
        raise HTTPException(status_code=500, detail="Users verification failed")

def _extract_sub_unverified(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        sub = payload.get("sub")
        return uuid.UUID(sub)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed access token")

async def resolve_user_from_token(token: str, db: AsyncSession) -> User:
    """
    1) Read user_id from token (unverified).
    2) Verify access remotely via Users service.
    3) Load user profile from DB and return it.
    """
    uid = _extract_sub_unverified(token)
    await _users_verify_access(uid, token)

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_current_user(
    token: str = Depends(auth_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await resolve_user_from_token(token, db)
