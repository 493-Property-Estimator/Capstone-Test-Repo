"""Per-neighbourhood valuation models (regression + RF) with optional sklearn support.

These models are trained on assessed values as a proxy target, and are intended to provide a
small, bounded adjustment relative to the baseline assessment anchor.
"""

from __future__ import annotations

import base64
import json
import pickle
from dataclasses import dataclass
from typing import Any

try:
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover
    pd = None

try:
    from sklearn.ensemble import RandomForestRegressor  # type: ignore
    from sklearn.linear_model import Ridge  # type: ignore
    from sklearn.model_selection import train_test_split  # type: ignore
except ImportError:  # pragma: no cover
    RandomForestRegressor = None
    Ridge = None
    train_test_split = None


NUMERIC_FEATURES = [
    "lot_size",
    "total_gross_area",
    "year_built",
    "bedrooms_estimated",
    "bathrooms_estimated",
]

CategoricalFeature = str
CATEGORICAL_FEATURES: list[CategoricalFeature] = [
    "zoning",
    "tax_class",
    "garage",
    "assessment_class_1",
]

TARGET_COLUMN = "assessment_value"


@dataclass(frozen=True)
class TrainedModel:
    neighbourhood: str
    model_type: str  # "ridge" | "rf"
    version: str
    feature_schema: dict[str, Any]
    payload: dict[str, Any]
    metrics: dict[str, Any]


def _safe_neighbourhood(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_feature_schema(dummy_columns: list[str]) -> dict[str, Any]:
    return {
        "numeric": list(NUMERIC_FEATURES),
        "categorical": list(CATEGORICAL_FEATURES),
        "dummy_columns": list(dummy_columns),
    }


def _vectorize_row(row: dict[str, Any], schema: dict[str, Any]) -> list[float]:
    numeric = schema.get("numeric") or []
    categorical = schema.get("categorical") or []
    dummy_columns: list[str] = list(schema.get("dummy_columns") or [])
    cat_set = set(categorical)
    num_set = set(numeric)

    out: list[float] = []
    for col in dummy_columns:
        if col in num_set:
            out.append(float(_to_float(row.get(col)) or 0.0))
            continue
        prefix = col.split("_", 1)[0]
        if prefix in cat_set and "_" in col:
            _, suffix = col.split("_", 1)
            raw = row.get(prefix)
            if raw is None or str(raw).strip() == "":
                out.append(1.0 if suffix == "nan" else 0.0)
            else:
                out.append(1.0 if str(raw) == suffix else 0.0)
            continue
        out.append(0.0)
    return out


def _train_one_neighbourhood(
    neighbourhood: str,
    rows: list[dict[str, Any]],
    *,
    version_prefix: str,
    min_samples_ridge: int,
    min_samples_rf: int,
) -> list[TrainedModel]:
    if pd is None or Ridge is None or train_test_split is None:
        return []
    if not rows:
        return []

    frame = pd.DataFrame(rows)
    frame = frame[frame[TARGET_COLUMN].notna()].copy()
    if len(frame) < min_samples_ridge:
        return []

    feature_columns = list(NUMERIC_FEATURES) + list(CATEGORICAL_FEATURES)
    raw_features = frame[feature_columns].copy()
    for column in NUMERIC_FEATURES:
        raw_features[column] = pd.to_numeric(raw_features[column], errors="coerce")
        median_value = raw_features[column].median()
        if pd.isna(median_value):
            median_value = 0.0
        raw_features[column] = raw_features[column].fillna(median_value)

    for column in CATEGORICAL_FEATURES:
        raw_features[column] = raw_features[column].astype("string").fillna("")

    features = pd.get_dummies(raw_features, dummy_na=True).fillna(0.0)
    dummy_columns = list(features.columns)

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        frame[TARGET_COLUMN].astype(float),
        test_size=0.2,
        random_state=42,
    )

    models: list[TrainedModel] = []

    ridge = Ridge(alpha=1.0, random_state=42)
    ridge.fit(x_train, y_train)
    ridge_pred = ridge.predict(x_test)
    ridge_r2 = float(ridge.score(x_test, y_test))
    ridge_mae = float((abs(ridge_pred - y_test)).mean())
    schema = _build_feature_schema(dummy_columns)
    models.append(
        TrainedModel(
            neighbourhood=neighbourhood,
            model_type="ridge",
            version=f"{version_prefix}-ridge-v1",
            feature_schema=schema,
            payload={
                "intercept": float(getattr(ridge, "intercept_", 0.0)),
                "coefficients": [float(v) for v in getattr(ridge, "coef_", [])],
            },
            metrics={
                "train_count": int(len(x_train)),
                "test_count": int(len(x_test)),
                "r2": ridge_r2,
                "mae": ridge_mae,
            },
        )
    )

    if RandomForestRegressor is None or len(frame) < min_samples_rf:
        return models

    rf = RandomForestRegressor(
        n_estimators=80,
        random_state=42,
        max_depth=14,
        min_samples_leaf=5,
        n_jobs=-1,
    )
    rf.fit(x_train, y_train)
    rf_pred = rf.predict(x_test)
    rf_r2 = float(rf.score(x_test, y_test))
    rf_mae = float((abs(rf_pred - y_test)).mean())
    rf_blob = base64.b64encode(pickle.dumps(rf, protocol=pickle.HIGHEST_PROTOCOL)).decode("ascii")
    models.append(
        TrainedModel(
            neighbourhood=neighbourhood,
            model_type="rf",
            version=f"{version_prefix}-rf-v1",
            feature_schema=schema,
            payload={
                "pickle_b64": rf_blob,
            },
            metrics={
                "train_count": int(len(x_train)),
                "test_count": int(len(x_test)),
                "r2": rf_r2,
                "mae": rf_mae,
            },
        )
    )
    return models


