from dotenv import load_dotenv
load_dotenv()

from .media import router
from .db.session import init_db
from fastapi import FastAPI

app = FastAPI(title="Media Service")

@app.on_event("startup")
async def on_startup() -> None:
    await init_db()

app.include_router(router, prefix="/v1/media")

