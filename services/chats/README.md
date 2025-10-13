# Chats Service

Chat and message management.

## Endpoints

- `POST /v1/chats` - Create chat
- `GET /v1/chats/` - List user's chats
- `GET /v1/chats/{id}` - Get chat details
- `POST /v1/chats/{id}/members` - Add member
- `GET /v1/chats/{id}/members` - List members

## Authentication

`Authorization: Bearer <JWT_TOKEN>`

## Configuration

```env
DATABASE_URL=postgresql://user:password@localhost:5432/llm_chat
```

## Start

```bash
# From project root
uvicorn services.chats.main:app --host 185.106.95.104 --port 8004
```
