import httpx
import os
from fastapi import FastAPI, Request, UploadFile, HTTPException
from fastapi.responses import Response

app = FastAPI(title="API Gateway")

SERVICES = {
    "nonce": os.getenv("NONCE_URL", "http://nonce:8000"),
    "users": os.getenv("USERS_URL", "http://users:8000"),
    "media": os.getenv("MEDIA_URL", "http://media:8000"),
    "chats": os.getenv("CHATS_URL", "http://chats:8000"),
}

async def proxy_request(method, url, headers, params, body, files):
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                content=body if not files else None,
                files=files,
            )
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Service unavailable")

    return resp



def parse_path(full_path: str):
    """
    Extract service and subpath.
    Example: 'nonce/confirm' -> service='nonce', subpath='/confirm'
    """
    parts = full_path.strip("/").split("/")
    if not parts or not parts[0]:
        return None, None
    service = parts[0]
    rest = "/" + "/".join(parts[1:]) if len(parts) > 1 else ""
    return service, rest


@app.api_route("/v1/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def gateway(request: Request, full_path: str):

    service, subpath = parse_path(full_path)

    if service not in SERVICES:
        raise HTTPException(status_code=404, detail="Unknown service")

    target_path = f"/v1/{service}{subpath}"
    target_url = SERVICES[service] + target_path

    # Headers except host
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}

    # Query parameters
    params = dict(request.query_params)

    # Extract body (for JSON / raw)
    body = await request.body()

    # Handle files if present
    files = None
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        form = await request.form()
        files = {}
        for key, value in form.items():
            if isinstance(value, UploadFile):
                files[key] = (value.filename, value.file, value.content_type)
            else:
                # Normal form fields
                files[key] = (None, value)

    resp = await proxy_request(
        method=request.method,
        url=target_url,
        headers=headers,
        params=params,
        body=body,
        files=files,
    )

    # Return proxied response
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={
            k: v for k, v in resp.headers.items()
            if k.lower() not in {"content-length", "transfer-encoding", "connection"}
        }
    )
