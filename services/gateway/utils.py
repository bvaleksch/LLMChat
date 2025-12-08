import httpx
from fastapi import HTTPException


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
