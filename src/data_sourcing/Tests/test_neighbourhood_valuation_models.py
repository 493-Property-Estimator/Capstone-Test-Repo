from __future__ import annotations

import base64
import pickle

import pytest

from src.data_sourcing import neighbourhood_valuation_models as nvm
from src.data_sourcing import bedbath_models


def test_helpers_safe_neighbourhood_and_to_float():
    assert nvm._safe_neighbourhood(None) is None
    assert nvm._safe_neighbourhood("   ") is None
    assert nvm._safe_neighbourhood(" Downtown ") == "Downtown"

    assert nvm._to_float(None) is None
    assert nvm._to_float("x") is None
    assert nvm._to_float("1.5") == 1.5


def test_vectorize_row_numeric_and_categorical_branches():
    schema = {
        "numeric": ["lot_size"],
        "categorical": ["zoning"],
        "dummy_columns": ["lot_size", "zoning_nan", "zoning_DC1", "unknown_feature"],
    }
    row = {"lot_size": "10", "zoning": ""}
    vec = nvm._vectorize_row(row, schema)
    assert vec == [10.0, 1.0, 0.0, 0.0]

    row2 = {"lot_size": 0, "zoning": "DC1"}
    vec2 = nvm._vectorize_row(row2, schema)
    assert vec2 == [0.0, 0.0, 1.0, 0.0]


def test_train_neighbourhood_models_trains_ridge_and_rf_with_imputation():
    rows = []
    for i in range(12):
        rows.append(
            {
                "canonical_location_id": f"loc-{i}",
                "neighbourhood": "Downtown",
                "assessment_value": 100000.0 + (i * 1000.0),
                "lot_size": None if i % 3 == 0 else 250.0 + i,
                "total_gross_area": 100.0 + i,
                "year_built": 2000 if i % 4 else None,
                "bedrooms_estimated": 3,
                "bathrooms_estimated": 2.0,
                "zoning": "DC1",
                "tax_class": "Residential",
                "garage": "Y",
                "assessment_class_1": "Residential",
            }
        )
    rows.append({"neighbourhood": None, "assessment_value": 1})

    models = nvm.train_neighbourhood_models(rows, min_samples_ridge=5, min_samples_rf=5, version_prefix="t")
    types = {m.model_type for m in models}
    assert "ridge" in types
    assert "rf" in types
    assert all(m.neighbourhood == "Downtown" for m in models)


def test_train_one_neighbourhood_empty_and_insufficient_samples():
    assert nvm._train_one_neighbourhood("X", [], version_prefix="t", min_samples_ridge=1, min_samples_rf=1) == []

    small_rows = [
        {"neighbourhood": "X", "assessment_value": 1.0, "zoning": "a"},
        {"neighbourhood": "X", "assessment_value": 2.0, "zoning": "a"},
    ]
    assert nvm._train_one_neighbourhood("X", small_rows, version_prefix="t", min_samples_ridge=5, min_samples_rf=5) == []


def test_train_one_neighbourhood_median_nan_and_ridge_only_path():
    rows = []
    for i in range(10):
        rows.append(
            {
                "neighbourhood": "Downtown",
                "assessment_value": 100000.0 + i,
                "lot_size": None,
                "total_gross_area": 100.0,
                "year_built": 2000,
                "bedrooms_estimated": 3,
                "bathrooms_estimated": 2.0,
                "zoning": "DC1",
                "tax_class": "Residential",
                "garage": "Y",
                "assessment_class_1": "Residential",
            }
        )
    models = nvm.train_neighbourhood_models(rows, min_samples_ridge=5, min_samples_rf=9999, version_prefix="t2")
    assert [m.model_type for m in models] == ["ridge"]


def test_train_one_neighbourhood_returns_empty_when_no_libs(monkeypatch):
    monkeypatch.setattr(nvm, "pd", None)
    monkeypatch.setattr(nvm, "Ridge", None)
    monkeypatch.setattr(nvm, "train_test_split", None)
    assert (
        nvm._train_one_neighbourhood("Downtown", [{"neighbourhood": "Downtown", "assessment_value": 1}], version_prefix="t", min_samples_ridge=1, min_samples_rf=1)
        == []
    )


def test_predict_ridge_and_guardrails():
    model = nvm.TrainedModel(
        neighbourhood="Downtown",
        model_type="ridge",
        version="v",
        feature_schema={"dummy_columns": ["lot_size"], "numeric": ["lot_size"], "categorical": []},
        payload={"coefficients": [2.0], "intercept": 1.0},
        metrics={},
    )
    assert nvm.predict_ridge(model, {"lot_size": 3}) == 7.0

    not_ridge = nvm.TrainedModel(
        neighbourhood="Downtown",
        model_type="rf",
        version="v",
        feature_schema={},
        payload={},
        metrics={},
    )
    assert nvm.predict_ridge(not_ridge, {}) is None

    bad_schema = nvm.TrainedModel(
        neighbourhood="Downtown",
        model_type="ridge",
        version="v",
        feature_schema={"dummy_columns": ["a", "b"], "numeric": [], "categorical": []},
        payload={"coefficients": [1.0], "intercept": 0.0},
        metrics={},
    )
    assert nvm.predict_ridge(bad_schema, {}) is None


def test_predict_rf_success_and_failure_paths():
    from sklearn.ensemble import RandomForestRegressor

    rf = RandomForestRegressor(n_estimators=5, random_state=42)
    rf.fit([[0.0], [1.0], [2.0]], [0.0, 1.0, 2.0])
    blob = base64.b64encode(pickle.dumps(rf, protocol=pickle.HIGHEST_PROTOCOL)).decode("ascii")

    good = nvm.TrainedModel(
        neighbourhood="Downtown",
        model_type="rf",
        version="v",
        feature_schema={"dummy_columns": ["lot_size"], "numeric": ["lot_size"], "categorical": []},
        payload={"pickle_b64": blob},
        metrics={},
    )
    assert nvm.predict_rf(good, {"lot_size": 1.0}) is not None

    not_rf = nvm.TrainedModel(
        neighbourhood="Downtown",
        model_type="ridge",
        version="v",
        feature_schema={},
        payload={},
        metrics={},
    )
    assert nvm.predict_rf(not_rf, {}) is None

    missing_blob = nvm.TrainedModel(
        neighbourhood="Downtown",
        model_type="rf",
        version="v",
        feature_schema={},
        payload={},
        metrics={},
    )
    assert nvm.predict_rf(missing_blob, {}) is None

    wrong_type = nvm.TrainedModel(
        neighbourhood="Downtown",
        model_type="rf",
        version="v",
        feature_schema={},
        payload={"pickle_b64": base64.b64encode(pickle.dumps(object())).decode("ascii")},
        metrics={},
    )
    assert nvm.predict_rf(wrong_type, {}) is None

    bad_predict = nvm.TrainedModel(
        neighbourhood="Downtown",
        model_type="rf",
        version="v",
        feature_schema={"dummy_columns": [], "numeric": [], "categorical": []},
        payload={"pickle_b64": blob},
        metrics={},
    )
    assert nvm.predict_rf(bad_predict, {}) is None


def test_serializers():
    assert nvm.serialize_feature_schema({"b": 1, "a": 2}) == '{"a": 2, "b": 1}'
    assert nvm.serialize_payload({"b": 1, "a": 2}) == '{"a": 2, "b": 1}'


def test_bedbath_select_model_grouped_fallback(monkeypatch):
    monkeypatch.setattr(bedbath_models, "pd", None)
    model = bedbath_models.select_model(version_prefix="x")
    assert model.__class__.__name__ == "GroupedBedBathModel"
