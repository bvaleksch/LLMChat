# Users Service

User authentication and management.

## Endpoints

- `POST /v1/users/register` - Register user
- `GET /v1/users/me` - Get current user (requires auth)
- `POST /v1/users/get_user` - Get user by token

## Authentication

`Authorization: Bearer <JWT_TOKEN>`

## Configuration

```env
DATABASE_URL=postgresql://user:password@localhost:5432/llm_chat
JWT_DEV_SECRET=your_jwt_secret
```

## Start

```bash
# From project root
uvicorn services.users.main:app --host 185.106.95.104 --port 8002
```
