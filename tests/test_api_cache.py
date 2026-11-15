# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Unit and integration tests for API caching, 0.01° spatial rounding, and pilot pre-warming (AD-7, AD-9)."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
import pandas as pd
import pytest
from referencing import Registry, Resource
import requests

from apps.api.cache import (
    DEFAULT_API_CACHE_DIR,
    PILOT_SITES,
    build_cache_key,
    coord_cache_key,
    coord_cache_key_variants,
    coord_key,
    format_coord_001,
    load_pilot_sites,
    prewarm_pilots,
    read_diagnosis_cache,
    read_recommendation_cache,
    resolve_api_cache_dir,
    round_coord,
    write_diagnosis_cache,
    write_recommendation_cache,
)
from apps.api.diagnosis import build_engine_diagnosis
from apps.api.errors import APIError
from apps.api.main import create_app
from src.data import open_meteo
from src.data.errors import RemoteDataError
from src.data.paths import ROOT
from src.engine.model import Crop, Priority

SCHEMAS_DIR = ROOT / "docs" / "data-format"
REC_SCHEMA = json.loads((SCHEMAS_DIR / "recommendation.schema.json").read_text(encoding="utf-8"))
REGISTRY = Registry().with_resources(
    (path.name, Resource.from_contents(json.loads(path.read_text(encoding="utf-8"))))
    for path in SCHEMAS_DIR.glob("*.schema.json")
)


def _make_15_day_mock_payload() -> dict[str, Any]:
    """Create a raw 15-day Open-Meteo payload for mocking."""
    dates = [f"2026-11-{15+i:02d}" for i in range(15)]
    return {
        "latitude": -10.22,
        "longitude": -37.42,
        "generationtime_ms": 0.5,
        "utc_offset_seconds": 0,
        "timezone": "UTC",
        "timezone_abbreviation": "UTC",
        "elevation": 200.0,
        "daily_units": {
            "time": "iso8601",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "precipitation_sum": "mm",
            "precipitation_probability_max": "%",
            "et0_fao_evapotranspiration": "mm",
            "shortwave_radiation_sum": "MJ/m²",
            "wind_speed_10m_max": "km/h",
        },
        "daily": {
            "time": dates,
            "temperature_2m_max": [30.0 + i * 0.2 for i in range(15)],
            "temperature_2m_min": [20.0 + i * 0.1 for i in range(15)],
            "precipitation_sum": [1.5 for _ in range(15)],
            "precipitation_probability_max": [40 for _ in range(15)],
            "et0_fao_evapotranspiration": [3.5 for _ in range(15)],
            "shortwave_radiation_sum": [18.0 for _ in range(15)],
            "wind_speed_10m_max": [12.0 for _ in range(15)],
        },
    }


# ---------------------------------------------------------------------------
# Test 1: Coordinate Rounding & Key Generation (AD-7)
# ---------------------------------------------------------------------------


def test_coordinate_rounding_and_cache_key_generation() -> None:
    """Validate 0.01° spatial rounding, -0.0 normalization, and canonical AD-7 cache keys."""
    # -0.0 and zero normalization
    assert round_coord(0.0) == 0.0
    assert round_coord(-0.0) == 0.0
    assert round_coord(-0.0001) == 0.0
    assert format_coord_001(-0.0001) == "0.00"
    assert format_coord_001(0.0) == "0.00"

    # Standard rounding
    assert round_coord(10.1234) == 10.12
    assert format_coord_001(10.1234) == "10.12"

    # Pilot sites coordinates
    assert format_coord_001(-10.218) == "-10.22"
    assert format_coord_001(-37.420) == "-37.42"
    assert coord_cache_key(-10.218, -37.420) == "-10.22,-37.42"
    assert coord_key(-10.218, -37.420) == "-10.22,-37.42"

    # Itabaiana variants cross-combination
    ita_variants = coord_cache_key_variants(-10.685, -37.425)
    assert ita_variants[0] == coord_cache_key(-10.685, -37.425)
    assert "-10.68,-37.42" in ita_variants or "-10.69,-37.43" in ita_variants
    assert len(set(ita_variants)) == len(ita_variants)

    # Canonical build_cache_key
    assert build_cache_key("diagnosis", -10.218, -37.420) == "diagnosis:-10.22,-37.42"
    assert (
        build_cache_key("recommendation", -10.218, -37.420, "2026-01-01..2026-11-15")
        == "recommendation:-10.22,-37.42:2026-01-01..2026-11-15"
    )
    assert (
        build_cache_key("forecast", -10.218, -37.420, "15d", "best_match")
        == "forecast:-10.22,-37.42:15d:best_match"
    )


