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
    assert summary["period_start"] == "2026-10-15"
    assert summary["period_end"] == "2026-11-07"
    assert summary["rain_total_mm"] == pytest.approx(27.3, rel=1e-2)
    assert summary["temperature_mean_c"] == pytest.approx(28.92, rel=1e-2)
    assert summary["water_balance_mm"] == pytest.approx(-135.95, rel=1e-2)
    assert summary["et0_daily_mean_mm"] == pytest.approx(7.1, rel=1e-2)
    assert summary["soil_moisture_surface_m3m3"] is not None
    assert summary["soil_moisture_root_kgm2"] is not None
    assert summary["ndvi_mean"] is not None
    assert summary["elevation_m"] is not None
    assert summary["slope_mean_pct"] is not None

    # 4b. Coverage disclosure validation
    coverage = data["coverage"]
    assert coverage["period_start"] == "2026-10-15"
    assert coverage["period_end"] == "2026-11-07"
    assert coverage["aligned"] is True
    assert coverage["expected_days"] == 24
    assert coverage["paired_days"] == 23
    assert coverage["missing_days"] == 1
    assert coverage["missing_dates"] == ["2026-11-05"]
    assert coverage["complete"] is False

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
    assert summary["period_start"] == "2026-10-15"
    assert summary["period_end"] == "2026-11-07"
    assert summary["rain_total_mm"] == pytest.approx(4.9, rel=1e-2)
    assert summary["temperature_mean_c"] == pytest.approx(30.0, rel=1e-2)
    assert summary["water_balance_mm"] == pytest.approx(-176.6, rel=1e-2)
    assert summary["et0_daily_mean_mm"] == pytest.approx(7.89, rel=1e-2)
    assert summary["soil_moisture_surface_m3m3"] is not None
    assert summary["soil_moisture_root_kgm2"] is not None
    assert summary["ndvi_mean"] is not None
    assert summary["elevation_m"] is not None
    assert summary["slope_mean_pct"] is not None

    coverage = data["coverage"]
    assert coverage["period_start"] == "2026-10-15"
    assert coverage["period_end"] == "2026-11-07"
    assert coverage["aligned"] is True
    assert coverage["expected_days"] == 24
    assert coverage["paired_days"] == 23
    assert coverage["missing_days"] == 1
    assert coverage["missing_dates"] == ["2026-11-05"]
    assert coverage["complete"] is False


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
    assert diagnosis.period_start == "2026-10-15"
    assert diagnosis.period_end == "2026-11-07"
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

    minimal_points = {
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

    (sergipe_dir / "power.json").write_text(json.dumps(minimal_power), encoding="utf-8")
    (sergipe_dir / "imerg.json").write_text(json.dumps(minimal_imerg), encoding="utf-8")
    (sergipe_dir / "smap.json").write_text(json.dumps(minimal_smap), encoding="utf-8")
    (sergipe_dir / "srtm.json").write_text(json.dumps(minimal_srtm), encoding="utf-8")
    (sergipe_dir / "points.geojson").write_text(json.dumps(minimal_points), encoding="utf-8")

    res = custom_client.get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["plot"]["matched_point"]["id"] == "SE001"
    assert res_data["gldas"] is None
    assert res_data["ndvi"] is None
    assert res_data["coverage"]["paired_days"] == 1
    assert res_data["coverage"]["expected_days"] == 3
    assert res_data["coverage"]["complete"] is False


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


def test_diagnosis_plot_reports_the_municipality_code(client: TestClient) -> None:
    body = client.get("/diagnosis", params={"lat": -10.685, "lon": -37.425}).json()

    assert body["plot"]["municipality_code"] == "2802908"


def _write_synthetic_snapshot_dir(
    root_dir: Path,
    *,
    points_features: list[dict[str, object]] | None = None,
    power_points: dict[str, list[dict[str, object]]] | None = None,
    imerg_points: dict[str, list[dict[str, object]]] | None = None,
    smap_points: dict[str, list[dict[str, object]]] | None = None,
    srtm_points: dict[str, dict[str, float | None]] | None = None,
    power_period: dict[str, str] | None = None,
    imerg_period: dict[str, str] | None = None,
    smap_period: dict[str, str] | None = None,
) -> Path:
    """Create a schema-valid synthetic Sergipe snapshot directory for regression tests."""
    sergipe_dir = root_dir / "sergipe"
    sergipe_dir.mkdir(parents=True, exist_ok=True)

    p_period = power_period or {"start": "2026-10-01", "end": "2026-10-03"}
    i_period = imerg_period or {"start": "2026-10-01", "end": "2026-10-03"}
    s_period = smap_period or {"start": "2026-10-01", "end": "2026-10-03"}

    power_payload = {
        "source": "power",
        "region": "sergipe",
        "variables": [
            {"name": "T2M", "long_name": "Air temperature at 2m", "unit": "°C"},
            {"name": "T2M_MAX", "long_name": "Max air temperature at 2m", "unit": "°C"},
            {"name": "ET0_FAO56", "long_name": "Reference evapotranspiration", "unit": "mm/day"},
            {"name": "WATER_BALANCE", "long_name": "Water balance", "unit": "mm/day"},
        ],
        "aggregation": "nearest_cell",
        "resolution": "0.5°",
        "period": p_period,
        "attribution": {
            "dataset": "POWER",
            "doi": None,
            "url": "https://power.larc.nasa.gov/",
            "notice": None,
        },
        "points": power_points if power_points is not None else {},
    }
    imerg_payload = {
        "source": "imerg",
        "region": "sergipe",
        "variables": [{"name": "precipitation", "long_name": "Daily precipitation", "unit": "mm/day"}],
        "aggregation": "cell_mean",
        "resolution": "0.1°",
        "period": i_period,
        "attribution": {
            "dataset": "IMERG",
            "doi": "10.5067/GPM/IMERGDF/DAY/07",
            "url": "https://gpm.nasa.gov/",
            "notice": None,
        },
        "points": imerg_points if imerg_points is not None else {},
    }
    smap_payload = {
        "source": "smap",
        "region": "sergipe",
        "variables": [{"name": "soil_moisture", "long_name": "Surface soil moisture", "unit": "m3/m3"}],
        "aggregation": "cell_mean",
        "resolution": "9 km",
        "period": s_period,
        "attribution": {
            "dataset": "SMAP",
            "doi": "10.5067/X2QI1IKQ9NGQ",
            "url": "https://smap.jpl.nasa.gov/",
            "notice": None,
        },
        "points": smap_points if smap_points is not None else {},
    }
    srtm_payload = {
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
        "points": srtm_points if srtm_points is not None else {},
    }

    VALIDATOR_SERIES.validate(power_payload)
    VALIDATOR_SERIES.validate(imerg_payload)
    VALIDATOR_SERIES.validate(smap_payload)
    VALIDATOR_STATIC.validate(srtm_payload)

    (sergipe_dir / "power.json").write_text(json.dumps(power_payload), encoding="utf-8")
    (sergipe_dir / "imerg.json").write_text(json.dumps(imerg_payload), encoding="utf-8")
    (sergipe_dir / "smap.json").write_text(json.dumps(smap_payload), encoding="utf-8")
    (sergipe_dir / "srtm.json").write_text(json.dumps(srtm_payload), encoding="utf-8")

    if points_features is not None:
        (sergipe_dir / "points.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": points_features}),
            encoding="utf-8",
        )

    return root_dir


