import sqlite3


def test_resolve_ambiguous(client, test_db_path):
    conn = sqlite3.connect(test_db_path)
    conn.execute(
        """
        INSERT INTO property_locations_prod (
            canonical_location_id, assessment_value, house_number, street_name,
            neighbourhood, ward, lat, lon
        ) VALUES ('loc_002', 420000, '123', 'Main St', 'Downtown', 'Ward 1', 53.5462, -113.4939)
        """
    )
    conn.commit()
    conn.close()

    resp = client.get("/api/v1/search/resolve", params={"q": "123 Main"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"ambiguous", "resolved"}


def test_resolve_unsupported_region(client, test_db_path):
    conn = sqlite3.connect(test_db_path)
    conn.execute(
        """
        INSERT INTO property_locations_prod (
            canonical_location_id, assessment_value, house_number, street_name,
            neighbourhood, ward, lat, lon
        ) VALUES ('loc_003', 430000, '999', 'Outside St', 'None', 'Ward 0', 0.0, 0.0)
        """
    )
    conn.commit()
    conn.close()
    resp = client.get("/api/v1/search/resolve", params={"q": "Outside St"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"unsupported_region", "resolved"}
