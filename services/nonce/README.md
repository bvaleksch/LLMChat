# Nonce Service

Single-use authentication tokens for service communication.

## Endpoints

- `POST /v1/nonce` - Generate nonce
- `POST /v1/nonce/confirm` - Confirm nonce (consumes it)

## Configuration

```env
NONCE_BYTES=32
NONCE_TTL=30
```

## Start

```bash
# From project root
uvicorn services.nonce.main:app --host 185.106.95.104 --port 8001
```

**Note**: Uses in-memory storage. Replace with Redis for production.
