# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Unit tests for the Open-Meteo forecast API endpoint (/forecast).

Tests verify:
1. 15-day forecast structure, derived variables, non-NASA attribution, and 6 domain series.
2. Schema validation against series.schema.json, recommendation.schema.json, and engine projection integration.
3. Response caching, custom forecast horizon, model selection, variable subsetting, and external coordinates.
4. Input validation (400 invalid_parameter) and upstream error mapping (504, 502, 422).
5. Isolation of snapshot generator modules from open_meteo imports.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
import pandas as pd
import pytest
from referencing import Registry, Resource
import requests

from apps.api.errors import APIError
from apps.api.forecast import (
    build_engine_projection,
    build_forecast_response,
)
from apps.api.main import create_app
from src.data import open_meteo
from src.data.errors import RemoteDataError
from src.data.paths import ROOT
from src.engine.model import Crop, Diagnosis, Plot, Priority, serialize_recommendation
from src.engine.recommend import recommend
from src.engine.rules import load_rules

SCHEMAS_DIR = ROOT / "docs" / "data-format"


def _build_schema_registry() -> tuple[Registry, dict[str, dict[str, Any]]]:
    """Load all JSON schemas from docs/data-format into a referencing registry."""
    raw_schemas: dict[str, dict[str, Any]] = {}
    resources: dict[str, Resource] = {}
    for path in SCHEMAS_DIR.glob("*.schema.json"):
        content = json.loads(path.read_text(encoding="utf-8"))
        raw_schemas[path.name] = content
        schema_id = content.get("$id") or path.name
        resources[schema_id] = Resource.from_contents(content)
    registry = Registry().with_resources(resources.items())
    return registry, raw_schemas


def _make_15_day_mock_frame() -> pd.DataFrame:
    """Create a deterministic 15-day Open-Meteo DataFrame for testing."""
    dates = pd.date_range("2026-11-15", periods=15, freq="D")
    data = {
        "temperature_2m_max": [30.0 + i * 0.2 for i in range(15)],
        "temperature_2m_min": [20.0 + i * 0.1 for i in range(15)],
        "precipitation_sum": [2.0 + i * 0.3 for i in range(15)],
        "precipitation_probability_max": [40.0 + i for i in range(15)],
        "et0_fao_evapotranspiration": [4.0 + (i % 3) * 0.2 for i in range(15)],
        "shortwave_radiation_sum": [20.0 + (i % 5) for i in range(15)],
        "wind_speed_10m_max": [12.0 + (i % 4) for i in range(15)],
    }
    frame = pd.DataFrame(data, index=dates).astype(float)
    frame.index.name = "date"
    return frame


class _FakeResponse:
    """Mock HTTP response matching requests.Response interface."""

    def __init__(self, status: int = 200, body: Any = None, text: str = "") -> None:
        self.status_code = status
        self._body = body
        self.text = text or (json.dumps(body) if body is not None else "")

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("invalid json")
        return self._body


class _FakeSession:
    """Mock requests.Session tracking calls and returning simulated Open-Meteo responses."""

    def __init__(self, full_payload: dict[str, Any]) -> None:
        self.full_payload = full_payload
        self.calls: list[tuple[str, dict[str, Any] | None, float | None]] = []

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> _FakeResponse:
        self.calls.append((url, params, timeout))
        if params and "daily" in params:
            req_vars = set(str(params["daily"]).split(","))
            filtered_daily: dict[str, list[Any]] = {"time": self.full_payload["daily"]["time"]}
            for v in req_vars:
                if v in self.full_payload["daily"]:
                    filtered_daily[v] = self.full_payload["daily"][v]
            lat = float(params["latitude"]) if "latitude" in params else self.full_payload["latitude"]
            lon = float(params["longitude"]) if "longitude" in params else self.full_payload["longitude"]
            body = {
                "latitude": lat,
                "longitude": lon,
                "daily": filtered_daily,
            }
            return _FakeResponse(200, body=body)
        return _FakeResponse(200, body=self.full_payload)


