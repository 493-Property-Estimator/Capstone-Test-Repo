import pytest

from src.backend.src.services import validation


def test_validate_coordinates_branches():
    assert validation.validate_coordinates(None)
    assert validation.validate_coordinates("bad")
    assert validation.validate_coordinates({"lat": 1})

    issues = validation.validate_coordinates({"lat": "no", "lng": "no"})
    assert any(issue.reason == "not_numeric" for issue in issues)

    issues = validation.validate_coordinates({"lat": 100, "lng": 200})
    assert any(issue.reason == "out_of_range" for issue in issues)


def test_validate_address_branches():
    assert validation.validate_address("")
    assert validation.validate_address("Main")
    assert validation.validate_address("123 Main") == []


def test_validate_location_payload_variants():
    assert validation.validate_location_payload({})
    assert validation.validate_location_payload({"location": "bad"})

    issues = validation.validate_location_payload({"location": {"address": ""}})
    assert issues

    issues = validation.validate_location_payload({"location": {"coordinates": {"lat": "x", "lng": 1}}})
    assert issues

    issues = validation.validate_location_payload({"location": {"polygon": {"type": "Point"}}})
    assert issues

    issues = validation.validate_location_payload({"location": {}})
    assert issues


def test_validate_property_details_branches():
    assert validation.validate_property_details({"property_details": "bad"}) == []

    issues = validation.validate_property_details({"property_details": {"bedrooms": "x"}})
    assert any(issue.reason == "not_numeric" for issue in issues)

    issues = validation.validate_property_details({"property_details": {"total_gross_area": 0}})
    assert any(issue.reason == "out_of_range" for issue in issues)

    assert validation.validate_property_details({"property_details": {"total_gross_area": 100}}) == []
    assert validation.validate_property_details({"property_details": {"bedrooms": 1}}) == []


def test_validate_polygon_branches():
    assert validation.validate_polygon("bad")
    assert validation.validate_polygon({"type": "Point"})
    assert validation.validate_polygon({"type": "Polygon", "coordinates": []})
    assert validation.validate_polygon({"type": "Polygon", "coordinates": [[(0, 0), (1, 1), (2, 2)]]})

    issues = validation.validate_polygon(
        {"type": "Polygon", "coordinates": [[[0, 0], "bad", [1, 1], [0, 0]]]}
    )
    assert issues

    issues = validation.validate_polygon({"type": "Polygon", "coordinates": [["bad"]]})
    assert issues

    issues = validation.validate_polygon({"type": "Polygon", "coordinates": [[["a", "b"], [0, 0], [0, 0], [0, 0]]]} )
    assert issues

    issues = validation.validate_polygon({"type": "Polygon", "coordinates": [[[200, 0], [0, 0], [0, 0], [200, 0]]]} )
    assert issues

    issues = validation.validate_polygon({"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]})
    assert any(issue.reason == "invalid_format" for issue in issues)

    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]],
    }
    issues = validation.validate_polygon(bowtie)
    assert any(issue.reason == "self_intersection" for issue in issues)

    valid = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }
    assert validation.validate_polygon(valid) == []
