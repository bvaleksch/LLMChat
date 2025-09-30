from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from jose import jwt
from passlib.context import CryptContext

from config import JWT_SECRET, JWT_ALG, JWT_EXPIRES_MIN

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p: str) -> str:
    return _pwd.hash(p)

def verify_password(p: str, h: str) -> bool:
    return _pwd.verify(p, h)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def jwt_create(sub: str) -> str:
    exp = now_utc() + timedelta(minutes=JWT_EXPIRES_MIN)
    payload: Dict[str, Any] = {"sub": sub, "exp": int(exp.timestamp())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def jwt_decode(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
