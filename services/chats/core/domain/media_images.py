import uuid
import os
import httpx
import mimetypes
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# Take base URL from environment or fallback to default
BASE_URL = os.getenv("MEDIA_SERVICE_BASE", "http://127.0.0.1:8000/v1")

def mime_to_ext(mime_type: str) -> str:
    """Convert MIME type (image/png) → extension (png)."""
    ext = mimetypes.guess_extension(mime_type or "")
    if ext:
        return ext.lstrip(".")
    if mime_type and "/" in mime_type:
        return mime_type.split("/")[-1]
    return "bin"


class MediaImage:
    """
    Represents an image stored in the media service.
    Does not cache presigned URLs, since they expire.
    """
    def __init__(self, media_id: uuid.UUID) -> None:
        self.uuid: uuid.UUID = uuid.uuid4()
        self.type: str = "MediaImage"
        self.media_id: uuid.UUID = media_id

        self.mime_type: Optional[str] = None
        self.output_format: Optional[str] = None
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        self.size_str: Optional[str] = None

    async def get_url(self) -> str:
        """Fetch a fresh presigned URL each time."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0, trust_env=False) as client:
            resp = await client.get(f"/media/{self.media_id}/url")
            if resp.is_error:
                raise RuntimeError(f"Failed to get URL: {resp.status_code} {resp.text}")

            data = resp.json()
            url = data.get("url")
            if not url:
                raise RuntimeError("Malformed response: no 'url'")
            return url

    async def load_meta(self) -> None:
        """Load image metadata (mime type, size, etc.) from the media service."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0, trust_env=False) as client:
            resp = await client.get(f"/media/{self.media_id}")
            if resp.is_error:
                raise RuntimeError(f"Failed to get metadata: {resp.status_code} {resp.text}")

            meta: Dict = resp.json()
            self.mime_type = meta.get("mime_type")
            self.output_format = mime_to_ext(self.mime_type or "")
            self.width = meta.get("width")
            self.height = meta.get("height")
            if self.width and self.height:
                self.size_str = f"{self.width}x{self.height}"

    async def get_input(self) -> Dict[str, str]:
        """Return data for sending to LLM (for example, as OpenAI input_image)."""
        url = await self.get_url()
        return {
            "type": "input_image",
            "image_url": url,
        }

    def __str__(self) -> str:
        return f"{self.type}(media_id={self.media_id})"

