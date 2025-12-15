import httpx
import os
import itertools
from fastapi import FastAPI, Request, UploadFile, HTTPException
from fastapi.responses import Response

app = FastAPI(title="API Gateway")

# ====== BACKENDS ======
MEDIA_BACKENDS = os.getenv(
    "MEDIA_BACKENDS",
    "http://media_1:8000,http://media_2:8000,http://media_3:8000"
).split(",")

media_rr = itertools.cycle(MEDIA_BACKENDS)

SERVICES = {
    "nonce": [os.getenv("NONCE_URL", "http://nonce:8000")],
    "users": [os.getenv("USERS_URL", "http://users:8000")],
    "chats": [os.getenv("CHATS_URL", "http://chats:8000")],
    "media": MEDIA_BACKENDS,
}


def pick_backend(service: str) -> str:
    if service == "media":
        return next(media_rr)
    return SERVICES[service][0]


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
    parts = full_path.strip("/").split("/")
    if not parts or not parts[0]:
        return None, None
    service = parts[0]
    rest = "/" + "/".join(parts[1:]) if len(parts) > 1 else ""
    return service, rest


@app.api_route("/v1/{full_path:path}",
               methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def gateway(request: Request, full_path: str):

    service, subpath = parse_path(full_path)

    if service not in SERVICES:
        raise HTTPException(status_code=404, detail="Unknown service")

    backend = pick_backend(service)
    target_url = backend + f"/v1/{service}{subpath}"

    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    params = dict(request.query_params)
    body = await request.body()

    files = None
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        form = await request.form()
        files = {}
        for key, value in form.items():
            if isinstance(value, UploadFile):
                files[key] = (value.filename, value.file, value.content_type)
            else:
                files[key] = (None, value)

    resp = await proxy_request(
        method=request.method,
        url=target_url,
        headers=headers,
        params=params,
        body=body,
        files=files,
    )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={
            k: v for k, v in resp.headers.items()
            if k.lower() not in {"content-length", "transfer-encoding", "connection"}
        }
    )
