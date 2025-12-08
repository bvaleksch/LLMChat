# LLM Chat Microservices

A microservices architecture for LLM chat application with image support.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Media | 8003 | Image upload/storage |
| Nonce | 8001 | Authentication nonces |
| Users | 8002 | User auth/management |
| Chats | 8004 | Chat/message handling |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start services (from project root)
uvicorn services.media.main:app --host 185.106.95.104 --port 8003 &
uvicorn services.nonce.main:app --host 185.106.95.104 --port 8001 &
uvicorn services.users.main:app --host 185.106.95.104 --port 8002 &
uvicorn services.chats.main:app --host 185.106.95.104 --port 8004 &
```

## Configuration

```env
USERS_DATABASE_URL=postgresql+asyncpg://users_service:<password>@localhost:5433/users_service_db
MEDIA_DATABASE_URL=postgresql+asyncpg://media_service:<password>@localhost:5434/media_service_db
CHATS_DATABASE_URL=postgresql+asyncpg://chats_service:<password>@localhost:5435/chats_service_db
S3_ENDPOINT=https://storage.clo.ru
S3_BUCKET=llm-chat-images
S3_ACCESS_KEY=your_key
S3_SECRET_KEY=your_secret
JWT_DEV_SECRET=your_jwt_secret
```

Each microservice owns its own PostgreSQL database. The docker-compose file provisions three separate Postgres containers (users, media, chats) bound to host ports 5433/5434/5435 respectively.
All database credentials/URLs are sourced from the root `.env` file (see variables above); no passwords are kept in `docker-compose.yml`.

## Testing

```bash
python tests/media_service_test.py
python tests/nonce_service_test.py
python tests/users_service_test.py
python tests/chats_service_test.py
```
