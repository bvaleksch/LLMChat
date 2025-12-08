from fastapi import FastAPI, Request, UploadFile, HTTPException
from fastapi.responses import Response
import httpx

app = FastAPI(title="API Gateway")

SERVICES = {
    "nonce": "http://nonce:8001",
    "users": "http://users:8002",
    "media": "http://media:8003",
    "chats": "http://chats:8004",
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
    /v1/users/login → service='users', subpath='/login'
    """
    parts = full_path.strip("/").split("/")

    if len(parts) < 2:
        return None, None

    version = parts[0]
    service = parts[1]
    rest = "/" + "/".join(parts[2:]) if len(parts) > 2 else ""

    return service, rest


@app.api_route("/v1/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def gateway(request: Request, full_path: str):

    service, subpath = parse_path(full_path)

    if service not in SERVICES:
        raise HTTPException(status_code=404, detail="Unknown service")

    target_url = SERVICES[service] + subpath

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
