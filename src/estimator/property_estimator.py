"""Baseline-anchored property estimator built on repository SQLite datasets."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path
from statistics import median
from typing import Any

from src.data_sourcing.database import connect
from src.estimator.proximity import (
    get_downtown_accessibility,
    get_nearest_libraries,
    get_nearest_parks,
    get_nearest_playgrounds,
    get_nearest_schools,
    get_neighbourhood_context,
    group_comparables_by_attributes,
)

DOWNTOWN_EDMONTON = {"name": "Downtown Edmonton", "lat": 53.5461, "lon": -113.4938}
MATCH_DISTANCE_THRESHOLD_M = 35.0
MAX_ROUTE_FALLBACK_DISTANCE_M = 30_000.0


class PropertyEstimator:
    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._services_module = self._load_testingstage_services()
        self._road_graph = self._services_module.RoadGraph(self._db_path)
        self._transit = self._services_module.TransitNetwork(self._db_path)
        self._osrm = self._services_module.OsrmService()
        provider = self._services_module.SQLiteCrimeProvider(self._db_path)
        self._crime_provider = (
            provider
            if provider.is_available()
            else self._services_module.UnavailableCrimeProvider()
        )

    @staticmethod
    def _load_testingstage_services():
        from TestingStage.backend import services as testingstage_services

        return testingstage_services

    def _connect(self) -> sqlite3.Connection:
        return connect(self._db_path)

    def estimate(
        self,
        *,
        lat: float,
        lon: float,
        property_attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        point = self._normalize_point(lat, lon)
        normalized_attributes = self._normalize_attributes(property_attributes or {})
        request_id = self._build_request_id(point, normalized_attributes)
        warnings: list[dict[str, Any]] = []
        missing_factors: list[str] = []
        fallback_flags: list[str] = []

        nearest_property = self._find_nearest_property(point["lat"], point["lon"])
        if nearest_property is None:
            raise ValueError("No properties with coordinates were found in the database.")

        matched_property = (
            nearest_property
            if float(nearest_property["distance_m"]) <= MATCH_DISTANCE_THRESHOLD_M
            else None
        )
        baseline = self._resolve_baseline(nearest_property, matched_property, warnings, fallback_flags)
        amenities = self._collect_amenities(point, warnings, fallback_flags, missing_factors)
        downtown = self._collect_downtown_access(point, warnings, fallback_flags, missing_factors)
        neighbourhood_context = self._collect_neighbourhood_context(
            point,
            matched_property,
            warnings,
            missing_factors,
        )
        comparables = self._collect_comparables(point, normalized_attributes, warnings, missing_factors)

        valuation = self._calculate_value(
            baseline=baseline,
            amenities=amenities,
            downtown=downtown,
            neighbourhood_context=neighbourhood_context,
            comparables=comparables,
            warnings=warnings,
            fallback_flags=fallback_flags,
        )
        range_result = self._calculate_range(
            final_estimate=valuation["final_estimate"],
            baseline_value=baseline["assessment_value"],
            comparables=comparables,
            completeness_score=valuation["completeness_score"],
            warnings=warnings,
        )
        confidence = self._calculate_confidence(
            matched_property=matched_property,
            baseline=baseline,
            comparables=comparables,
            missing_factors=missing_factors,
            fallback_flags=fallback_flags,
            amenities=amenities,
            downtown=downtown,
            neighbourhood_context=neighbourhood_context,
        )
        warnings = self._dedupe_warnings(warnings)

        matched_payload = None
        if matched_property is not None:
            matched_payload = {
                **self._property_payload(matched_property),
                "assessed_value": self._round_money(matched_property.get("assessment_value")),
                "estimated_value": valuation["final_estimate"],
                "estimate_minus_assessed_delta": self._round_money(
                    valuation["final_estimate"] - float(matched_property.get("assessment_value") or 0.0)
                ),
            }

        return {
            "request_id": request_id,
            "correlation_id": request_id,
            "query_point": point,
            "matched_property": matched_payload,
            "baseline": baseline,
            "final_estimate": valuation["final_estimate"],
            "low_estimate": range_result["low_estimate"],
            "high_estimate": range_result["high_estimate"],
            "confidence_score": confidence["confidence_score"],
            "confidence_label": confidence["confidence_label"],
            "completeness_score": valuation["completeness_score"],
            "warnings": warnings,
            "missing_factors": sorted(set(missing_factors)),
            "fallback_flags": sorted(set(fallback_flags)),
            "feature_breakdown": {
                "amenities": amenities,
                "downtown_accessibility": downtown,
                "valuation_adjustments": valuation["adjustments"],
            },
            "top_positive_factors": valuation["top_positive_factors"],
            "top_negative_factors": valuation["top_negative_factors"],
            "comparables_matching": comparables["matching"],
            "comparables_non_matching": comparables["non_matching"],
            "neighbourhood_context": neighbourhood_context,
        }

    def _normalize_point(self, lat: float, lon: float) -> dict[str, float]:
        lat_value = float(lat)
        lon_value = float(lon)
        if not -90.0 <= lat_value <= 90.0:
            raise ValueError("Latitude must be between -90 and 90.")
        if not -180.0 <= lon_value <= 180.0:
            raise ValueError("Longitude must be between -180 and 180.")
        return {
            "lat": round(lat_value, 6),
            "lon": round(lon_value, 6),
        }

    def _normalize_attributes(self, attributes: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in sorted(attributes.items()):
            if value in (None, ""):
                continue
            if key in {"year_built", "lot_size", "total_gross_area", "bedrooms", "bathrooms"}:
                normalized[key] = float(value)
            else:
                normalized[key] = str(value).strip()
        return normalized

    def _build_request_id(self, point: dict[str, float], attributes: dict[str, Any]) -> str:
        with self._connect() as connection:
            dataset_rows = connection.execute(
                """
                SELECT dataset_type, version_id
                FROM dataset_versions
                ORDER BY dataset_type, promoted_at DESC, id DESC
                """
            ).fetchall()
        payload = {
            "point": point,
            "attributes": attributes,
            "dataset_versions": [(row["dataset_type"], row["version_id"]) for row in dataset_rows],
            "model_version": "baseline-anchor-v1",
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return f"est-{digest[:16]}"

    def _find_nearest_property(self, lat: float, lon: float) -> dict[str, Any] | None:
        lon_scale = math.cos(math.radians(lat))
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    pl.canonical_location_id,
                    pl.assessment_year,
                    COALESCE(ap.assessment_value, pl.assessment_value) AS assessment_value,
                    pl.house_number,
                    pl.street_name,
                    pl.neighbourhood_id,
                    pl.neighbourhood,
                    pl.ward,
                    pl.zoning,
                    pl.lot_size,
                    pl.total_gross_area,
                    pl.year_built,
                    pl.tax_class,
                    pl.garage,
                    pl.assessment_class_1,
                    pl.assessment_class_2,
                    pl.assessment_class_3,
                    pl.lat,
                    pl.lon,
                    ap.chosen_record_id
                FROM property_locations_prod pl
                LEFT JOIN assessments_prod ap
                  ON ap.canonical_location_id = pl.canonical_location_id
                WHERE pl.lat IS NOT NULL
                  AND pl.lon IS NOT NULL
                ORDER BY
                  ((pl.lat - ?) * (pl.lat - ?))
                  + (((pl.lon - ?) * ?) * ((pl.lon - ?) * ?)),
                  pl.canonical_location_id
                LIMIT 1
                """,
                (lat, lat, lon, lon_scale, lon, lon_scale),
            ).fetchone()
        if row is None:
            return None

        item_lat = float(row["lat"])
        item_lon = float(row["lon"])
        return {
            **dict(row),
            "distance_m": round(
                self._services_module.haversine_meters(lat, lon, item_lat, item_lon),
                2,
            ),
        }

    def _resolve_baseline(
        self,
        nearest_property: dict[str, Any],
        matched_property: dict[str, Any] | None,
        warnings: list[dict[str, Any]],
        fallback_flags: list[str],
    ) -> dict[str, Any]:
        value = nearest_property.get("assessment_value")
        if value is None:
            raise ValueError("Baseline assessment data is required but unavailable for the query point.")

        exact_match = matched_property is not None
        baseline_source = "assessments_prod" if nearest_property.get("chosen_record_id") else "property_locations_prod"
        baseline_type = "matched_property_assessment" if exact_match else "nearest_neighbour_assessment"
        if not exact_match:
            fallback_flags.append("baseline_nearest_neighbour")
            warnings.append(
                self._warning(
                    "baseline_nearest_neighbour",
                    "medium",
                    "No property was matched at the query point. The estimate is anchored to the nearest assessed property instead.",
                )
            )

        return {
            "canonical_location_id": nearest_property["canonical_location_id"],
            "assessment_year": nearest_property.get("assessment_year"),
            "assessment_value": self._round_money(value),
            "baseline_type": baseline_type,
            "source_table": baseline_source,
            "distance_to_query_m": round(float(nearest_property["distance_m"]), 2),
            "address": self._property_address(nearest_property),
            "neighbourhood": nearest_property.get("neighbourhood"),
            "matched_property": exact_match,
        }

    def _collect_amenities(
        self,
        point: dict[str, float],
        warnings: list[dict[str, Any]],
        fallback_flags: list[str],
        missing_factors: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        amenity_specs = [
            ("parks", get_nearest_parks, 3, "park_access"),
            ("playgrounds", get_nearest_playgrounds, 3, "playground_access"),
            ("schools", get_nearest_schools, 3, "school_access"),
            ("libraries", get_nearest_libraries, 1, "library_access"),
        ]
        output: dict[str, list[dict[str, Any]]] = {}
        for amenity_name, query_fn, limit, missing_code in amenity_specs:
            rows = query_fn(
                (point["lon"], point["lat"]),
                limit=limit,
                distance_mode="manhattan",
                db_path=self._db_path,
            )
            if not rows:
                missing_factors.append(missing_code)
                warnings.append(
                    self._warning(
                        f"{amenity_name}_unavailable",
                        "medium",
                        f"No {amenity_name} were found in the current repository database for this query.",
                    )
                )
                output[amenity_name] = []
                continue
            output[amenity_name] = [
                self._distance_bundle(
                    point=point,
                    target=row,
                    label=row.get("name") or amenity_name.title(),
                    fallback_flags=fallback_flags,
                    warnings=warnings,
                )
                for row in rows
            ]
        return output

    def _collect_downtown_access(
        self,
        point: dict[str, float],
        warnings: list[dict[str, Any]],
        fallback_flags: list[str],
        missing_factors: list[str],
    ) -> dict[str, Any]:
        downtown = get_downtown_accessibility(
            (point["lon"], point["lat"]),
            downtown_point=(DOWNTOWN_EDMONTON["lon"], DOWNTOWN_EDMONTON["lat"]),
        )
        target = {
            "name": DOWNTOWN_EDMONTON["name"],
            "lat": DOWNTOWN_EDMONTON["lat"],
            "lon": DOWNTOWN_EDMONTON["lon"],
            "entity_id": "downtown-edmonton",
        }
        bundle = self._distance_bundle(
            point=point,
            target=target,
            label=DOWNTOWN_EDMONTON["name"],
            fallback_flags=fallback_flags,
            warnings=warnings,
        )
        if bundle["transit_distance_m"] is None:
            missing_factors.append("downtown_transit_time")
        bundle["straight_line_m"] = downtown["straight_line_m"]
        return bundle

    def _collect_neighbourhood_context(
        self,
        point: dict[str, float],
        matched_property: dict[str, Any] | None,
        warnings: list[dict[str, Any]],
        missing_factors: list[str],
    ) -> dict[str, Any]:
        neighbourhood_context = get_neighbourhood_context(
            (point["lon"], point["lat"]),
            other_limit=4,
            db_path=self._db_path,
        )
        primary_name = neighbourhood_context.get("primary_neighbourhood")
        if matched_property and matched_property.get("neighbourhood"):
            primary_name = matched_property["neighbourhood"]

        if primary_name is None:
            missing_factors.append("neighbourhood_context")
            warnings.append(
                self._warning(
                    "neighbourhood_unavailable",
                    "medium",
                    "Neighbourhood context could not be resolved from the property table.",
                )
            )
            return {
                **neighbourhood_context,
                "crime_available": False,
                "census_available": False,
                "primary_crime": None,
            }

        aggregates = self._neighbourhood_aggregates_by_name(primary_name)
        others = self._closest_other_neighbourhoods(primary_name, limit=4)

        crime_available = hasattr(self._crime_provider, "is_available") and self._crime_provider.is_available()
        primary_crime = self._crime_provider.summary_by_neighbourhood(primary_name)
        other_crime = [
            {
                **item,
                "crime": self._crime_provider.summary_by_neighbourhood(item["neighbourhood"]),
            }
            for item in others
        ]
        if not crime_available:
            missing_factors.append("crime_statistics")
            warnings.append(
                self._warning(
                    "crime_unavailable",
                    "medium",
                    "Crime data is not available in the current repository database. Crime factors were omitted.",
                )
            )

        census_available = self._table_row_count("census_prod") > 0
        if not census_available:
            missing_factors.append("census_indicators")
            warnings.append(
                self._warning(
                    "census_unavailable",
                    "medium",
                    "census_prod is empty, so census-based neighbourhood indicators were omitted.",
                )
            )

        return {
            "primary_neighbourhood": primary_name,
            "primary_average_assessment": self._round_money(aggregates["average_assessment"]),
            "primary_property_count": int(aggregates["property_count"]),
            "primary_crime": primary_crime,
            "other_neighbourhoods": other_crime,
            "crime_available": bool(crime_available),
            "census_available": census_available,
            "resolution_method": "matched_property_neighbourhood"
            if matched_property and matched_property.get("neighbourhood")
            else neighbourhood_context.get("resolution_method"),
        }

    def _collect_comparables(
        self,
        point: dict[str, float],
        normalized_attributes: dict[str, Any],
        warnings: list[dict[str, Any]],
        missing_factors: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        grouped = group_comparables_by_attributes(
            (point["lon"], point["lat"]),
            normalized_attributes,
            limit=8,
            db_path=self._db_path,
        )
        matching = [self._comparable_payload(item) for item in grouped["matching"]]
        non_matching = [self._comparable_payload(item) for item in grouped["non_matching"]]

        if normalized_attributes and not matching:
            missing_factors.append("matching_comparables")
            warnings.append(
                self._warning(
                    "matching_comparables_unavailable",
                    "medium",
                    "No nearby properties matched the supplied property attributes. The estimate used non-matching comparables instead.",
                )
            )

        if not non_matching and not matching:
            missing_factors.append("comparables")
            warnings.append(
                self._warning(
                    "comparables_unavailable",
                    "high",
                    "No nearby assessed comparables were available. The estimate relies heavily on the baseline anchor.",
                )
            )

        return {
            "matching": matching,
            "non_matching": non_matching,
        }

    def _distance_bundle(
        self,
        *,
        point: dict[str, float],
        target: dict[str, Any],
        label: str,
        fallback_flags: list[str],
        warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        route = self._road_graph.route_distance(
            point["lat"],
            point["lon"],
            float(target["lat"]),
            float(target["lon"]),
        )
        road_distance_m = min(float(route["road_distance_m"]), MAX_ROUTE_FALLBACK_DISTANCE_M)
        route_mode = route["routing_mode"]
        fallback_used = route_mode == "straight_line_fallback"
        if fallback_used:
            fallback_flags.append("straight_line_distance")
            warnings.append(
                self._warning(
                    "straight_line_fallback",
                    "medium",
                    f"Road routing was unavailable for {label}, so straight-line distance was used as a fallback.",
                )
            )

        car_time_s = None
        car_time_source = None
        if self._osrm.is_configured():
            try:
                osrm_route = self._osrm.route(
                    point["lat"],
                    point["lon"],
                    float(target["lat"]),
                    float(target["lon"]),
                    "driving",
                )
                car_time_s = round(float(osrm_route["duration_s"]), 2)
                road_distance_m = round(float(osrm_route["distance_m"]), 2)
                car_time_source = "osrm"
                route_mode = "osrm"
            except Exception:
                warnings.append(
                    self._warning(
                        "osrm_duration_unavailable",
                        "low",
                        f"Car travel time for {label} is unavailable because OSRM is not configured or did not return a route.",
                    )
                )

        transit_distance_m = None
        transit_time_s = None
        transit_mode = "unavailable"
        if self._transit.has_data():
            try:
                journey = self._transit.plan_journey(
                    {
                        "label": "Query point",
                        "lat": point["lat"],
                        "lon": point["lon"],
                    },
                    {
                        "label": label,
                        "lat": float(target["lat"]),
                        "lon": float(target["lon"]),
                    },
                )
                transit_distance_m = round(float(journey["summary"]["total_distance_m"]), 2)
                transit_mode = "distance_only"
            except Exception:
                transit_distance_m = None

        return {
            "id": target.get("entity_id") or target.get("canonical_location_id"),
            "name": label,
            "lat": round(float(target["lat"]), 6),
            "lon": round(float(target["lon"]), 6),
            "raw_category": target.get("raw_category"),
            "straight_line_m": round(float(route["straight_line_m"]), 2),
            "road_distance_m": round(max(0.0, road_distance_m), 2),
            "car_travel_time_s": car_time_s,
            "car_travel_time_min": round(car_time_s / 60.0, 2) if car_time_s is not None else None,
            "car_time_source": car_time_source,
            "transit_distance_m": transit_distance_m,
            "transit_travel_time_s": transit_time_s,
            "transit_travel_time_min": None,
            "transit_mode": transit_mode,
            "distance_method": route_mode,
            "fallback_metadata": {
                "used": fallback_used,
                "reason": "routing_unavailable" if fallback_used else None,
                "straight_line_fallback": fallback_used,
            },
        }

    def _calculate_value(
        self,
        *,
        baseline: dict[str, Any],
        amenities: dict[str, list[dict[str, Any]]],
        downtown: dict[str, Any],
        neighbourhood_context: dict[str, Any],
        comparables: dict[str, list[dict[str, Any]]],
        warnings: list[dict[str, Any]],
        fallback_flags: list[str],
    ) -> dict[str, Any]:
        baseline_value = float(baseline["assessment_value"])
        adjustments: list[dict[str, Any]] = []

        matching_values = [item["assessment_value"] for item in comparables["matching"] if item["assessment_value"] is not None]
        non_matching_values = [
            item["assessment_value"] for item in comparables["non_matching"] if item["assessment_value"] is not None
        ]
        neighbourhood_average = neighbourhood_context.get("primary_average_assessment")

        if matching_values:
            median_value = float(median(matching_values))
            adjustments.append(
                self._adjustment(
                    "matching_comparables",
                    "Matching nearby assessments",
                    max(-0.12 * baseline_value, min(0.12 * baseline_value, (median_value - baseline_value) * 0.55)),
                    {"median_assessment": self._round_money(median_value), "sample_size": len(matching_values)},
                )
            )
        if non_matching_values:
            median_value = float(median(non_matching_values))
            adjustments.append(
                self._adjustment(
                    "nearby_comparables",
                    "Nearby assessments",
                    max(-0.08 * baseline_value, min(0.08 * baseline_value, (median_value - baseline_value) * 0.25)),
                    {"median_assessment": self._round_money(median_value), "sample_size": len(non_matching_values)},
                )
            )
        if neighbourhood_average is not None:
            neighbourhood_average_value = float(neighbourhood_average)
            adjustments.append(
                self._adjustment(
                    "neighbourhood_context",
                    "Neighbourhood average assessment",
                    max(
                        -0.06 * baseline_value,
                        min(0.06 * baseline_value, (neighbourhood_average_value - baseline_value) * 0.18),
                    ),
                    {"neighbourhood_average_assessment": self._round_money(neighbourhood_average_value)},
                )
            )

        for amenity_group, baseline_distance in (
            ("parks", 1_400.0),
            ("playgrounds", 1_200.0),
            ("schools", 2_000.0),
            ("libraries", 3_500.0),
        ):
            nearest = amenities.get(amenity_group, [])
            if not nearest:
                continue
            best = nearest[0]
            effective_distance = float(best["road_distance_m"] or best["straight_line_m"] or 0.0)
            distance_ratio = max(0.0, min(1.0, 1.0 - (effective_distance / baseline_distance)))
            max_impact = {
                "parks": 0.018,
                "playgrounds": 0.012,
                "schools": 0.02,
                "libraries": 0.01,
            }[amenity_group]
            adjustments.append(
                self._adjustment(
                    f"{amenity_group}_access",
                    f"{amenity_group[:-1].title() if amenity_group.endswith('s') else amenity_group.title()} accessibility",
                    baseline_value * max_impact * (distance_ratio - 0.35),
                    {"nearest_distance_m": round(effective_distance, 2)},
                )
            )

        downtown_distance = float(downtown["road_distance_m"] or downtown["straight_line_m"] or 0.0)
        downtown_ratio = max(0.0, min(1.0, 1.0 - (downtown_distance / 14_000.0)))
        adjustments.append(
            self._adjustment(
                "downtown_accessibility",
                "Downtown accessibility",
                baseline_value * 0.03 * (downtown_ratio - 0.25),
                {"distance_m": round(downtown_distance, 2)},
            )
        )

        raw_estimate = baseline_value + sum(item["value"] for item in adjustments)
        lower_guardrail = baseline_value * 0.65
        upper_guardrail = baseline_value * 1.35
        final_estimate = raw_estimate
        if raw_estimate < lower_guardrail or raw_estimate > upper_guardrail:
            final_estimate = min(max(raw_estimate, lower_guardrail), upper_guardrail)
            fallback_flags.append("valuation_guardrail")
            warnings.append(
                self._warning(
                    "valuation_guardrail",
                    "medium",
                    "An estimate guardrail was applied to keep the final result within a stable range around the assessment baseline.",
                )
            )

        rounded_estimate = self._round_money(max(0.0, final_estimate))
        rounded_adjustments = [
            {**item, "value": self._round_money(item["value"])}
            for item in sorted(adjustments, key=lambda row: (abs(row["value"]), row["code"]), reverse=True)
        ]
        completeness_score = self._calculate_completeness(
            amenities=amenities,
            downtown=downtown,
            neighbourhood_context=neighbourhood_context,
            comparables=comparables,
        )
        return {
            "final_estimate": rounded_estimate,
            "adjustments": rounded_adjustments,
            "completeness_score": completeness_score,
            "top_positive_factors": [item for item in rounded_adjustments if item["value"] > 0][:3],
            "top_negative_factors": [item for item in rounded_adjustments if item["value"] < 0][:3],
        }

    def _calculate_range(
        self,
        *,
        final_estimate: float,
        baseline_value: float,
        comparables: dict[str, list[dict[str, Any]]],
        completeness_score: float,
        warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        comparable_values = [
            item["assessment_value"]
            for group in ("matching", "non_matching")
            for item in comparables[group]
            if item["assessment_value"] is not None
        ]
        spread_ratio = 0.12
        if comparable_values:
            median_value = float(median(comparable_values))
            mean_abs_delta = sum(abs(float(value) - median_value) for value in comparable_values) / len(comparable_values)
            spread_ratio += min(0.12, mean_abs_delta / max(baseline_value, 1.0))
        else:
            spread_ratio += 0.08
        spread_ratio += max(0.0, (100.0 - completeness_score) / 250.0)
        spread_ratio = min(max(spread_ratio, 0.08), 0.38)

        low_estimate = max(0.0, final_estimate * (1.0 - spread_ratio))
        high_estimate = max(final_estimate, final_estimate * (1.0 + spread_ratio))
        if low_estimate > high_estimate:
            low_estimate, high_estimate = high_estimate, low_estimate

        if not comparable_values:
            warnings.append(
                self._warning(
                    "range_low_reliability",
                    "low",
                    "The estimate range is wider because no comparable sample was available for calibration.",
                )
            )

        return {
            "low_estimate": self._round_money(low_estimate),
            "high_estimate": self._round_money(high_estimate),
        }

    def _calculate_completeness(
        self,
        *,
        amenities: dict[str, list[dict[str, Any]]],
        downtown: dict[str, Any],
        neighbourhood_context: dict[str, Any],
        comparables: dict[str, list[dict[str, Any]]],
    ) -> float:
        weighted_checks = [
            (bool(amenities.get("parks")), 12.0),
            (bool(amenities.get("playgrounds")), 10.0),
            (bool(amenities.get("schools")), 12.0),
            (bool(amenities.get("libraries")), 8.0),
            (downtown.get("road_distance_m") is not None, 10.0),
            (neighbourhood_context.get("primary_average_assessment") is not None, 14.0),
            (neighbourhood_context.get("crime_available"), 8.0),
            (neighbourhood_context.get("census_available"), 8.0),
            (bool(comparables.get("matching")) or bool(comparables.get("non_matching")), 18.0),
        ]
        score = sum(weight for condition, weight in weighted_checks if condition)
        return round(min(score, 100.0), 2)

    def _calculate_confidence(
        self,
        *,
        matched_property: dict[str, Any] | None,
        baseline: dict[str, Any],
        comparables: dict[str, list[dict[str, Any]]],
        missing_factors: list[str],
        fallback_flags: list[str],
        amenities: dict[str, list[dict[str, Any]]],
        downtown: dict[str, Any],
        neighbourhood_context: dict[str, Any],
    ) -> dict[str, Any]:
        score = self._calculate_completeness(
            amenities=amenities,
            downtown=downtown,
            neighbourhood_context=neighbourhood_context,
            comparables=comparables,
        )
        if matched_property is not None:
            score += 8.0
        if baseline.get("matched_property"):
            score += 6.0
        score -= len(set(missing_factors)) * 4.0
        score -= len(set(fallback_flags)) * 3.5
        if comparables["matching"]:
            score += 6.0
        elif comparables["non_matching"]:
            score += 2.0
        score = max(5.0, min(score, 99.0))
        if score >= 80:
            label = "high"
        elif score >= 60:
            label = "medium"
        elif score >= 40:
            label = "low"
        else:
            label = "very_low"
        return {
            "confidence_score": round(score, 2),
            "confidence_label": label,
        }

    def _neighbourhood_aggregates_by_name(self, neighbourhood: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    neighbourhood,
                    AVG(assessment_value) AS average_assessment,
                    COUNT(*) AS property_count
                FROM property_locations_prod
                WHERE UPPER(COALESCE(neighbourhood, '')) = UPPER(?)
                  AND assessment_value IS NOT NULL
                GROUP BY neighbourhood
                """,
                (neighbourhood,),
            ).fetchone()
        if row is None:
            return {
                "neighbourhood": neighbourhood,
                "average_assessment": None,
                "property_count": 0,
            }
        return dict(row)

    def _closest_other_neighbourhoods(self, neighbourhood: str, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            anchor = connection.execute(
                """
                SELECT AVG(lat) AS centroid_lat, AVG(lon) AS centroid_lon
                FROM property_locations_prod
                WHERE UPPER(COALESCE(neighbourhood, '')) = UPPER(?)
                  AND lat IS NOT NULL
                  AND lon IS NOT NULL
                """,
                (neighbourhood,),
            ).fetchone()
            rows = connection.execute(
                """
                SELECT
                    neighbourhood,
                    AVG(assessment_value) AS average_assessment,
                    COUNT(*) AS property_count,
                    AVG(lat) AS centroid_lat,
                    AVG(lon) AS centroid_lon
                FROM property_locations_prod
                WHERE neighbourhood IS NOT NULL
                  AND TRIM(neighbourhood) <> ''
                  AND UPPER(neighbourhood) <> UPPER(?)
                  AND assessment_value IS NOT NULL
                  AND lat IS NOT NULL
                  AND lon IS NOT NULL
                GROUP BY neighbourhood
                """
                ,
                (neighbourhood,),
            ).fetchall()

        if anchor is None or anchor["centroid_lat"] is None or anchor["centroid_lon"] is None:
            return []

        ranked = []
        anchor_lat = float(anchor["centroid_lat"])
        anchor_lon = float(anchor["centroid_lon"])
        for row in rows:
            distance_m = self._services_module.haversine_meters(
                anchor_lat,
                anchor_lon,
                float(row["centroid_lat"]),
                float(row["centroid_lon"]),
            )
            ranked.append(
                {
                    "neighbourhood": row["neighbourhood"],
                    "average_assessment": self._round_money(row["average_assessment"]),
                    "property_count": int(row["property_count"] or 0),
                    "distance_from_primary_m": round(distance_m, 2),
                }
            )
        ranked.sort(key=lambda item: (item["distance_from_primary_m"], item["neighbourhood"]))
        return ranked[:limit]

    def _table_row_count(self, table_name: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS row_count FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()
            if row is None or int(row["row_count"] or 0) == 0:
                return 0
            result = connection.execute(f"SELECT COUNT(*) AS row_count FROM {table_name}").fetchone()
        return int(result["row_count"] or 0)

    def _comparable_payload(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "canonical_location_id": item.get("canonical_location_id"),
            "address": self._property_address(item),
            "assessment_value": self._round_money(item.get("assessment_value")),
            "distance_m": round(float(item.get("distance_m") or 0.0), 2),
            "neighbourhood": item.get("neighbourhood"),
            "year_built": item.get("year_built"),
            "lot_size": item.get("lot_size"),
            "total_gross_area": item.get("total_gross_area"),
            "garage": item.get("garage"),
            "tax_class": item.get("tax_class"),
            "attribute_match": bool(item.get("attribute_match")),
        }

    def _property_payload(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "canonical_location_id": item.get("canonical_location_id"),
            "address": self._property_address(item),
            "assessment_year": item.get("assessment_year"),
            "neighbourhood": item.get("neighbourhood"),
            "ward": item.get("ward"),
            "zoning": item.get("zoning"),
            "year_built": item.get("year_built"),
            "lot_size": item.get("lot_size"),
            "total_gross_area": item.get("total_gross_area"),
            "lat": round(float(item.get("lat") or 0.0), 6) if item.get("lat") is not None else None,
            "lon": round(float(item.get("lon") or 0.0), 6) if item.get("lon") is not None else None,
        }

    def _property_address(self, item: dict[str, Any]) -> str:
        parts = [str(item.get("house_number") or "").strip(), str(item.get("street_name") or "").strip()]
        address = " ".join(part for part in parts if part)
        return address or "Address unavailable"

    @staticmethod
    def _adjustment(code: str, label: str, value: float, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "code": code,
            "label": label,
            "value": value,
            "metadata": metadata,
        }

    @staticmethod
    def _warning(code: str, severity: str, message: str) -> dict[str, Any]:
        return {
            "code": code,
            "severity": severity,
            "message": message,
        }

    @staticmethod
    def _dedupe_warnings(warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str | None, str | None, str | None]] = set()
        for warning in warnings:
            key = (warning.get("code"), warning.get("severity"), warning.get("message"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(warning)
        return deduped

    @staticmethod
    def _round_money(value: Any) -> float | None:
        if value is None:
            return None
        return round(max(0.0, float(value)), 2)


def estimate_property_value(
    db_path: Path,
    *,
    lat: float,
    lon: float,
    property_attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    estimator = PropertyEstimator(db_path)
    return estimator.estimate(lat=lat, lon=lon, property_attributes=property_attributes)