def test_missing_point_in_source_does_not_leak_unrelated_point(tmp_path: Path) -> None:
    """When a source lacks the selected point, never return or relabel another point's data."""
    point_a = {
        "type": "Feature",
        "id": "A",
        "geometry": {"type": "Point", "coordinates": [-37.425, -10.685]},
        "properties": {"id": "A", "lat": -10.685, "lon": -37.425},
    }
    point_b = {
        "type": "Feature",
        "id": "B",
        "geometry": {"type": "Point", "coordinates": [-37.10, -10.20]},
        "properties": {"id": "B", "lat": -10.20, "lon": -37.10},
    }
    shared_power = {
        "A": [
            {"time": "2026-10-01", "values": {"T2M": 27.0, "T2M_MAX": 33.0, "ET0_FAO56": 5.0, "WATER_BALANCE": -5.0}},
            {"time": "2026-10-02", "values": {"T2M": 27.5, "T2M_MAX": 33.5, "ET0_FAO56": 5.0, "WATER_BALANCE": -5.0}},
            {"time": "2026-10-03", "values": {"T2M": 28.0, "T2M_MAX": 34.0, "ET0_FAO56": 5.0, "WATER_BALANCE": -5.0}},
        ]
    }
    shared_smap = {"A": [{"time": "2026-10-01", "values": {"soil_moisture": 0.14}}]}
    shared_srtm = {"A": {"elevation_m": 200.0, "slope_mean_pct": 2.5}}
    imerg_only_b = {
        "B": [
            {"time": "2026-10-01", "values": {"precipitation": 99.0}},
            {"time": "2026-10-02", "values": {"precipitation": 99.0}},
            {"time": "2026-10-03", "values": {"precipitation": 99.0}},
        ]
    }

    # Case 1: Point B has unknown coordinates (absent from points.geojson) and IMERG only has B
    case1_dir = _write_synthetic_snapshot_dir(
        tmp_path / "case_unknown_b",
        points_features=[point_a],
        power_points=shared_power,
        imerg_points=imerg_only_b,
        smap_points=shared_smap,
        srtm_points=shared_srtm,
    )
    client1 = TestClient(create_app(data_dir=case1_dir))
    res1 = client1.get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res1.status_code == 200, res1.text
    d1 = res1.json()
    assert d1["plot"]["matched_point"]["id"] == "A"
    assert all(pt["values"]["precipitation"] is None for pt in d1["rain"]["points"]["A"])
    assert d1["summary"]["rain_total_mm"] is None
    assert d1["summary"]["water_balance_mm"] is None
    assert d1["coverage"]["aligned"] is False
    assert d1["coverage"]["paired_days"] == 0

    # Case 2: Point B is known in points.geojson (> 60 km away) and IMERG only has B
    case2_dir = _write_synthetic_snapshot_dir(
        tmp_path / "case_known_distant_b",
        points_features=[point_a, point_b],
        power_points=shared_power,
        imerg_points=imerg_only_b,
        smap_points=shared_smap,
        srtm_points=shared_srtm,
    )
    client2 = TestClient(create_app(data_dir=case2_dir))
    res2 = client2.get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res2.status_code == 200, res2.text
    d2 = res2.json()
    assert d2["plot"]["matched_point"]["id"] == "A"
    assert all(pt["values"]["precipitation"] is None for pt in d2["rain"]["points"]["A"])
    assert d2["summary"]["rain_total_mm"] is None
    assert d2["summary"]["water_balance_mm"] is None


