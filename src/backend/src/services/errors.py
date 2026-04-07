from __future__ import annotations

from typing import Any

from src.backend.src.services.validation import ValidationIssue


def error_response(request_id: str, code: str, message: str, details: dict[str, Any] | None = None, retryable: bool = False):
    return {
        "request_id": request_id,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "retryable": retryable,
        },
    }


def validation_error_response(request_id: str, issues: list[ValidationIssue], status: int):
    # Map to frontend standard error envelope but include issue details
    details = {
        "errors": [
            {
                "field": issue.field,
                "reason": issue.reason,
                "correction": issue.correction,
            }
            for issue in sorted(issues, key=lambda i: i.severity)
        ]
    }
    return error_response(
        request_id=request_id,
        code="INVALID_INPUT",
        message="Request validation failed.",
        details=details,
        retryable=False,
    ), status