# ---------------------------------------------------------------------------
# Test 2: Same 0.01° Grid Cell Coordinates Share Cache Files
# ---------------------------------------------------------------------------


def test_same_cell_coordinates_share_cache_keys_and_files(tmp_path: Path) -> None:
    """Coordinates inside the same 0.01° cell map to identical cache keys and share disk files."""
    pt1 = (-10.218, -37.420)
    pt2 = (-10.222, -37.418)

    # Verify identical canonical keys
    ck1 = coord_cache_key(pt1[0], pt1[1])
    ck2 = coord_cache_key(pt2[0], pt2[1])
    assert ck1 == ck2 == "-10.22,-37.42"

    # API cache file sharing
    api_cache_dir = tmp_path / "api_cache"
    fake_response = {
        "plot": {"lat": pt1[0], "lon": pt1[1], "radius_km": 5.0},
        "summary": {"period_start": "2026-01-01", "period_end": "2026-11-15"},
    }
    written_path = write_diagnosis_cache(api_cache_dir, pt1[0], pt1[1], fake_response)
    assert written_path.is_file()

    read_back = read_diagnosis_cache(api_cache_dir, pt2[0], pt2[1])
    assert read_back is not None
    assert read_back["summary"]["period_start"] == "2026-01-01"

    # Open-Meteo cache file sharing
    fdir = tmp_path / "forecast_cache"
    vars_list = ["temperature_2m_max"]
    p1 = open_meteo.build_params(pt1[0], pt1[1], vars_list)
    p2 = open_meteo.build_params(pt2[0], pt2[1], vars_list)

    assert open_meteo.cache_path(fdir, p1) == open_meteo.cache_path(fdir, p2)
    assert open_meteo.stale_cache_path(fdir, p1) == open_meteo.stale_cache_path(fdir, p2)


# ---------------------------------------------------------------------------
# Test 3: Pre-warm Pilots, Schema Validation, and Multi-language (AD-9)
# ---------------------------------------------------------------------------


def test_prewarm_pilots_schema_validation_and_multi_lang(tmp_path: Path) -> None:
    """Pre-warming generates cache files for all 12 crop/priority combinations conforming to schema."""
    api_cache_dir = tmp_path / "api_cache"
    summary = prewarm_pilots(cache_dir=api_cache_dir, force=True)

    assert summary["prewarmed"] is True
    assert len(summary["pilots"]) >= 2
    assert len(summary["coord_keys"]) >= 2

    validator = Draft202012Validator(REC_SCHEMA, registry=REGISTRY)

    for pilot in PILOT_SITES:
        lat = pilot["lat"]
        lon = pilot["lon"]
        ck = coord_cache_key(lat, lon)
        stem = ck.replace(",", "_")

        diag_file = api_cache_dir / f"diagnosis_{stem}.json"
        rec_file = api_cache_dir / f"recommendation_{stem}.json"
        assert diag_file.is_file(), f"Missing diagnosis file: {diag_file}"
        assert rec_file.is_file(), f"Missing recommendation file: {rec_file}"

        rec_data = json.loads(rec_file.read_text(encoding="utf-8"))
        entries = rec_data.get("entries", {})
        assert len(entries) == 12, f"Expected 12 combinations, found {len(entries)}"

        for crop in Crop:
            for priority in Priority:
                entry_key = f"{crop.value}:{priority.value}::"
                assert entry_key in entries, f"Missing entry key {entry_key}"
                entry = entries[entry_key]
                rec_dict = entry["recommendation"]
                explanations = entry["explanations"]

                # Schema validation (AD-9: language-neutral structure)
                validator.validate(rec_dict)
                assert len(rec_dict["strategies"]) >= 3

                # Multi-language explanations
                assert "en" in explanations and explanations["en"].strip()
                assert "pt-BR" in explanations and explanations["pt-BR"].strip()

    # Second pass without force should mark as cached
    cached_summary = prewarm_pilots(cache_dir=api_cache_dir, force=False)
    assert cached_summary["prewarmed"] is True
    for p in cached_summary["pilots"]:
        assert p.get("status") == "cached"