def test_unknown_coordinates_and_all_sources_missing_point_return_422(tmp_path: Path) -> None:
    """Missing coordinates, all sources lacking the point, or nearest point out of range return 422."""
    obs_b = [{"time": "2026-10-01", "values": {"precipitation": 99.0}}]
    power_b = [{"time": "2026-10-01", "values": {"T2M": 28.0, "T2M_MAX": 34.0, "ET0_FAO56": 5.0}}]
    smap_b = [{"time": "2026-10-01", "values": {"soil_moisture": 0.14}}]
    srtm_b = {"elevation_m": 150.0, "slope_mean_pct": 2.0}

    # 1. No points.geojson / pilots.geojson (unknown coordinates for all point IDs)
    no_coords_dir = _write_synthetic_snapshot_dir(
        tmp_path / "no_coords",
        points_features=None,
        power_points={"B": power_b},
        imerg_points={"B": obs_b},
        smap_points={"B": smap_b},
        srtm_points={"B": srtm_b},
    )
    res_no_coords = TestClient(create_app(data_dir=no_coords_dir)).get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res_no_coords.status_code == 422
    assert res_no_coords.json()["error"]["code"] == "no_data"

    # 2. Point A is known at requested coords, but all sources only contain unrelated point B
    point_a = {
        "type": "Feature",
        "id": "A",
        "geometry": {"type": "Point", "coordinates": [-37.425, -10.685]},
        "properties": {"id": "A", "lat": -10.685, "lon": -37.425},
    }
    all_missing_dir = _write_synthetic_snapshot_dir(
        tmp_path / "all_missing",
        points_features=[point_a],
        power_points={"B": power_b},
        imerg_points={"B": obs_b},
        smap_points={"B": smap_b},
        srtm_points={"B": srtm_b},
    )
    res_missing = TestClient(create_app(data_dir=all_missing_dir)).get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res_missing.status_code == 422
    assert res_missing.json()["error"]["code"] == "no_data"

    # 3. Nearest known point B is > 25 km away with default radius_km=5.0
    distant_b = {
        "type": "Feature",
        "id": "B",
        "geometry": {"type": "Point", "coordinates": [-37.90, -9.60]},
        "properties": {"id": "B", "lat": -9.60, "lon": -37.90},
    }
    distant_dir = _write_synthetic_snapshot_dir(
        tmp_path / "distant_point",
        points_features=[distant_b],
        power_points={"B": power_b},
        imerg_points={"B": obs_b},
        smap_points={"B": smap_b},
        srtm_points={"B": srtm_b},
    )
    res_distant = TestClient(create_app(data_dir=distant_dir)).get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res_distant.status_code == 422
    assert res_distant.json()["error"]["code"] == "no_data"