def test_forecast_15_days_all_series_have_nasa_false_and_open_meteo_attribution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Assert 15-day forecast structure, derived variables, non-NASA attribution, and domain series."""
    mock_frame = _make_15_day_mock_frame()
    monkeypatch.setattr(open_meteo, "fetch_forecast", lambda *args, **kwargs: mock_frame)

    app = create_app(forecast_cache_dir=tmp_path)
    client = TestClient(app)

    response = client.get("/forecast?lat=-10.685&lon=-37.425")
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["horizon_days"] == 15
    assert len(data["series"]) == 15
    assert data["nasa"] is False
    assert data["source"] == "open-meteo"
    assert "Open-Meteo" in data["attribution"]["dataset"]
    assert "CC BY 4.0" in data["attribution"]["dataset"]
    assert "not NASA" in data["attribution"]["notice"]
    assert data["plot"]["id"] == "sergipe_agreste_itabaiana"
    assert data["plot"]["region"] == "sergipe"

    # Verify derived values for day 0:
    # temperature_2m_max=30.0, min=20.0 -> mean=25.0
    # precipitation_sum=2.0, et0=4.0 -> water_balance=2.0 - 4.0 = -2.0
    day0_values = data["series"][0]["values"]
    assert day0_values["temperature_2m_mean"] == 25.0
    assert day0_values["water_balance"] == -2.0

    expected_domains = {"rain", "temperature", "et0", "water_balance", "radiation", "wind"}
    assert set(data["domains"].keys()) == expected_domains

    for domain_name in expected_domains:
        domain_series = data["domains"][domain_name]
        assert domain_series["nasa"] is False
        assert domain_series["source"] == "open-meteo"
        assert "Open-Meteo" in domain_series["attribution"]["dataset"]
        assert domain_series["attribution"]["url"] == "https://open-meteo.com/"
        assert "not NASA" in domain_series["attribution"]["notice"]
        assert len(domain_series["series"]) == 15

    for d_name, d_source in data["domain_sources"].items():
        assert d_source["nasa"] is False
        assert d_source["source"] == "open-meteo"

    for src in data["sources"]:
        assert src["nasa"] is False
        assert src["source"] == "open-meteo"


def test_forecast_schemas_and_engine_projection_integration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Validate forecast against series and recommendation JSON schemas, and verify engine integration."""
    mock_frame = _make_15_day_mock_frame()
    monkeypatch.setattr(open_meteo, "fetch_forecast", lambda *args, **kwargs: mock_frame)

    registry, raw_schemas = _build_schema_registry()

    series_validator = Draft202012Validator(
        raw_schemas["series.schema.json"],
        registry=registry,
        format_checker=FormatChecker(),
    )
    projection_validator = Draft202012Validator(
        {"$ref": "recommendation.schema.json#/$defs/projection"},
        registry=registry,
        format_checker=FormatChecker(),
    )
    source_attribution_validator = Draft202012Validator(
        {"$ref": "recommendation.schema.json#/$defs/sourceAttribution"},
        registry=registry,
        format_checker=FormatChecker(),
    )
    recommendation_validator = Draft202012Validator(
        raw_schemas["recommendation.schema.json"],
        registry=registry,
        format_checker=FormatChecker(),
    )

    resp = build_forecast_response(lat=-10.685, lon=-37.425, cache_dir=tmp_path)

    # 1. Validate every domain series against series.schema.json
    for domain_name, domain_series in resp.domains.items():
        series_dict = domain_series.to_series_schema_dict()
        series_validator.validate(series_dict)

    # 2. Validate projection and summary against recommendation.schema.json#/$defs/projection
    projection_validator.validate(resp.projection.model_dump())
    projection_validator.validate(resp.summary.model_dump())

    # 3. Validate sources against recommendation.schema.json#/$defs/sourceAttribution
    for src in resp.sources:
        source_attribution_validator.validate(src.model_dump())

    # 4. Integrate with decision engine
    proj = build_engine_projection(lat=-10.685, lon=-37.425, cache_dir=tmp_path)
    plot = Plot(
        lat=-10.685,
        lon=-37.425,
        radius_km=5.0,
        id="sergipe_agreste_itabaiana",
        name="Itabaiana (Agreste)",
        region="sergipe",
        elevation_m=180.0,
        slope_mean_pct=4.5,
        season="rainy",
        previous_crops=("maize",),
    )
    diagnosis = Diagnosis(
        period_start="2026-10-01",
        period_end="2026-11-14",
        rain_total_mm=120.0,
        rain_daily_mean_mm=2.7,
        et0_daily_mean_mm=4.5,
        water_balance_mm=-30.0,
        temperature_mean_c=26.5,
        temperature_max_c=31.2,
        ndvi_mean=0.45,
        elevation_m=180.0,
        slope_mean_pct=4.5,
    )
    rec = recommend(
        plot=plot,
        diagnosis=diagnosis,
        projection=proj,
        crop=Crop.MAIZE,
        priority=Priority.WATER,
        rules=load_rules(),
    )
    serialized_rec = serialize_recommendation(rec)
    recommendation_validator.validate(serialized_rec)

    # 5. Unavailable forecast handling when Open-Meteo fails
    monkeypatch.setattr(
        open_meteo,
        "fetch_forecast",
        lambda *args, **kwargs: (_ for _ in ()).throw(RemoteDataError("Request timed out")),
    )

    # With allow_unavailable=True: produces a valid fallback Projection with available=False
    proj_unavailable = build_engine_projection(
        lat=-10.685,
        lon=-37.425,
        cache_dir=tmp_path,
        allow_unavailable=True,
    )
    assert proj_unavailable.available is False
    assert len(proj_unavailable.sources) > 0
    assert proj_unavailable.sources[0].nasa is False

    rec_fallback = recommend(
        plot=plot,
        diagnosis=diagnosis,
        projection=proj_unavailable,
        crop=Crop.MAIZE,
        priority=Priority.WATER,
        rules=load_rules(),
    )
    assert "absent" in rec_fallback.uncertainty_note.lower()
    recommendation_validator.validate(serialize_recommendation(rec_fallback))

    # With allow_unavailable=False: raises APIError (504 upstream_timeout)
    with pytest.raises(APIError) as exc_info:
        build_engine_projection(
            lat=-10.685,
            lon=-37.425,
            cache_dir=tmp_path,
            allow_unavailable=False,
        )
    assert exc_info.value.status_code == 504
    assert exc_info.value.code == "upstream_timeout"


