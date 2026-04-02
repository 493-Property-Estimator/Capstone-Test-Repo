"""Model training and deterministic fallback imputation for bed/bath enrichment."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

try:
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover
    pd = None

try:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor  # type: ignore
except ImportError:  # pragma: no cover
    RandomForestClassifier = None
    RandomForestRegressor = None


FEATURE_COLUMNS = [
    "assessment_value",
    "suite",
    "house_number",
    "street_name",
    "legal_description",
    "zoning",
    "lot_size",
    "total_gross_area",
    "year_built",
    "neighbourhood_id",
    "neighbourhood",
    "ward",
    "tax_class",
    "garage",
    "assessment_class_1",
    "assessment_class_2",
    "assessment_class_3",
    "assessment_class_pct_1",
    "assessment_class_pct_2",
    "assessment_class_pct_3",
    "lat",
    "lon",
]


@dataclass
class ModelPrediction:
    canonical_location_id: str
    bedrooms_estimated: int | None
    bathrooms_estimated: float | None
    confidence: float
    feature_snapshot: dict[str, Any]


def _group_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("zoning"),
        row.get("tax_class"),
        row.get("garage"),
        row.get("neighbourhood"),
    )


class GroupedBedBathModel:
    """Deterministic fallback model when pandas/sklearn are unavailable."""

    def __init__(self, version: str = "grouped-v1") -> None:
        self.version = version
        self._bedroom_majority: dict[tuple[Any, ...], int] = {}
        self._bathroom_average: dict[tuple[Any, ...], float] = {}
        self._global_bedroom = 3
        self._global_bathroom = 2.0

    def fit(self, rows: list[dict[str, Any]]) -> None:
        bedroom_votes: dict[tuple[Any, ...], list[int]] = defaultdict(list)
        bathroom_votes: dict[tuple[Any, ...], list[float]] = defaultdict(list)
        global_bedrooms: list[int] = []
        global_bathrooms: list[float] = []

        for row in rows:
            key = _group_key(row)
            if row.get("bedrooms") is not None:
                bedroom_votes[key].append(int(row["bedrooms"]))
                global_bedrooms.append(int(row["bedrooms"]))
            if row.get("bathrooms") is not None:
                bathroom_votes[key].append(float(row["bathrooms"]))
                global_bathrooms.append(float(row["bathrooms"]))

        if global_bedrooms:
            self._global_bedroom = Counter(global_bedrooms).most_common(1)[0][0]
        if global_bathrooms:
            self._global_bathroom = sum(global_bathrooms) / len(global_bathrooms)

        self._bedroom_majority = {
            key: Counter(values).most_common(1)[0][0]
            for key, values in bedroom_votes.items()
            if values
        }
        self._bathroom_average = {
            key: sum(values) / len(values)
            for key, values in bathroom_votes.items()
            if values
        }

    def predict(self, row: dict[str, Any]) -> ModelPrediction:
        key = _group_key(row)
        bedrooms = self._bedroom_majority.get(key, self._global_bedroom)
        bathrooms = self._bathroom_average.get(key, self._global_bathroom)
        confidence = 0.78 if key in self._bedroom_majority or key in self._bathroom_average else 0.64
        return ModelPrediction(
            canonical_location_id=str(row["canonical_location_id"]),
            bedrooms_estimated=bedrooms,
            bathrooms_estimated=round(float(bathrooms) * 2) / 2,
            confidence=confidence,
            feature_snapshot=build_feature_snapshot(row),
        )


class SklearnBedBathModel(GroupedBedBathModel):
    """Uses scikit-learn when available, with grouped fallback confidence semantics."""

    def __init__(self, version: str = "sklearn-rf-v1") -> None:
        super().__init__(version=version)
        self._bedroom_model = None
        self._bathroom_model = None
        self._feature_frame_columns: list[str] = []

    def fit(self, rows: list[dict[str, Any]]) -> None:
        super().fit(rows)
        if pd is None or RandomForestClassifier is None or RandomForestRegressor is None:
            return
        frame = pd.DataFrame(rows)
        features = pd.get_dummies(frame[FEATURE_COLUMNS], dummy_na=True)
        self._feature_frame_columns = list(features.columns)

        bedroom_mask = frame["bedrooms"].notna()
        if bedroom_mask.any():
            self._bedroom_model = RandomForestClassifier(n_estimators=100, random_state=42)
            self._bedroom_model.fit(features.loc[bedroom_mask], frame.loc[bedroom_mask, "bedrooms"].astype(int))

        bathroom_mask = frame["bathrooms"].notna()
        if bathroom_mask.any():
            self._bathroom_model = RandomForestRegressor(n_estimators=100, random_state=42)
            self._bathroom_model.fit(features.loc[bathroom_mask], frame.loc[bathroom_mask, "bathrooms"].astype(float))

    def predict(self, row: dict[str, Any]) -> ModelPrediction:
        baseline = super().predict(row)
        if pd is None or not self._feature_frame_columns:
            return baseline
        features = pd.get_dummies(pd.DataFrame([row])[FEATURE_COLUMNS], dummy_na=True)
        features = features.reindex(columns=self._feature_frame_columns, fill_value=0)

        bedrooms = baseline.bedrooms_estimated
        bathrooms = baseline.bathrooms_estimated
        confidence = baseline.confidence

        if self._bedroom_model is not None:
            probabilities = self._bedroom_model.predict_proba(features)[0]
            bedrooms = int(self._bedroom_model.classes_[probabilities.argmax()])
            confidence = max(confidence, float(probabilities.max()))

        if self._bathroom_model is not None:
            predicted = float(self._bathroom_model.predict(features)[0])
            bathrooms = round(predicted * 2) / 2
            confidence = max(confidence, 0.70)

        return ModelPrediction(
            canonical_location_id=baseline.canonical_location_id,
            bedrooms_estimated=bedrooms,
            bathrooms_estimated=bathrooms,
            confidence=min(confidence, 0.95),
            feature_snapshot=baseline.feature_snapshot,
        )


def select_model(version_prefix: str = "bedbath") -> GroupedBedBathModel:
    if pd is not None and RandomForestClassifier is not None and RandomForestRegressor is not None:
        return SklearnBedBathModel(version=f"{version_prefix}-sklearn-rf-v1")
    return GroupedBedBathModel(version=f"{version_prefix}-grouped-v1")


def build_feature_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {column: row.get(column) for column in FEATURE_COLUMNS}


def training_rows_from_candidates(
    rows: list[dict[str, Any]],
    *,
    min_confidence: float,
    allowed_source_types: set[str] | None = None,
) -> list[dict[str, Any]]:
    allowed = allowed_source_types or {"observed", "inferred"}
    training_rows: list[dict[str, Any]] = []
    for row in rows:
        if row.get("source_type") not in allowed:
            continue
        if row.get("quarantined"):
            continue
        confidence = float(row.get("confidence") or 0.0)
        if confidence < min_confidence:
            continue
        if row.get("bedrooms") is None and row.get("bathrooms") is None:
            continue
        training_rows.append(dict(row))
    return training_rows


def training_rows_from_observed(rows: list[dict[str, Any]], *, min_confidence: float) -> list[dict[str, Any]]:
    return training_rows_from_candidates(
        rows,
        min_confidence=min_confidence,
        allowed_source_types={"observed"},
    )
