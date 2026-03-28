"""Estimator helpers for proximity and simple summary lookups."""

from .simple_estimator import summarize_property_cluster

__all__ = ["summarize_property_cluster"]

try:
    from .proximity import (
        get_nearest_parks,
        get_nearest_playgrounds,
        get_nearest_police_stations,
        get_nearest_schools,
        get_properties_on_same_street,
        get_top_closest_properties,
    )

    __all__.extend(
        [
            "get_top_closest_properties",
            "get_properties_on_same_street",
            "get_nearest_schools",
            "get_nearest_police_stations",
            "get_nearest_playgrounds",
            "get_nearest_parks",
        ]
    )
except ModuleNotFoundError:
    # Keep simple estimator imports working even when the proximity module's
    # environment-specific dependencies are not on the import path.
    pass
