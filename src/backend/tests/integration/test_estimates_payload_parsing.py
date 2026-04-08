import asyncio
from starlette.requests import Request
from src.backend.src.api import estimates as estimates_api


async def _make_request(app, body: bytes):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {"type": "http", "headers": [], "app": app}
    request = Request(scope, receive)
    request.state.request_id = "req-1"
    return request


def test_estimates_payload_raw_body_parsing(client):
    async def _run():
        request = await _make_request(client.app, b"not-json")
        response = await estimates_api.create_estimate(request, payload=None)
        assert response.status_code == 400

    asyncio.run(_run())


def test_estimates_payload_string_parsing(client):
    async def _run():
        request = await _make_request(client.app, b"")
        response = await estimates_api.create_estimate(request, payload="bad-json")
        assert response.status_code == 400

    asyncio.run(_run())
