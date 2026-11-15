# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Tests for the GET /diagnosis endpoint, spatial matching, and schema compliance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from apps.api import build_engine_diagnosis, create_app
from src.engine import (
    Crop,
    Priority,
    Projection,
    load_rules,
    recommend,
    serialize_recommendation,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "docs" / "data-format"

SERIES_SCHEMA = json.loads((SCHEMAS_DIR / "series.schema.json").read_text(encoding="utf-8"))
STATIC_SCHEMA = json.loads((SCHEMAS_DIR / "static.schema.json").read_text(encoding="utf-8"))
REC_SCHEMA = json.loads((SCHEMAS_DIR / "recommendation.schema.json").read_text(encoding="utf-8"))

REGISTRY = Registry().with_resources(
    [
        ("series.schema.json", Resource.from_contents(SERIES_SCHEMA)),
        ("static.schema.json", Resource.from_contents(STATIC_SCHEMA)),
        ("recommendation.schema.json", Resource.from_contents(REC_SCHEMA)),
        (REC_SCHEMA["$id"], Resource.from_contents(REC_SCHEMA)),
    ]
)

VALIDATOR_SERIES = Draft202012Validator(SERIES_SCHEMA, registry=REGISTRY)
VALIDATOR_STATIC = Draft202012Validator(STATIC_SCHEMA, registry=REGISTRY)
VALIDATOR_DIAGNOSIS_DEF = Draft202012Validator(
    {"$ref": "recommendation.schema.json#/$defs/diagnosis"},
    registry=REGISTRY,
)
VALIDATOR_SOURCE_DEF = Draft202012Validator(
    {"$ref": "recommendation.schema.json#/$defs/sourceAttribution"},
    registry=REGISTRY,
)
VALIDATOR_BARE_SOIL_DEF = Draft202012Validator(
    {"$ref": "recommendation.schema.json#/$defs/bareSoilWindow"},
    registry=REGISTRY,
)


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_diagnosis_pilot_itabaiana(client: TestClient) -> None:
    """Exact coordinates of Itabaiana pilot site."""
    response = client.get("/diagnosis?lat=-10.685&lon=-37.425&radius_km=5.0")
    assert response.status_code == 200, response.text
    data = response.json()

    # 1. Plot & matching
    plot = data["plot"]
    assert plot["lat"] == -10.685
    assert plot["lon"] == -37.425
    assert plot["radius_km"] == 5.0
    assert plot["region"] == "sergipe"
    matched = plot["matched_point"]
    assert matched["id"] == "sergipe_agreste_itabaiana"
    assert matched["kind"] == "pilot"
    assert matched["distance_km"] == 0.0

    # 2. Strict series schema validation
    for domain in ("rain", "soil_moisture", "temperature", "et0", "water_balance", "ndvi", "gldas"):
        domain_data = data.get(domain)
        if domain_data is not None:
            VALIDATOR_SERIES.validate(domain_data)
            assert matched["id"] in domain_data["points"]

    # 3. Static terrain schema validation
    VALIDATOR_STATIC.validate(data["terrain"])
    assert matched["id"] in data["terrain"]["points"]
    terrain_point = data["terrain"]["points"][matched["id"]]
    assert terrain_point["elevation_m"] is not None
    assert terrain_point["slope_mean_pct"] is not None

    # 4. Engine diagnosis summary validation
    summary = data["summary"]
    VALIDATOR_DIAGNOSIS_DEF.validate(summary)
    assert summary["rain_total_mm"] == pytest.approx(28.2, rel=1e-2)
    assert summary["temperature_mean_c"] == pytest.approx(28.51, rel=1e-2)
    assert summary["water_balance_mm"] == pytest.approx(-189.33, rel=1e-2)
    assert summary["et0_daily_mean_mm"] is not None
    assert summary["soil_moisture_surface_m3m3"] is not None
    assert summary["soil_moisture_root_kgm2"] is not None
    assert summary["ndvi_mean"] is not None
    assert summary["elevation_m"] is not None
    assert summary["slope_mean_pct"] is not None

    # 5. Attributions & domain mapping
    for source_entry in data["sources"]:
        VALIDATOR_SOURCE_DEF.validate(source_entry)
        assert source_entry["nasa"] is True

    domain_sources = data["domain_sources"]
    for required_domain in ("rain", "soil_moisture", "temperature", "et0", "water_balance", "terrain", "ndvi", "gldas"):
        assert required_domain in domain_sources
        assert domain_sources[required_domain]["nasa"] is True


def test_diagnosis_pilot_gloria(client: TestClient) -> None:
    """Exact coordinates of Nossa Senhora da Glória pilot site."""
    response = client.get("/diagnosis?lat=-10.218&lon=-37.42&radius_km=10.0")
    assert response.status_code == 200, response.text
    data = response.json()

    plot = data["plot"]
    assert plot["radius_km"] == 10.0
    matched = plot["matched_point"]
    assert matched["id"] == "sergipe_semiarido_ns_gloria"
    assert matched["kind"] == "pilot"
    assert matched["distance_km"] == 0.0

    summary = data["summary"]
    VALIDATOR_DIAGNOSIS_DEF.validate(summary)
    assert summary["rain_total_mm"] == pytest.approx(4.9, rel=1e-2)
    assert summary["temperature_mean_c"] == pytest.approx(29.58, rel=1e-2)
    assert summary["water_balance_mm"] == pytest.approx(-216.38, rel=1e-2)
    assert summary["et0_daily_mean_mm"] is not None
    assert summary["soil_moisture_surface_m3m3"] is not None
    assert summary["soil_moisture_root_kgm2"] is not None
    assert summary["ndvi_mean"] is not None
    assert summary["elevation_m"] is not None
    assert summary["slope_mean_pct"] is not None


def test_diagnosis_grid_matching_and_bare_soil(client: TestClient) -> None:
    """Query a location distant from pilots (matching SE019 with bare soil windows)."""
    response = client.get("/diagnosis?lat=-10.25&lon=-37.75")
    assert response.status_code == 200, response.text
    data = response.json()

    matched = data["plot"]["matched_point"]
    assert matched["id"] == "SE019"
    assert matched["kind"] == "grid"

    # Verify bare soil window detection
    windows = data["bare_soil_windows"]
    assert len(windows) >= 1
    for w in windows:
        VALIDATOR_BARE_SOIL_DEF.validate(w)
        assert w["ndvi_mean"] is not None
        assert w["ndvi_mean"] <= 0.30


def test_calendar_expansion_and_missing_days(client: TestClient) -> None:
    """Verify daily series have every calendar date from period start to end."""
    response = client.get("/diagnosis?lat=-10.685&lon=-37.425")
    assert response.status_code == 200
    data = response.json()

    # In raw smap.json, only 28 entries were stored due to null days omitted.
    # The calendar spine must have 31 entries between 2026-10-13 and 2026-11-12 inclusive.
    smap_series = data["soil_moisture"]
    period = smap_series["period"]
    assert period["start"] == "2026-10-13"
    assert period["end"] == "2026-11-12"

    pts = smap_series["points"]["sergipe_agreste_itabaiana"]
    assert len(pts) == 31

    # Check date continuity and ascending order
    dates = [p["time"] for p in pts]
    assert dates == sorted(dates)
    assert dates[0] == "2026-10-13"
    assert dates[-1] == "2026-11-12"

    # Missing days should have None explicitly
    null_entries = [p for p in pts if p["values"]["soil_moisture"] is None]
    assert len(null_entries) > 0

    # POWER-based domains (et0 and water_balance) contiguous calendar and explicit None check:
    # In power.json, period is 2026-10-09..2026-11-07 (30 contiguous calendar days).
    # On 2026-11-05, ALLSKY_SFC_SW_DWN was unavailable, leading to ET0_FAO56 and WATER_BALANCE being None.
    for domain_key, var_key in [("et0", "ET0_FAO56"), ("water_balance", "WATER_BALANCE")]:
        series = data[domain_key]
        assert series["period"]["start"] == "2026-10-09"
        assert series["period"]["end"] == "2026-11-07"
        series_pts = series["points"]["sergipe_agreste_itabaiana"]
        assert len(series_pts) == 30

        series_dates = [p["time"] for p in series_pts]
        assert series_dates == sorted(series_dates)
        assert series_dates[0] == "2026-10-09"
        assert series_dates[-1] == "2026-11-07"

        nov5_entry = next(p for p in series_pts if p["time"] == "2026-11-05")
        assert nov5_entry["values"][var_key] is None

        # Verify other days have valid non-null numerical values
        non_null_entries = [p for p in series_pts if p["values"][var_key] is not None]
        assert len(non_null_entries) > 0


def test_invalid_parameters_return_400(client: TestClient) -> None:
    """Query parameter validation errors return 400 invalid_parameter."""
    # Missing lat/lon
    res = client.get("/diagnosis")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_parameter"

    res = client.get("/diagnosis?lat=-10.0")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_parameter"

    # Non-numeric
    res = client.get("/diagnosis?lat=invalid&lon=-37.0")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_parameter"

    # Out of range coordinates
    res = client.get("/diagnosis?lat=95.0&lon=-37.0")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_parameter"

    res = client.get("/diagnosis?lat=-10.0&lon=200.0")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_parameter"

    # Radius out of range
    res = client.get("/diagnosis?lat=-10.0&lon=-37.0&radius_km=0.0")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_parameter"

    res = client.get("/diagnosis?lat=-10.0&lon=-37.0&radius_km=60.0")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_parameter"

    # Unknown parameter rejected
    res = client.get("/diagnosis?lat=-10.0&lon=-37.0&unexpected=1")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_parameter"


def test_outside_sergipe_returns_422(client: TestClient) -> None:
    """Coordinates outside the Sergipe bounding box return 422 no_data."""
    # Point at (0.0, 0.0)
    res = client.get("/diagnosis?lat=0.0&lon=0.0")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "no_data"

    # Point in São Paulo (-23.55, -46.63)
    res = client.get("/diagnosis?lat=-23.55&lon=-46.63")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "no_data"


def test_build_engine_diagnosis_integrates_with_recommend() -> None:
    """Verify build_engine_diagnosis feeds cleanly into src.engine.recommend()."""
    plot, diagnosis = build_engine_diagnosis(lat=-10.685, lon=-37.425, radius_km=5.0)

    assert plot.id == "sergipe_agreste_itabaiana"
    assert plot.region == "sergipe"
    assert diagnosis.rain_total_mm is not None
    assert diagnosis.temperature_mean_c is not None
    assert diagnosis.water_balance_mm is not None

    projection = Projection(
        period_start=diagnosis.period_end,
        period_end=diagnosis.period_end,
        horizon_days=15,
        available=False,
    )
    rules = load_rules()

    rec = recommend(
        plot=plot,
        crop=Crop.MAIZE,
        priority=Priority.WATER,
        diagnosis=diagnosis,
        projection=projection,
        rules=rules,
    )

    serialized = serialize_recommendation(rec)
    rec_validator = Draft202012Validator(REC_SCHEMA, registry=REGISTRY)
    rec_validator.validate(serialized)
    assert len(rec.strategies) >= 3


def test_synthetic_tmp_path_handling(tmp_path: Path) -> None:
    """Test custom data_dir injection and missing snapshot error handling."""
    custom_app = create_app(data_dir=tmp_path)
    custom_client = TestClient(custom_app)

    # Missing sergipe directory returns 503
    res = custom_client.get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "server_not_configured"

    # Create minimal sergipe directory with core files
    sergipe_dir = tmp_path / "sergipe"
    sergipe_dir.mkdir(parents=True)

    minimal_power = {
        "source": "power",
        "region": "sergipe",
        "variables": [{"name": "T2M", "long_name": "Air temperature", "unit": "°C"}],
        "aggregation": "nearest_cell",
        "resolution": "0.5°",
        "period": {"start": "2026-10-01", "end": "2026-10-03"},
        "attribution": {"dataset": "POWER", "doi": None, "url": "https://power.larc.nasa.gov/", "notice": None},
        "points": {"SE001": [{"time": "2026-10-01", "values": {"T2M": 28.0}}]},
    }
    minimal_imerg = {
        "source": "imerg",
        "region": "sergipe",
        "variables": [{"name": "precipitation", "long_name": "Rain", "unit": "mm/day"}],
        "aggregation": "cell_mean",
        "resolution": "0.1°",
        "period": {"start": "2026-10-01", "end": "2026-10-03"},
        "attribution": {"dataset": "IMERG", "doi": None, "url": "https://gpm.nasa.gov/", "notice": None},
        "points": {"SE001": [{"time": "2026-10-01", "values": {"precipitation": 5.0}}]},
    }
    minimal_smap = {
        "source": "smap",
        "region": "sergipe",
        "variables": [{"name": "soil_moisture", "long_name": "SM", "unit": "m3/m3"}],
        "aggregation": "cell_mean",
        "resolution": "9 km",
        "period": {"start": "2026-10-01", "end": "2026-10-03"},
        "attribution": {"dataset": "SMAP", "doi": None, "url": "https://smap.jpl.nasa.gov/", "notice": None},
        "points": {"SE001": [{"time": "2026-10-01", "values": {"soil_moisture": 0.15}}]},
    }
    minimal_srtm = {
        "source": "srtm",
        "region": "sergipe",
        "variables": [{"name": "elevation_m", "long_name": "Elevation", "unit": "m"}],
        "aggregation": "window_mean",
        "resolution": "30 m",
        "attribution": {"dataset": "SRTM", "doi": None, "url": "https://planetarycomputer.microsoft.com/", "notice": None},
        "points": {"SE001": {"elevation_m": 120.0}},
    }

    (sergipe_dir / "power.json").write_text(json.dumps(minimal_power), encoding="utf-8")
    (sergipe_dir / "imerg.json").write_text(json.dumps(minimal_imerg), encoding="utf-8")
    (sergipe_dir / "smap.json").write_text(json.dumps(minimal_smap), encoding="utf-8")
    (sergipe_dir / "srtm.json").write_text(json.dumps(minimal_srtm), encoding="utf-8")

    res = custom_client.get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["plot"]["matched_point"]["id"] == "SE001"
    assert res_data["gldas"] is None
    assert res_data["ndvi"] is None


def test_synthetic_modis_fallback_and_bare_soil_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify VIIRS all-None fallback to MODIS, bare soil window detection, and DIAGNOSIS_DATA_DIR env var override."""
    sergipe_dir = tmp_path / "sergipe"
    sergipe_dir.mkdir(parents=True)

    synthetic_power = {
        "source": "power",
        "region": "sergipe",
        "variables": [
            {"name": "T2M", "long_name": "Air temperature at 2m", "unit": "°C"},
            {"name": "ET0_FAO56", "long_name": "Reference evapotranspiration", "unit": "mm/day"},
            {"name": "WATER_BALANCE", "long_name": "Water balance", "unit": "mm/day"},
        ],
        "aggregation": "nearest_cell",
        "resolution": "0.5°",
        "period": {"start": "2026-09-01", "end": "2026-09-03"},
        "attribution": {
            "dataset": "POWER",
            "doi": None,
            "url": "https://power.larc.nasa.gov/",
            "notice": None,
        },
        "points": {
            "SE001": [
                {"time": "2026-09-01", "values": {"T2M": 26.5, "ET0_FAO56": 5.0, "WATER_BALANCE": -3.0}},
                {"time": "2026-09-02", "values": {"T2M": 27.0, "ET0_FAO56": 5.2, "WATER_BALANCE": -3.2}},
                {"time": "2026-09-03", "values": {"T2M": 26.8, "ET0_FAO56": 4.8, "WATER_BALANCE": -2.8}},
            ]
        },
    }
    synthetic_imerg = {
        "source": "imerg",
        "region": "sergipe",
        "variables": [
            {"name": "precipitation", "long_name": "Daily precipitation", "unit": "mm/day"}
        ],
        "aggregation": "cell_mean",
        "resolution": "0.1°",
        "period": {"start": "2026-09-01", "end": "2026-09-03"},
        "attribution": {
            "dataset": "IMERG",
            "doi": "10.5067/GPM/IMERGDF/DAY/07",
            "url": "https://gpm.nasa.gov/",
            "notice": None,
        },
        "points": {
            "SE001": [
                {"time": "2026-09-01", "values": {"precipitation": 2.0}},
                {"time": "2026-09-02", "values": {"precipitation": 2.0}},
                {"time": "2026-09-03", "values": {"precipitation": 2.0}},
            ]
        },
    }
    synthetic_smap = {
        "source": "smap",
        "region": "sergipe",
        "variables": [
            {"name": "soil_moisture", "long_name": "Surface soil moisture", "unit": "m3/m3"}
        ],
        "aggregation": "cell_mean",
        "resolution": "9 km",
        "period": {"start": "2026-09-01", "end": "2026-09-03"},
        "attribution": {
            "dataset": "SMAP",
            "doi": "10.5067/X2QI1IKQ9NGQ",
            "url": "https://smap.jpl.nasa.gov/",
            "notice": None,
        },
        "points": {
            "SE001": [
                {"time": "2026-09-01", "values": {"soil_moisture": 0.12}},
                {"time": "2026-09-02", "values": {"soil_moisture": 0.11}},
                {"time": "2026-09-03", "values": {"soil_moisture": 0.10}},
            ]
        },
    }
    synthetic_srtm = {
        "source": "srtm",
        "region": "sergipe",
        "variables": [
            {"name": "elevation_m", "long_name": "Elevation above sea level", "unit": "m"},
            {"name": "slope_mean_pct", "long_name": "Mean terrain slope", "unit": "%"},
        ],
        "aggregation": "window_mean",
        "resolution": "30 m",
        "attribution": {
            "dataset": "SRTM",
            "doi": None,
            "url": "https://planetarycomputer.microsoft.com/",
            "notice": None,
        },
        "points": {
            "SE001": {"elevation_m": 150.0, "slope_mean_pct": 3.5}
        },
    }
    synthetic_viirs = {
        "source": "viirs",
        "region": "sergipe",
        "variables": [
            {"name": "NDVI", "long_name": "Normalized Difference Vegetation Index", "unit": "dimensionless"}
        ],
        "aggregation": "window_mean",
        "resolution": "500 m",
        "period": {"start": "2026-09-01", "end": "2026-10-18"},
        "attribution": {
            "dataset": "VIIRS",
            "doi": "10.5067/VIIRS/VNP13A1.002",
            "url": "https://lpdaac.usgs.gov/",
            "notice": None,
        },
        "points": {
            "SE001": [
                {"time": "2026-09-01", "values": {"NDVI": None}},
                {"time": "2026-09-17", "values": {"NDVI": None}},
                {"time": "2026-10-03", "values": {"NDVI": None}},
            ]
        },
    }
    synthetic_modis = {
        "source": "modis",
        "region": "sergipe",
        "variables": [
            {"name": "NDVI", "long_name": "Normalized Difference Vegetation Index", "unit": "dimensionless"}
        ],
        "aggregation": "window_mean",
        "resolution": "250 m",
        "period": {"start": "2026-09-01", "end": "2026-10-18"},
        "attribution": {
            "dataset": "MODIS",
            "doi": "10.5067/MODIS/MOD13Q1.061",
            "url": "https://lpdaac.usgs.gov/",
            "notice": None,
        },
        "points": {
            "SE001": [
                {"time": "2026-09-01", "values": {"NDVI": 0.18}},
                {"time": "2026-09-17", "values": {"NDVI": 0.24}},
                {"time": "2026-10-03", "values": {"NDVI": 0.52}},
            ]
        },
    }
    synthetic_points = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "SE001",
                "geometry": {"type": "Point", "coordinates": [-37.425, -10.685]},
                "properties": {"id": "SE001", "lat": -10.685, "lon": -37.425},
            }
        ],
    }

    # Validate snapshot inputs against strict schemas
    VALIDATOR_SERIES.validate(synthetic_power)
    VALIDATOR_SERIES.validate(synthetic_imerg)
    VALIDATOR_SERIES.validate(synthetic_smap)
    VALIDATOR_STATIC.validate(synthetic_srtm)
    VALIDATOR_SERIES.validate(synthetic_viirs)
    VALIDATOR_SERIES.validate(synthetic_modis)

    (sergipe_dir / "power.json").write_text(json.dumps(synthetic_power), encoding="utf-8")
    (sergipe_dir / "imerg.json").write_text(json.dumps(synthetic_imerg), encoding="utf-8")
    (sergipe_dir / "smap.json").write_text(json.dumps(synthetic_smap), encoding="utf-8")
    (sergipe_dir / "srtm.json").write_text(json.dumps(synthetic_srtm), encoding="utf-8")
    (sergipe_dir / "viirs.json").write_text(json.dumps(synthetic_viirs), encoding="utf-8")
    (sergipe_dir / "modis.json").write_text(json.dumps(synthetic_modis), encoding="utf-8")
    (sergipe_dir / "points.geojson").write_text(json.dumps(synthetic_points), encoding="utf-8")

    # Set DIAGNOSIS_DATA_DIR env var and call create_app() with no data_dir argument
    monkeypatch.setenv("DIAGNOSIS_DATA_DIR", str(tmp_path))
    app = create_app()
    client = TestClient(app)

    response = client.get("/diagnosis?lat=-10.685&lon=-37.425")
    assert response.status_code == 200, response.text
    data = response.json()

    # Validate all returned envelopes against JSON schemas
    for domain in ("rain", "soil_moisture", "temperature", "et0", "water_balance", "ndvi"):
        domain_data = data.get(domain)
        if domain_data is not None:
            VALIDATOR_SERIES.validate(domain_data)
    VALIDATOR_STATIC.validate(data["terrain"])
    VALIDATOR_DIAGNOSIS_DEF.validate(data["summary"])
    for source_entry in data["sources"]:
        VALIDATOR_SOURCE_DEF.validate(source_entry)
    for window_entry in data["bare_soil_windows"]:
        VALIDATOR_BARE_SOIL_DEF.validate(window_entry)

    # Verify VIIRS -> MODIS fallback
    assert data["ndvi"]["source"] == "modis"
    assert data["domain_sources"]["ndvi"] == {"source": "modis", "nasa": True}
    assert any(s["source"] == "modis" and s["nasa"] is True for s in data["sources"])

    # Verify bare soil window detection and statistics
    assert len(data["bare_soil_windows"]) == 1
    assert data["bare_soil_windows"][0]["start"] == "2026-09-01"
    assert data["bare_soil_windows"][0]["end"] == "2026-10-02"
    assert data["bare_soil_windows"][0]["ndvi_mean"] == pytest.approx(0.21, abs=1e-3)