def test_missing_day_paired_alignment_and_coverage_regression(tmp_path: Path) -> None:
    """Summary aggregates only use explicitly paired dates and disclose missing days."""
    point_se = {
        "type": "Feature",
        "id": "SE001",
        "geometry": {"type": "Point", "coordinates": [-37.425, -10.685]},
        "properties": {"id": "SE001", "lat": -10.685, "lon": -37.425},
    }

    # Case 1: 2026-10-02 has 50 mm rain in IMERG but ET0_FAO56 is None in POWER -> excluded from paired scalars
    partial_dir = _write_synthetic_snapshot_dir(
        tmp_path / "partial_missing_day",
        points_features=[point_se],
        power_points={
            "SE001": [
                {"time": "2026-10-01", "values": {"T2M": 26.0, "T2M_MAX": 32.0, "ET0_FAO56": 4.0, "WATER_BALANCE": -4.0}},
                {"time": "2026-10-02", "values": {"T2M": 28.0, "T2M_MAX": 35.0, "ET0_FAO56": None, "WATER_BALANCE": None}},
                {"time": "2026-10-03", "values": {"T2M": 27.0, "T2M_MAX": 33.0, "ET0_FAO56": 4.0, "WATER_BALANCE": -4.0}},
            ]
        },
        imerg_points={
            "SE001": [
                {"time": "2026-10-01", "values": {"precipitation": 10.0}},
                {"time": "2026-10-02", "values": {"precipitation": 50.0}},
                {"time": "2026-10-03", "values": {"precipitation": 10.0}},
            ]
        },
        smap_points={
            "SE001": [
                {"time": "2026-10-01", "values": {"soil_moisture": 0.14}},
                {"time": "2026-10-03", "values": {"soil_moisture": 0.12}},
            ]
        },
        srtm_points={"SE001": {"elevation_m": 180.0, "slope_mean_pct": 3.0}},
    )
    res = TestClient(create_app(data_dir=partial_dir)).get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res.status_code == 200, res.text
    data = res.json()

    summary = data["summary"]
    VALIDATOR_DIAGNOSIS_DEF.validate(summary)
    assert summary["period_start"] == "2026-10-01"
    assert summary["period_end"] == "2026-10-03"
    assert summary["rain_total_mm"] == pytest.approx(20.0)
    assert summary["rain_daily_mean_mm"] == pytest.approx(10.0)
    assert summary["et0_daily_mean_mm"] == pytest.approx(4.0)
    assert summary["water_balance_mm"] == pytest.approx(12.0)
    assert summary["temperature_mean_c"] == pytest.approx(26.5)
    assert summary["temperature_max_c"] == pytest.approx(33.0)
    assert summary["soil_moisture_surface_m3m3"] == pytest.approx(0.13)

    cov = data["coverage"]
    assert cov["aligned"] is True
    assert cov["complete"] is False
    assert cov["expected_days"] == 3
    assert cov["paired_days"] == 2
    assert cov["missing_days"] == 1
    assert cov["missing_dates"] == ["2026-10-02"]
    assert any(s.get("notice") for s in summary["sources"])

    # Case 2: Non-overlapping non-null days within the same period -> zero paired days -> aggregates unknown
    unpaired_dir = _write_synthetic_snapshot_dir(
        tmp_path / "unpaired_same_period",
        points_features=[point_se],
        power_points={
            "SE001": [
                {"time": "2026-10-01", "values": {"T2M": None, "T2M_MAX": None, "ET0_FAO56": None}},
                {"time": "2026-10-02", "values": {"T2M": 28.0, "T2M_MAX": 34.0, "ET0_FAO56": 4.0}},
            ]
        },
        imerg_points={
            "SE001": [
                {"time": "2026-10-01", "values": {"precipitation": 10.0}},
                {"time": "2026-10-02", "values": {"precipitation": None}},
            ]
        },
        smap_points={"SE001": [{"time": "2026-10-01", "values": {"soil_moisture": 0.14}}]},
        srtm_points={"SE001": {"elevation_m": 180.0, "slope_mean_pct": 3.0}},
    )
    res_unpaired = TestClient(create_app(data_dir=unpaired_dir)).get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res_unpaired.status_code == 200, res_unpaired.text
    du = res_unpaired.json()
    assert du["coverage"]["aligned"] is False
    assert du["coverage"]["paired_days"] == 0
    assert du["summary"]["rain_total_mm"] is None
    assert du["summary"]["et0_daily_mean_mm"] is None
    assert du["summary"]["water_balance_mm"] is None
    assert du["summary"]["temperature_mean_c"] is None