def test_forecast_caching_and_custom_days_and_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test disk caching, custom horizon days, forecast models, subset variables, and external plots."""
    dates = [f"2026-11-{15 + i:02d}" for i in range(15)]
    full_payload = {
        "latitude": -10.218,
        "longitude": -37.42,
        "daily": {
            "time": dates,
            "temperature_2m_max": [32.0 + i * 0.1 for i in range(15)],
            "temperature_2m_min": [22.0 + i * 0.1 for i in range(15)],
            "precipitation_sum": [1.5 + (i % 2) for i in range(15)],
            "precipitation_probability_max": [25.0 + i for i in range(15)],
            "et0_fao_evapotranspiration": [4.8 for _ in range(15)],
            "shortwave_radiation_sum": [21.5 for _ in range(15)],
            "wind_speed_10m_max": [11.0 for _ in range(15)],
        },
    }

    fake_session = _FakeSession(full_payload)
    monkeypatch.setattr(requests, "Session", lambda: fake_session)
    monkeypatch.setenv("FORECAST_CACHE_DIR", str(tmp_path))

    # App created with no arguments so it exercises FORECAST_CACHE_DIR environment variable
    app = create_app()
    client = TestClient(app)

    # First call: makes 1 upstream request to Open-Meteo
    res1 = client.get("/forecast?lat=-10.218&lon=-37.42&days=15&model=ecmwf_ifs")
    assert res1.status_code == 200, res1.text
    data1 = res1.json()
    assert len(fake_session.calls) == 1
    assert data1["cached"] is False
    assert data1["model"] == "ecmwf_ifs"
    assert data1["horizon_days"] == 15
    assert data1["plot"]["id"] == "sergipe_semiarido_ns_gloria"

    # Second identical call: hits disk cache, 0 new upstream requests
    res2 = client.get("/forecast?lat=-10.218&lon=-37.42&days=15&model=ecmwf_ifs")
    assert res2.status_code == 200, res2.text
    data2 = res2.json()
    assert len(fake_session.calls) == 1
    assert data2["cached"] is True

    # Custom variable subset: temperature_2m_max and precipitation_sum
    res3 = client.get(
        "/forecast?lat=-10.218&lon=-37.42&variables=temperature_2m_max,precipitation_sum",
    )
    assert res3.status_code == 200, res3.text
    data3 = res3.json()
    assert data3["rain"] is not None
    assert data3["temperature"] is not None
    assert data3["et0"] is None
    assert data3["water_balance"] is None
    assert data3["radiation"] is None
    assert data3["wind"] is None

    # External coordinate outside Sergipe
    res4 = client.get("/forecast?lat=0.0&lon=0.0")
    assert res4.status_code == 200, res4.text
    data4 = res4.json()
    assert data4["plot"]["region"] == "external"
    assert data4["plot"]["id"] == "PLOT"


def test_forecast_validation_and_upstream_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify 400 invalid_parameter validation errors and upstream error mappings (504, 502, 422)."""
    client = TestClient(create_app(forecast_cache_dir=tmp_path))

    invalid_query_paths = [
        "/forecast?lon=-37.425",  # missing lat
        "/forecast?lat=-10.685",  # missing lon
        "/forecast?lat=abc&lon=-37.425",  # non-numeric lat
        "/forecast?lat=95&lon=-37.425",  # lat > 89
        "/forecast?lat=-10.685&lon=200",  # lon > 180
        "/forecast?lat=-10.685&lon=-37.425&radius_km=0",  # radius_km <= 0
        "/forecast?lat=-10.685&lon=-37.425&radius_km=51",  # radius_km > 50
        "/forecast?lat=-10.685&lon=-37.425&days=0",  # days < 1
        "/forecast?lat=-10.685&lon=-37.425&days=20",  # days > 16
        "/forecast?lat=-10.685&lon=-37.425&days=10&forecast_days=15",  # conflicting days
        "/forecast?lat=-10.685&lon=-37.425&model=bad_model",  # unsupported model
        "/forecast?lat=-10.685&lon=-37.425&variables=BAD!",  # invalid variable syntax
        "/forecast?lat=-10.685&lon=-37.425&foo=1",  # unknown parameter
    ]

    for path in invalid_query_paths:
        res = client.get(path)
        assert res.status_code == 400, f"Expected 400 for {path}, got {res.status_code}: {res.text}"
        body = res.json()
        assert "error" in body, f"Response missing 'error' key for {path}"
        assert body["error"]["code"] == "invalid_parameter"
        assert isinstance(body["error"]["message"], str) and len(body["error"]["message"]) > 0

    # Upstream timeout -> 504 upstream_timeout
    monkeypatch.setattr(
        open_meteo,
        "fetch_forecast",
        lambda *args, **kwargs: (_ for _ in ()).throw(RemoteDataError("network timeout")),
    )
    res_to = client.get("/forecast?lat=-10.685&lon=-37.425")
    assert res_to.status_code == 504
    assert res_to.json()["error"]["code"] == "upstream_timeout"

    # Upstream HTTP 500 -> 502 upstream_error
    monkeypatch.setattr(
        open_meteo,
        "fetch_forecast",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RemoteDataError("Open-Meteo API unavailable after 3 attempts (HTTP 500). Try again later."),
        ),
    )
    res_502 = client.get("/forecast?lat=-10.685&lon=-37.425")
    assert res_502.status_code == 502
    assert res_502.json()["error"]["code"] == "upstream_error"

    # Upstream all-null data -> 422 no_data
    monkeypatch.setattr(
        open_meteo,
        "fetch_forecast",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RemoteDataError("Open-Meteo API returned only null values for this location"),
        ),
    )
    res_422 = client.get("/forecast?lat=-10.685&lon=-37.425")
    assert res_422.status_code == 422
    assert res_422.json()["error"]["code"] == "no_data"