# ---------------------------------------------------------------------------
# Test 4: Offline Resilience for Recommendation and Diagnosis (AD-7)
# ---------------------------------------------------------------------------


def test_offline_resilience_recommendation_and_diagnosis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pre-warmed pilots serve recommendations and diagnosis even with missing snapshots and network offline."""
    api_cache_dir = tmp_path / "api_cache"
    prewarm_pilots(cache_dir=api_cache_dir, force=True)

    offline_data_dir = tmp_path / "offline_snapshots"
    app = create_app(
        data_dir=offline_data_dir,
        api_cache_dir=api_cache_dir,
        prewarm=False,
    )

    # Simulate upstream network failure
    def offline_fetch(*args: Any, **kwargs: Any) -> Any:
        raise RemoteDataError("Network connection offline")

    monkeypatch.setattr(open_meteo, "fetch_forecast", offline_fetch)

    client = TestClient(app)

    # Test Itabaiana pilot (-10.685, -37.425) in English and Portuguese
    body_ita_en = {
        "lat": -10.685,
        "lon": -37.425,
        "crop": "maize",
        "priority": "water",
        "lang": "en",
    }
    resp = client.post("/recommendation", json=body_ita_en)
    assert resp.status_code == 200
    data = resp.json()
    assert data["lang"] == "en"
    assert data["recommendation"]["crop"] == "maize"
    assert len(data["recommendation"]["strategies"]) >= 3
    assert data["explanation"].strip()

    body_ita_pt = {**body_ita_en, "lang": "pt-BR"}
    resp_pt = client.post("/recommendation", json=body_ita_pt)
    assert resp_pt.status_code == 200
    assert resp_pt.json()["lang"] == "pt-BR"

    # Test coordinate variants for Itabaiana (-10.68, -37.42 and -10.69, -37.43)
    for v_lat, v_lon in [(-10.68, -37.42), (-10.69, -37.43)]:
        body_var = {**body_ita_en, "lat": v_lat, "lon": v_lon}
        resp_var = client.post("/recommendation", json=body_var)
        assert resp_var.status_code == 200

    # Test Nossa Senhora da Glória pilot (-10.218, -37.42)
    body_gloria = {
        "lat": -10.218,
        "lon": -37.42,
        "crop": "cassava",
        "priority": "income",
        "lang": "pt-BR",
    }
    resp_gloria = client.post("/recommendation", json=body_gloria)
    assert resp_gloria.status_code == 200

    # Test GET /diagnosis offline for both pilots
    resp_diag_ita = client.get("/diagnosis?lat=-10.685&lon=-37.425")
    assert resp_diag_ita.status_code == 200
    diag_ita = resp_diag_ita.json()
    assert diag_ita["plot"]["region"] == "sergipe"
    assert len(diag_ita["summary"]["sources"]) > 0

    resp_diag_glo = client.get("/diagnosis?lat=-10.218&lon=-37.42")
    assert resp_diag_glo.status_code == 200

    # Test recommendation fallback when build_engine_diagnosis raises 503
    def failing_engine_diagnosis(*args: Any, **kwargs: Any) -> Any:
        raise APIError(status_code=503, code="server_not_configured", message="DB down")

    monkeypatch.setattr("apps.api.recommendation.build_engine_diagnosis", failing_engine_diagnosis)
    resp_after_503 = client.post("/recommendation", json=body_ita_en)
    assert resp_after_503.status_code == 200


# ---------------------------------------------------------------------------
# Test 5: Offline Resilience for GET /forecast
# ---------------------------------------------------------------------------


def test_offline_resilience_forecast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /forecast serves cached or stale weather data when upstream Open-Meteo times out."""
    fdir = tmp_path / "forecast_cache"
    app = create_app(forecast_cache_dir=fdir, prewarm=False)
    client = TestClient(app)

    # 1. Populate cache using mock session
    mock_payload = _make_15_day_mock_payload()
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_session = MagicMock(spec=requests.Session)
    mock_session.get.return_value = mock_resp

    monkeypatch.setattr(requests, "Session", lambda: mock_session)

    resp_live = client.get("/forecast?lat=-10.218&lon=-37.42")
    assert resp_live.status_code == 200
    assert resp_live.json()["cached"] is False

    # 2. Make upstream fail with Timeout
    def timeout_request(*args: Any, **kwargs: Any) -> Any:
        raise RemoteDataError("Open-Meteo connection timed out")

    monkeypatch.setattr(open_meteo, "_request_json", timeout_request)

    # Offline query on same coordinates returns cached=True
    resp_offline = client.get("/forecast?lat=-10.218&lon=-37.42")
    assert resp_offline.status_code == 200
    assert resp_offline.json()["cached"] is True

    # Offline query on different point in same 0.01° cell (-10.222, -37.418) also returns cached=True
    resp_same_cell = client.get("/forecast?lat=-10.222&lon=-37.418")
    assert resp_same_cell.status_code == 200
    assert resp_same_cell.json()["cached"] is True


