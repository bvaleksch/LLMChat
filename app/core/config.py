import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_EXPIRES_MIN = int(os.getenv("ACCESS_EXPIRES_MIN", "15"))
REFRESH_EXPIRES_DAYS = int(os.getenv("REFRESH_EXPIRES_DAYS", "30"))
REFRESH_TOKEN_BYTES = int(os.getenv("REFRESH_TOKEN_BYTES", "32"))
