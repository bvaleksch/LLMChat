from fastapi import FastAPI
from app.api.routes import auth, users
from app.db.session import init_db

app = FastAPI(title="Async Registration Service (No Email)", version="0.3.0")

@app.on_event("startup")
async def on_startup() -> None:
    await init_db()

# Routers
app.include_router(users.router)
app.include_router(auth.router)
