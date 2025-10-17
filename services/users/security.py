import secrets
import base64
import bcrypt   
import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException, status


JWT_SECRET = os.getenv("JWT_SECRET", "jwt-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_EXPIRES_MIN = int(os.getenv("ACCESS_EXPIRES_MIN", "15"))
REFRESH_EXPIRES_DAYS = int(os.getenv("REFRESH_EXPIRES_DAYS", "14"))
REFRESH_TOKEN_BYTES = int(os.getenv("REFRESH_TOKEN_BYTES", "64"))


# ---------- Password helpers ----------
def hash_password(p: str) -> str:
    return base64.b64encode(bcrypt.hashpw(p.encode("utf8"), bcrypt.gensalt())).decode("utf8")

def verify_password(p: str, h: str) -> bool:
    hash_value = base64.b64decode(h.encode("utf8"))
    return bcrypt.checkpw(p.encode("utf8"), hash_value)


# ---------- Time ----------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------- Access token (JWT) ----------
def create_access_token(sub: str) -> str:
    exp = now_utc() + timedelta(minutes=ACCESS_EXPIRES_MIN)
    payload: Dict[str, Any] = {"sub": sub, "exp": int(exp.timestamp()), "typ": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


# ---------- Refresh token (opaque string) ----------
def create_refresh_token_raw() -> str:
    # random, URL-safe string; send to client, store only a hash server-side
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)

def hash_refresh_token(rt: str) -> str:
    return hash_password(rt)

def verify_refresh_token(rt: str, h: str) -> bool:
    return verify_password(rt, h)


# ---------- Decode & validate JWT ----------
def jwt_decode(token: str) -> Dict[str, Any]:
    """Decode JWT (access or any JWT you issue). Raises 401 on failure."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def require_token_type(payload: Dict[str, Any], expected: str) -> None:
    """Ensure the 'typ' claim matches (e.g., 'access')."""
    typ = payload.get("typ")
    if typ != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Wrong token type: expected '{expected}', got '{typ or 'unknown'}'",
        )

