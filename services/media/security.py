import os
import jwt
import httpx
from typing import Optional, List

from fastapi import Header, HTTPException, Request, status
from pydantic import BaseModel
from .media_enums import PrincipalMode
#from schemas.auth import VerifyAccessIn

# === Configuration ===
JWT_SECRET = os.getenv("JWT_DEV_SECRET", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
USERS_SERVICE_BASE = os.getenv("USERS_SERVICE_BASE", "http://users:8000")
NONCE_SERVICE_BASE = os.getenv("NONCE_SERVICE_BASE", "http://185.106.95.104:8000")


class Principal(BaseModel):
    """Represents an authenticated principal (user or service)."""
    mode: PrincipalMode
    user_id: Optional[str] = None
    access_key: Optional[str] = None
    service_name: Optional[str] = None
    scopes: List[str] = []


async def verify_user_credentials(user_id: str, access_key: str) -> bool:
    """Verify user credentials via Users service."""
    url = f"{USERS_SERVICE_BASE}/users/verify-access"
    data = {"user_id": str(user_id), "access_key": access_key}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.post(url, json=data)
            return r.status_code == 200
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Users service unavailable",
            )

async def _confirm_nonce_or_401(nonce: str) -> None:
    """Confirm single-use nonce at Nonce-service."""
    url = f"{NONCE_SERVICE_BASE}/nonce/confirm"
    async with httpx.AsyncClient(timeout=3.0) as c:
        r = await c.post(url, json={"nonce": nonce})
    if r.status_code == 404:
        raise HTTPException(status_code=401, detail="Nonce not found or expired")
    if r.status_code == 409:
        raise HTTPException(status_code=401, detail="Nonce reused")
    if r.status_code != 204:
        raise HTTPException(status_code=503, detail="Nonce service unavailable")

async def get_principal(
    request: Request,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_access_key: Optional[str] = Header(default=None, alias="X-Access-Key"),
) -> Optional[Principal]:
    """
    Two authentication modes:
      - USER: X-User-Id + X-Access-Key -> verified via /users/verify-access
      - SERVICE: Bearer <JWT> (must be signed with JWT_DEV_SECRET, contain typ='service' and a valid nonce)
      - None: unauthenticated (public access)
    """
    # USER mode
    if x_user_id and x_access_key:
        r = await verify_user_credentials(x_user_id, x_access_key)
        if not r:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return Principal(mode=PrincipalMode.USER, user_id=x_user_id, access_key=x_access_key)

    # SERVICE mode
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG], options={"verify_aud": False})
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired JWT")

        # must explicitly declare itself as a service
        if payload.get("typ") != "service":
            raise HTTPException(status_code=401, detail="Invalid service token type")

        # every service JWT must have nonce and must be confirmed
        nonce = payload.get("nonce")
        if not nonce or not isinstance(nonce, str):
            raise HTTPException(status_code=400, detail="Missing nonce in service token")
        await _confirm_nonce_or_401(nonce)

        service_name = payload.get("service") or payload.get("client_id")
        return Principal(mode=PrincipalMode.SERVICE, service_name=service_name)

    # public (unauthenticated) requests
    return None

def require_user(p: Optional[Principal]) -> None:
    if not p or p.mode is not PrincipalMode.USER or not p.user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

def require_service(p: Optional[Principal]) -> None:
    if not p or p.mode is not PrincipalMode.SERVICE:
        raise HTTPException(status_code=401, detail="Service authentication required")

