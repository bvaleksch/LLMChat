from flask import Flask, request, Response
import requests
from services import SERVICES

app = Flask(__name__)


def get_target_service(path: str):
    """
    /v1/users/profile -> service 'users'
    /v1/media/upload  -> service 'media'
    /v1/chats/send    -> service 'chats'
    """
    parts = path.strip("/").split("/")

    if len(parts) < 2:
        return None, None

    version = parts[0]      # v1
    service = parts[1]      # users, media, chats
    rest = "/" + "/".join(parts[2:]) if len(parts) > 2 else ""

    return service, rest


@app.route("/v1/<path:path>", methods=[
    "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
])
def proxy(path):

    service_name, subpath = get_target_service(path)

    if service_name not in SERVICES:
        return {"detail": "Unknown service"}, 404

    target_url = SERVICES[service_name] + subpath

    # Prepare request data
    data = request.get_data()
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    params = request.args

    # Files
    files = None
    if request.files:
        files = {
            k: (f.filename, f.stream, f.mimetype)
            for k, f in request.files.items()
        }

    # Send request to target service
    resp = requests.request(
        method=request.method,
        url=target_url,
        headers=headers,
        params=params,
        data=None if files else data,
        files=files,
        timeout=30
    )

    # Return response back to the client
    excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]

    response_headers = [
        (name, value)
        for name, value in resp.headers.items()
        if name.lower() not in excluded_headers
    ]

    return Response(
        resp.content,
        status=resp.status_code,
        headers=response_headers
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
