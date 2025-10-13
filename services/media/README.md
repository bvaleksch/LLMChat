# Media Service

Image upload and storage service.

## Endpoints

- `POST /v1/media` - Upload image (requires auth)
- `GET /v1/media/{id}` - Get image metadata
- `GET /v1/media/{id}/url` - Get download URL

## Authentication

**User**: `X-User-Id` + `X-Access-Key` headers
**Service**: `Authorization: Bearer <JWT>` (with nonce)

## Configuration

```env
S3_ENDPOINT=https://storage.clo.ru
S3_BUCKET=llm-chat-images
S3_ACCESS_KEY=your_key
S3_SECRET_KEY=your_secret
USERS_SERVICE_BASE=http://localhost:8002
NONCE_SERVICE_BASE=http://localhost:8001
```

## Start

```bash
# From project root
uvicorn services.media.main:app --host 185.106.95.104 --port 8003
```
