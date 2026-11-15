# AI-assisted: generated with Antigravity, reviewed by dudxyz
"""Tests for the Open-Meteo weather forecast connector (no network)."""

import json

import pandas as pd
import pytest
import requests

from src.data import cli, open_meteo
from src.data.errors import InputError, RemoteDataError

PAYLOAD = {
    "latitude": -10.685,
    "longitude": -37.425,
    "daily": {
        "time": ["2026-11-14", "2026-11-15"],
        "temperature_2m_max": [33.3, 32.8],
        "temperature_2m_min": [23.5, 22.9],
        "precipitation_sum": [0.1, 4.2],
        "et0_fao_evapotranspiration": [5.62, 4.95],
    },
}


class _FakeResponse:
    def __init__(self, status=200, body=None, text=""):
        self.status_code = status
        self._body = body
        self.text = text

    def json(self):
        if self._body is None:
            raise ValueError("invalid json")
        return self._body


class _FakeSession:
    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _no_sleep(_seconds):
    pass


def test_build_params_validates_inputs():
    params = open_meteo.build_params(-10.685, -37.425, ["temperature_2m_max", "precipitation_sum"], 15, "ecmwf_ifs")
    assert params["forecast_days"] == 15 and params["models"] == "ecmwf_ifs"
    with pytest.raises(InputError, match="forecast_days"):
        open_meteo.build_params(-10.685, -37.425, ["temperature_2m_max"], 20, "best_match")
    with pytest.raises(InputError, match="unsupported Open-Meteo model"):
        open_meteo.build_params(-10.685, -37.425, ["temperature_2m_max"], 15, "unknown_model")


def test_parse_response_builds_dated_frame():
    frame = open_meteo.parse_response(PAYLOAD)
    assert frame.index.name == "date"
    assert len(frame) == 2 and frame.loc["2026-11-15", "precipitation_sum"] == 4.2
    with pytest.raises(RemoteDataError, match="returned an error"):
        open_meteo.parse_response({"error": True, "reason": "bad coordinate"})


def test_fetch_forecast_retries_and_caches(tmp_path):
    session = _FakeSession(
        requests.Timeout("slow"),
        _FakeResponse(503, text="busy"),
        _FakeResponse(200, body=PAYLOAD),
    )
    frame = open_meteo.fetch_forecast(
        -10.685,
        -37.425,
        variables=["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "et0_fao_evapotranspiration"],
        forecast_days=15,
        model="best_match",
        cache_dir=tmp_path,
        session=session,
        sleep=_no_sleep,
    )
    assert len(session.calls) == 3 and len(frame) == 2

    # Second call reads fresh cache without hitting session
    empty_session = _FakeSession()
    cached = open_meteo.fetch_forecast(
        -10.685,
        -37.425,
        variables=["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "et0_fao_evapotranspiration"],
        forecast_days=15,
        model="best_match",
        cache_dir=tmp_path,
        session=empty_session,
        sleep=_no_sleep,
    )
    assert cached.equals(frame) and len(empty_session.calls) == 0


def test_to_api_response_includes_non_nasa_attribution():
    frame = open_meteo.parse_response(PAYLOAD)
    envelope = open_meteo.to_api_response(frame, -10.685, -37.425, model="ecmwf_ifs")
    assert envelope["source"] == "open-meteo"
    assert envelope["nasa"] is False
    assert "CC BY 4.0" in envelope["attribution"]
    assert len(envelope["series"]) == 2
    assert envelope["series"][0]["values"]["et0_fao_evapotranspiration"] == 5.62


def test_cli_open_meteo_writes_json_without_start_end(tmp_path, monkeypatch, capsys):
    frame = open_meteo.parse_response(PAYLOAD)
    monkeypatch.setattr(open_meteo, "fetch_forecast", lambda *a, **kw: frame)
    out = tmp_path / "forecast.json"
    code = cli.main(["open-meteo", "--point", "-10.685,-37.425", "--out", str(out)])
    assert code == 0
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["source"] == "open-meteo" and len(saved["series"]) == 2
    assert "Open-Meteo (best_match)" in capsys.readouterr().out


def test_historical_sources_still_require_start_end(capsys):
    code = cli.main(["power", "--variable", "T2M"])
    assert code == 2 and "--start and --end are required" in capsys.readouterr().err
