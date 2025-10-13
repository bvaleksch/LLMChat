from pydantic import BaseModel

class Nonce(BaseModel):
    nonce: str