def test_snapshot_generator_does_not_import_open_meteo() -> None:
    """Ensure snapshot generator modules contain zero imports or references to open_meteo."""
    import src.data.snapshot_sources
    import src.data.snapshots

    snapshot_modules = [
        ROOT / "src" / "data" / "snapshots.py",
        ROOT / "src" / "data" / "snapshot_sources.py",
        ROOT / "src" / "data" / "snapshot_output.py",
        ROOT / "src" / "data" / "snapshot_model.py",
    ]

    for file_path in snapshot_modules:
        assert file_path.is_file(), f"File {file_path} must exist"
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "open_meteo" not in alias.name, f"{file_path}: imported {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "open_meteo" not in node.module, f"{file_path}: from {node.module} import ..."
                for alias in node.names:
                    assert "open_meteo" not in alias.name, f"{file_path}: from ... import {alias.name}"
            elif isinstance(node, ast.Name):
                assert node.id != "open_meteo", f"{file_path}: reference to Name 'open_meteo'"
            elif isinstance(node, ast.Attribute):
                assert node.attr != "open_meteo", f"{file_path}: reference to Attribute 'open_meteo'"

    assert "open_meteo" not in src.data.snapshots.__dict__
    assert "open_meteo" not in src.data.snapshot_sources.__dict__
