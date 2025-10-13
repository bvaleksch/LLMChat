from dotenv import load_dotenv
load_dotenv()

from .users import router as urouter
from .auth import router as arouter
from fastapi import FastAPI
from .db.session import init_db

app = FastAPI(title="Users Service")

@app.on_event("startup")
async def on_startup() -> None:
    await init_db()

app.include_router(urouter, prefix="/v1/users")
app.include_router(arouter, prefix="/v1/users")