# ---------------------------------------------------------------------------
# Test 6: Error Boundaries Preserved (400, 422, 503)
# ---------------------------------------------------------------------------


def test_error_boundaries_preserved_offline(tmp_path: Path) -> None:
    """Uncached locations fail with 503, outside bounds with 422, invalid parameters with 400."""
    api_cache_dir = tmp_path / "api_cache"
    prewarm_pilots(cache_dir=api_cache_dir, force=True)

    offline_data_dir = tmp_path / "offline_snapshots"
    app = create_app(
        data_dir=offline_data_dir,
        api_cache_dir=api_cache_dir,
        prewarm=False,
    )
    client = TestClient(app)

    # 1. Uncached non-pilot coordinates inside Sergipe return 503 when snapshots are offline
    resp_uncached_diag = client.get("/diagnosis?lat=-10.50&lon=-37.10")
    assert resp_uncached_diag.status_code == 503
    assert resp_uncached_diag.json()["error"]["code"] == "server_not_configured"

    body_uncached_rec = {
        "lat": -10.50,
        "lon": -37.10,
        "crop": "maize",
        "priority": "water",
    }
    resp_uncached_rec = client.post("/recommendation", json=body_uncached_rec)
    assert resp_uncached_rec.status_code == 503

    # 2. Coordinates outside Sergipe return 422 no_data
    resp_outside_diag = client.get("/diagnosis?lat=-23.50&lon=-46.60")
    assert resp_outside_diag.status_code == 422
    assert resp_outside_diag.json()["error"]["code"] == "no_data"

    body_outside_rec = {
        "lat": -23.50,
        "lon": -46.60,
        "crop": "maize",
        "priority": "water",
    }
    resp_outside_rec = client.post("/recommendation", json=body_outside_rec)
    assert resp_outside_rec.status_code == 422
    assert resp_outside_rec.json()["error"]["code"] == "no_data"

    # 3. Invalid parameters return 400 invalid_parameter
    resp_inv_diag = client.get("/diagnosis?lat=invalid&lon=-37.42")
    assert resp_inv_diag.status_code == 400
    assert resp_inv_diag.json()["error"]["code"] == "invalid_parameter"

    body_inv_rec = {
        "lat": -10.685,
        "lon": -37.425,
        "crop": "unsupported_crop",
        "priority": "water",
    }
    resp_inv_rec = client.post("/recommendation", json=body_inv_rec)
    assert resp_inv_rec.status_code == 400
    assert resp_inv_rec.json()["error"]["code"] == "invalid_parameter"


# ---------------------------------------------------------------------------
# Test 7: CLI Execution
# ---------------------------------------------------------------------------


def test_cache_cli_execution(tmp_path: Path) -> None:
    """Running python -m apps.api.cache --cache-dir <dir> exits with 0 and writes pilot cache JSON."""
    cli_cache_dir = tmp_path / "cli_cache"
    cmd = [
        sys.executable,
        "-m",
        "apps.api.cache",
        "--cache-dir",
        str(cli_cache_dir),
        "--force",
    ]
    res = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, f"CLI exited with {res.returncode}. stderr: {res.stderr}"
    data = json.loads(res.stdout)
    assert data.get("prewarmed") is True
    assert len(data.get("pilots", [])) >= 2
    assert any(cli_cache_dir.glob("recommendation_*.json"))
    assert any(cli_cache_dir.glob("diagnosis_*.json"))


def test_prewarm_pilots_read_only_filesystem_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Pre-warming gracefully returns {} on a read-only filesystem without raising OSError."""
    orig_mkdir = Path.mkdir

    def fake_mkdir(self: Path, *args: Any, **kwargs: Any) -> None:
        if "ro_cache" in str(self):
            raise OSError(30, "Read-only file system")
        return orig_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)
    res = prewarm_pilots(cache_dir=tmp_path / "ro_cache")
    assert res == {}
