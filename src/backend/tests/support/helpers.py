from src.backend.src.services.validation import ValidationIssue


def assert_error_envelope(data):
    assert "request_id" in data
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]


def assert_validation_errors(data):
    assert_error_envelope(data)
    details = data["error"].get("details") or {}
    errors = details.get("errors")
    assert isinstance(errors, list)
    assert all("field" in err and "reason" in err for err in errors)
