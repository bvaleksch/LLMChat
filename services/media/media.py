# app/api/routes/media.py
import os
import uuid
import hashlib
from io import BytesIO
from typing import Optional

import aioboto3
from PIL import Image
from fastapi import (
    APIRouter, Depends, UploadFile, File,
    HTTPException, status, Header, Form
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .db.session import get_db
from .models.image import Image as ImageModel
from ..schemas.media import ImageKind  
from .media_enums import PrincipalMode
from ..schemas.media import MediaOut
from .security import (
    get_principal, require_user, require_service,
    Principal
)

router = APIRouter(tags=["media"])

# S3 config (bucket must already exist)
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "https://storage.clo.ru")
S3_BUCKET = os.getenv("S3_BUCKET", "llm-chat-images")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
PRESIGN_EXPIRES = int(os.getenv("S3_PRESIGN_TTL", "900"))  # seconds


def _s3_client():
    """Create aioboto3 S3 client (bucket must already exist)."""
    return aioboto3.Session().client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )


async def _get_image_size(content: bytes) -> tuple[Optional[int], Optional[int]]:
    """Best-effort detect width and height for an image."""
    try:
        with Image.open(BytesIO(content)) as im:
            return im.width, im.height
    except Exception:
        return None, None


def _make_key(chat_id: str, media_id: uuid.UUID, filename: str | None) -> str:
    """Build S3 object key."""
    ext = ""
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[1].lower()
    return f"chats/{chat_id}/{media_id}{ext}"


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    x_chat_id: str = Header(..., alias="X-Chat-Id"),
    prompt: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    principal: Optional[Principal] = Depends(get_principal),
):
    """
    Upload image to S3 and persist metadata.
    - USER: verified via /users/verify-access inside get_principal(),
             MUST be ImageKind.input, prompt ignored.
    - SERVICE: verified via Bearer JWT (typ=service + nonce confirmed in get_principal()),
               MUST provide X-Prompt, saved as ImageKind.gen.
    - Reads are public; writes require USER or SERVICE.
    """
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    w, h = await _get_image_size(content)
    sha256 = hashlib.sha256(content).hexdigest()
    media_id = uuid.uuid4()
    key = _make_key(x_chat_id, media_id, file.filename)
    mime = file.content_type or "application/octet-stream"

    # enforce per-mode rules
    if principal.mode is PrincipalMode.USER:
        require_user(principal)
        kind = ImageKind.INPUT
        prompt = None  # user prompt is prohibited
    elif principal.mode is PrincipalMode.SERVICE:
        require_service(principal)
        if not prompt or not prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt is required for service uploads")
        kind = ImageKind.GEN
        prompt = prompt.strip()
    else:
        raise HTTPException(status_code=401, detail="Unsupported principal mode")

    # upload object to S3 (bucket must already exist)
    async with _s3_client() as s3:
        try:
            await s3.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=content,
                ContentType=mime,
            )
        except s3.exceptions.NoSuchBucket:
            raise HTTPException(
                status_code=500,
                detail=f"S3 bucket '{S3_BUCKET}' does not exist. Create it manually before running the service.",
            )

    # persist metadata
    img = ImageModel(
        id=media_id,
        chat_id=uuid.UUID(x_chat_id),
        owner_id=uuid.UUID(principal.user_id) if principal.mode is PrincipalMode.USER else None,
        kind=kind,                 # enum
        mime_type=mime,
        width=w,
        height=h,
        size_bytes=len(content),
        sha256=sha256,
        storage_url=key,           
        prompt=prompt,             
    )

    db.add(img)
    await db.commit()
    return {"id": str(img.id)}


@router.get("/{media_id}", response_model=MediaOut)
async def get_media_meta(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Public: return metadata for an image by id."""
    res = await db.execute(select(ImageModel).where(ImageModel.id == media_id))
    img = res.scalar_one_or_none()

    if not img or img.is_deleted:
        raise HTTPException(status_code=404, detail="Not found")

    return MediaOut.model_validate(img)


@router.get("/{media_id}/url")
async def get_presigned_url(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Public: return a presigned URL for downloading the file."""
    res = await db.execute(select(ImageModel).where(ImageModel.id == media_id))
    img = res.scalar_one_or_none()
    if not img or img.is_deleted:
        raise HTTPException(404, "Not found")

    async with _s3_client() as s3:
        try:
            url = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": img.storage_url},
                ExpiresIn=PRESIGN_EXPIRES,
            )
        except s3.exceptions.NoSuchBucket:
            raise HTTPException(status_code=500, detail=f"Bucket '{S3_BUCKET}' not found.")
    return {"media_id": str(img.id), "url": url}

