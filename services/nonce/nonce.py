import os
import time
import secrets
import asyncio
from typing import Dict, Tuple

from fastapi import APIRouter, HTTPException, status
from ..schemas.nonce import Nonce

router = APIRouter(tags=["nonce"])

# Config
NONCE_BYTES = int(os.getenv("NONCE_BYTES", "32"))   # 32 bytes -> 64 hex chars
NONCE_TTL   = int(os.getenv("NONCE_TTL", "30"))     # seconds

# In-memory storage: nonce -> (used: bool, expires_at: float)
_storage: Dict[str, Tuple[bool, float]] = {}
_lock = asyncio.Lock()


def _now() -> float:
    return time.time()


async def _cleanup_expired() -> None:
    """Remove expired nonces from in-memory storage."""
    now = _now()
    to_del = [k for k, (_, exp) in _storage.items() if exp <= now]
    for k in to_del:
        _storage.pop(k, None)


@router.post("", response_model=Nonce, status_code=status.HTTP_201_CREATED)
async def issue_nonce() -> Nonce:
    """
    Issue a fresh nonce (hex) and store it as 'unused' with TTL.
    This is an in-memory prototype; replace with Redis in microservice form.
    """
    async with _lock:
        await _cleanup_expired()

        # Try until we get a unique value (extremely unlikely to collide)
        while True:
            value = secrets.token_hex(NONCE_BYTES)
            if value not in _storage:
                break

        _storage[value] = (False, _now() + NONCE_TTL)
        return Nonce(nonce=value)


@router.post("/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_nonce(body: Nonce) -> None:
    """
    Mark the provided nonce as used and immediately remove it.
    - 404 if not found or expired
    """
    async with _lock:
        await _cleanup_expired()

        rec = _storage.pop(body.nonce, None)
        if rec is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="nonce not found or expired")

        # if record existed — just confirm once and delete
        return

