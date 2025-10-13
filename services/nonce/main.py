from dotenv import load_dotenv
load_dotenv()

from .nonce import router
from fastapi import FastAPI

app = FastAPI(title="Nonce Service")
app.include_router(router, prefix="/v1/nonce")

