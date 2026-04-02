from starlette.requests import Request
from starlette.datastructures import Headers

import asyncio

from backend.src.app import value_error_handler


def test_value_error_handler():
    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    request = Request(scope, receive=lambda: None)
    response = asyncio.run(value_error_handler(request, ValueError("bad")))
    assert response.status_code == 400
