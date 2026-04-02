import sqlite3

from backend.src.services import features
from backend.src.jobs import precompute_grid


def test_distance_factor_branches():
    assert features._distance_to_factor(100) == 5000
    assert features._distance_to_factor(700) == 2000
    assert features._distance_to_factor(1500) == 500
    assert features._distance_to_factor(5000) == 0.0
    assert features._distance_to_factor(100, positive=False) == -5000


def test_validate_location_payload_polygon():
    from backend.src.services.validation import validate_location_payload

    issues = validate_location_payload({"location": {"polygon": "bad"}})
    assert any(issue.field == "location.polygon" for issue in issues)


def test_health_degraded_without_version(client, test_db_path):
    conn = sqlite3.connect(test_db_path)
    conn.execute("DELETE FROM dataset_versions")
    conn.commit()
    conn.close()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"degraded", "unhealthy", "healthy"}


def test_precompute_grid_failure_branch(monkeypatch, client):
    monkeypatch.setattr(precompute_grid, "_compute_grid", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))
    resp = client.post("/api/v1/jobs/precompute-grid")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["warnings"]