def train_neighbourhood_models(
    rows: list[dict[str, Any]],
    *,
    version_prefix: str = "neighbourhood",
    min_samples_ridge: int = 150,
    min_samples_rf: int = 250,
) -> list[TrainedModel]:
    """Train ridge + RF models for each neighbourhood.

    Returns empty list if pandas/sklearn are unavailable.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        neighbourhood = _safe_neighbourhood(row.get("neighbourhood"))
        if neighbourhood is None:
            continue
        grouped.setdefault(neighbourhood, []).append(row)

    output: list[TrainedModel] = []
    for name, group_rows in sorted(grouped.items(), key=lambda item: item[0].lower()):
        output.extend(
            _train_one_neighbourhood(
                name,
                group_rows,
                version_prefix=version_prefix,
                min_samples_ridge=min_samples_ridge,
                min_samples_rf=min_samples_rf,
            )
        )
    return output


def predict_ridge(model: TrainedModel, row: dict[str, Any]) -> float | None:
    if model.model_type != "ridge":
        return None
    schema = model.feature_schema or {}
    dummy_columns: list[str] = list(schema.get("dummy_columns") or [])
    coefficients = model.payload.get("coefficients") or []
    if not dummy_columns or len(coefficients) != len(dummy_columns):
        return None
    intercept = float(model.payload.get("intercept") or 0.0)
    x = _vectorize_row(row, schema)
    return float(intercept + sum(float(a) * float(b) for a, b in zip(x, coefficients)))


def predict_rf(model: TrainedModel, row: dict[str, Any]) -> float | None:
    if model.model_type != "rf":
        return None
    blob = model.payload.get("pickle_b64")
    if not blob:
        return None
    try:
        from sklearn.ensemble import RandomForestRegressor as _RFR  # type: ignore
    except ImportError:  # pragma: no cover
        return None
    rf = pickle.loads(base64.b64decode(str(blob).encode("ascii")))
    if not isinstance(rf, _RFR):
        return None
    schema = model.feature_schema or {}
    x = _vectorize_row(row, schema)
    try:
        return float(rf.predict([x])[0])
    except Exception:
        return None


def serialize_feature_schema(schema: dict[str, Any]) -> str:
    return json.dumps(schema, sort_keys=True)


def serialize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True)
