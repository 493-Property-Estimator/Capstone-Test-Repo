# System ER Diagram (Collapsed Collective Model)

```mermaid
erDiagram
    %% Each entity below intentionally aggregates related data-model.md files.

    LOCATION_INPUT_RESOLUTION {
        string resolution_id PK
        string input_mode "address|coords|map_click|search"
        string raw_input
        float latitude
        float longitude
        string geocode_status
        string boundary_status
        string parcel_status
        string canonical_location_id
        string normalization_status
    }

    PROPERTY_PROFILE_BASELINE {
        string profile_id PK
        string canonical_location_id
        json property_attributes
        json baseline_assessment_data
        json location_features
        json fallback_averages
        datetime computed_at
    }

    VALUE_ESTIMATION {
        string estimate_id PK
        string request_id
        string canonical_location_id
        float point_estimate
        float range_low
        float range_high
        float confidence_score
        string estimate_status
        string response_status
        json warnings
    }

    VALUE_EXPLANATION {
        string explanation_id PK
        string estimate_id
        json factor_contributions
        json factor_adjustments
        json warning_flags
        string explanation_status
    }

    ACCESSIBILITY_ENV_SIGNALS {
        string signal_set_id PK
        string canonical_location_id
        json amenity_proximity
        json travel_accessibility
        json green_space
        json school_distance
        json commute_accessibility
        json neighbourhood_indicators
        datetime refreshed_at
    }

    OPEN_DATA_WORKFLOW {
        string workflow_id PK
        string workflow_type "geospatial|census|assessment|poi_standardization|deduplication|refresh"
        string run_status
        json artifacts
        json validation_results
        json qa_results
        json promotion_publication_results
        json dataset_versions
        datetime started_at
        datetime completed_at
    }

    CACHE_PRECOMPUTE {
        string cache_compute_id PK
        string canonical_request_signature
        string cache_key
        json cached_estimate
        datetime ttl_expires_at
        json cache_telemetry
        json grid_features
        string precompute_job_status
    }

    MAP_SEARCH_OVERLAYS {
        string map_session_id PK
        string search_query
        json suggestions
        json map_state
        json map_bounds
        json layer_toggles
        json layer_data_responses
        json layer_warnings
        datetime updated_at
    }

    RELIABILITY_FALLBACKS {
        string reliability_id PK
        string request_id
        json dataset_availability
        bool strict_mode
        json strict_mode_failure
        string distance_mode
        bool fallback_used
        json fallback_logs
        json missing_data_warning_state
        json dismissal_state
    }

    API_ERROR_CONTRACT {
        string error_contract_id PK
        string request_id
        int status_code
        string error_code
        string message
        json validation_error_items
        string correlation_id
        datetime emitted_at
    }

    SERVICE_HEALTH_METRICS {
        string health_snapshot_id PK
        string health_status
        json dependency_statuses
        json metrics_output
        datetime observed_at
    }

    %% Core system flow
    LOCATION_INPUT_RESOLUTION ||--|| PROPERTY_PROFILE_BASELINE : resolves_to_profile
    PROPERTY_PROFILE_BASELINE ||--|| ACCESSIBILITY_ENV_SIGNALS : enriches_with_signals
    ACCESSIBILITY_ENV_SIGNALS ||--|| VALUE_ESTIMATION : contributes_features
    PROPERTY_PROFILE_BASELINE ||--|| VALUE_ESTIMATION : anchors_estimate
    VALUE_ESTIMATION ||--|| VALUE_EXPLANATION : explained_by

    %% Reliability, cache, and API behavior
    VALUE_ESTIMATION ||--o| RELIABILITY_FALLBACKS : may_use_partial_or_fallback
    VALUE_ESTIMATION ||--o| CACHE_PRECOMPUTE : may_be_cached
    VALUE_ESTIMATION ||--o| API_ERROR_CONTRACT : may_fail_with

    %% Platform data pipelines feeding valuation
    OPEN_DATA_WORKFLOW ||--|{ ACCESSIBILITY_ENV_SIGNALS : publishes_signal_data
    OPEN_DATA_WORKFLOW ||--|{ PROPERTY_PROFILE_BASELINE : publishes_baselines
    OPEN_DATA_WORKFLOW ||--|{ CACHE_PRECOMPUTE : triggers_precompute

    %% UI and service surface
    LOCATION_INPUT_RESOLUTION ||--o{ MAP_SEARCH_OVERLAYS : drives_map_search
    MAP_SEARCH_OVERLAYS ||--o{ VALUE_ESTIMATION : initiates_requests
    SERVICE_HEALTH_METRICS ||--o{ OPEN_DATA_WORKFLOW : monitors
    SERVICE_HEALTH_METRICS ||--o{ VALUE_ESTIMATION : monitors_runtime
```

## Coverage Mapping (spec folders -> collapsed entities)

- `001, 002, 003, 004, 024` -> `LOCATION_INPUT_RESOLUTION` and `MAP_SEARCH_OVERLAYS`
- `005, 006` -> `PROPERTY_PROFILE_BASELINE`
- `013, 014, 023` -> `VALUE_ESTIMATION`
- `015, 016` -> `VALUE_EXPLANATION` and `VALUE_ESTIMATION`
- `007, 008, 009, 010, 011, 012` -> `ACCESSIBILITY_ENV_SIGNALS`
- `017, 018, 019, 020, 021, 022` -> `OPEN_DATA_WORKFLOW`
- `029, 030` -> `CACHE_PRECOMPUTE`
- `026, 027, 028` -> `RELIABILITY_FALLBACKS`
- `031` -> `SERVICE_HEALTH_METRICS`
- `032` (+ error parts of `023`) -> `API_ERROR_CONTRACT`
