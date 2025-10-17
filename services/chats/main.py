import os

from dotenv import load_dotenv
load_dotenv()

from .chats import router as crouter
from .messages import router as mrouter
from .db.session import init_db
from fastapi import FastAPI

app = FastAPI(title="Chats Service")

@app.on_event("startup")
async def on_startup() -> None:
    await init_db()

print("DATABASE_URL:", os.getenv("DATABASE_URL", "DATABASE_URL"))

app.include_router(crouter, prefix="/v1/chats")
app.include_router(mrouter, prefix="/v1/chats")

