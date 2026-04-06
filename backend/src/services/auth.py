from __future__ import annotations

from fastapi import HTTPException, Request


def require_estimate_access(request: Request) -> None:
    settings = request.app.state.settings
    if not settings.estimate_auth_required:
        return

    auth_header = request.headers.get("Authorization", "").strip()
    api_key_header = request.headers.get("X-API-Key", "").strip()
    expected_token = settings.estimate_api_token.strip()
    if not expected_token:
        raise HTTPException(status_code=503, detail="Estimate auth token is not configured.")

    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    else:
        token = api_key_header

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required for estimate endpoint.")
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid estimate API credentials.")
