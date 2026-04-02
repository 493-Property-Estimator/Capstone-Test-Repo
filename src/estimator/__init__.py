"""Estimator helpers for proximity and simple summary lookups."""

from .property_estimator import PropertyEstimator, estimate_property_value
from .simple_estimator import summarize_property_cluster

__all__ = ["summarize_property_cluster", "PropertyEstimator", "estimate_property_value"]

try:
    from .proximity import (
        get_downtown_accessibility,
        get_nearest_libraries,
        get_nearest_parks,
        get_nearest_playgrounds,
        get_nearest_police_stations,
        get_nearest_schools,
        get_neighbourhood_context,
        get_properties_on_same_street,
        get_top_closest_properties,
        group_comparables_by_attributes,
    )

    __all__.extend(
        [
            "get_top_closest_properties",
            "get_properties_on_same_street",
            "get_nearest_schools",
            "get_nearest_police_stations",
            "get_nearest_playgrounds",
            "get_nearest_parks",
            "get_nearest_libraries",
            "get_neighbourhood_context",
            "get_downtown_accessibility",
            "group_comparables_by_attributes",
        ]
    )
except ModuleNotFoundError:
    # Keep simple estimator imports working even when the proximity module's
    # environment-specific dependencies are not on the import path.
    pass