def test_disjoint_source_periods_keep_aggregates_unknown(tmp_path: Path) -> None:
    """Disjoint source date ranges keep daily aggregates None instead of mixing periods."""
    point_se = {
        "type": "Feature",
        "id": "SE001",
        "geometry": {"type": "Point", "coordinates": [-37.425, -10.685]},
        "properties": {"id": "SE001", "lat": -10.685, "lon": -37.425},
    }
    disjoint_dir = _write_synthetic_snapshot_dir(
        tmp_path / "disjoint_periods",
        points_features=[point_se],
        power_period={"start": "2026-11-01", "end": "2026-11-03"},
        imerg_period={"start": "2026-10-01", "end": "2026-10-03"},
        smap_period={"start": "2026-10-15", "end": "2026-10-17"},
        power_points={
            "SE001": [
                {"time": "2026-11-01", "values": {"T2M": 28.0, "T2M_MAX": 34.0, "ET0_FAO56": 5.0}},
                {"time": "2026-11-02", "values": {"T2M": 28.5, "T2M_MAX": 34.5, "ET0_FAO56": 5.2}},
                {"time": "2026-11-03", "values": {"T2M": 29.0, "T2M_MAX": 35.0, "ET0_FAO56": 5.4}},
            ]
        },
        imerg_points={
            "SE001": [
                {"time": "2026-10-01", "values": {"precipitation": 10.0}},
                {"time": "2026-10-02", "values": {"precipitation": 12.0}},
                {"time": "2026-10-03", "values": {"precipitation": 8.0}},
            ]
        },
        smap_points={
            "SE001": [
                {"time": "2026-10-15", "values": {"soil_moisture": 0.14}},
                {"time": "2026-10-16", "values": {"soil_moisture": 0.15}},
            ]
        },
        srtm_points={"SE001": {"elevation_m": 210.0, "slope_mean_pct": 4.0}},
    )

    res = TestClient(create_app(data_dir=disjoint_dir)).get("/diagnosis?lat=-10.685&lon=-37.425")
    assert res.status_code == 200, res.text
    data = res.json()

    cov = data["coverage"]
    assert cov["aligned"] is False
    assert cov["complete"] is False
    assert cov["paired_days"] == 0
    assert cov["period_start"] is None
    assert cov["period_end"] is None

    summary = data["summary"]
    VALIDATOR_DIAGNOSIS_DEF.validate(summary)
    for field in (
        "rain_total_mm",
        "rain_daily_mean_mm",
        "et0_daily_mean_mm",
        "water_balance_mm",
        "temperature_mean_c",
        "temperature_max_c",
        "soil_moisture_surface_m3m3",
    ):
        assert summary[field] is None

    assert summary["elevation_m"] == pytest.approx(210.0)
    assert summary["slope_mean_pct"] == pytest.approx(4.0)
    assert any(s.get("notice") for s in summary["sources"])

    # Also verify build_engine_diagnosis integrates cleanly with unknown aggregates
    _, engine_diag = build_engine_diagnosis(lat=-10.685, lon=-37.425, data_dir=disjoint_dir)
    assert engine_diag.rain_total_mm is None
    assert engine_diag.water_balance_mm is None
    assert engine_diag.temperature_mean_c is None

