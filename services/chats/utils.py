import os
import httpx
from fastapi import HTTPException, Request, status
from ..schemas.users import UserOut

USERS_SERVICE_BASE = os.getenv("USERS_SERVICE_BASE", "http://users:8000")
USERS_ME_URL = f"{USERS_SERVICE_BASE}/users/me"
TIMEOUT = 5.0

async def get_current_user(request: Request) -> UserOut:
    """
    1. Read Authorization: Bearer <token> from headers.
    2. Forward it to users-service /users/me.
    3. If token is valid, return user.
       If not — raise HTTPException with same code.
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(USERS_ME_URL, headers={"Authorization": auth})
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Users service unavailable")

    if r.status_code != 200:
        # propagate original auth error (401/403)
        if r.status_code in (400, 401, 403, 404):
            detail = r.json().get("detail", "Access denied") if "application/json" in r.headers.get("content-type", "") else "Access denied"
            raise HTTPException(status_code=r.status_code, detail=detail)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Users verification failed")

    return UserOut.model_validate(r.json())

    