# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
import pandas as pd
import pytest
import requests

from src.data import power
from src.data.dates import parse_range
from src.data.errors import InputError, RemoteDataError

DATES = parse_range("2025-01-01", "2025-01-03")
PAYLOAD = {
    "header": {"fill_value": -999.0},
    "properties": {
        "parameter": {
            "T2M": {"20250101": 27.68, "20250102": -999.0, "20250103": 27.3},
            "PRECTOTCORR": {"20250101": 0.0, "20250102": 1.5, "20250103": -999.0},
        }
    },
}


class FakeResponse:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._body, self.text = status, body, text

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeSession:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def no_sleep(_seconds):
    pass


def test_build_params():
    params = power.build_params(-10.91, -37.07, DATES, ["T2M", "PRECTOTCORR"], "AG")
    assert params == {
        "parameters": "T2M,PRECTOTCORR",
        "community": "AG",
        "latitude": "-10.9100",
        "longitude": "-37.0700",
        "start": "20250101",
        "end": "20250103",
        "format": "JSON",
    }


def test_fetch_sends_request_to_point_endpoint():
    session = FakeSession(FakeResponse(body=PAYLOAD))
    power.fetch_point(-10.91, -37.07, DATES, ["T2M", "PRECTOTCORR"], session=session, sleep=no_sleep)
    url, params, timeout = session.calls[0]
    assert url == "https://power.larc.nasa.gov/api/temporal/daily/point"
    assert params["parameters"] == "T2M,PRECTOTCORR" and timeout > 0


def test_parse_response_turns_fill_value_into_nan():
    frame = power.parse_response(PAYLOAD)
    assert list(frame.columns) == ["T2M", "PRECTOTCORR"]
    assert frame.index.name == "date" and frame.index[0] == pd.Timestamp("2025-01-01")
    assert frame.loc["2025-01-01", "T2M"] == 27.68
    assert pd.isna(frame.loc["2025-01-02", "T2M"]) and pd.isna(frame.loc["2025-01-03", "PRECTOTCORR"])


def test_parse_response_without_data():
    with pytest.raises(RemoteDataError, match="no data"):
        power.parse_response({"messages": ["bad parameter"]})
    with pytest.raises(RemoteDataError, match="no parameters"):
        power.parse_response({"properties": {"parameter": {}}})


def test_parse_response_only_fill_values():
    payload = {"properties": {"parameter": {"T2M": {"20250101": -999.0}}}}
    with pytest.raises(RemoteDataError, match="only fill values"):
        power.parse_response(payload)


def test_api_error_message_is_reported():
    body = {"header": "failed", "messages": ["parameter XYZ is not valid"]}
    session = FakeSession(FakeResponse(422, body))
    with pytest.raises(RemoteDataError, match="HTTP 422.*XYZ"):
        power.fetch_point(0, 0, DATES, ["XYZ"], session=session, sleep=no_sleep)
    assert len(session.calls) == 1


def test_retries_then_succeeds():
    session = FakeSession(requests.Timeout(), FakeResponse(503), FakeResponse(body=PAYLOAD))
    frame = power.fetch_point(0, 0, DATES, ["T2M"], session=session, sleep=no_sleep)
    assert len(session.calls) == 3 and not frame.empty


def test_gives_up_after_retries():
    session = FakeSession(requests.ConnectionError(), requests.ConnectionError(), requests.ConnectionError())
    with pytest.raises(RemoteDataError, match="unavailable after 3 attempts"):
        power.fetch_point(0, 0, DATES, ["T2M"], session=session, sleep=no_sleep)


def test_invalid_json_body():
    with pytest.raises(RemoteDataError, match="not valid JSON"):
        power.fetch_point(0, 0, DATES, ["T2M"], session=FakeSession(FakeResponse(200, None)), sleep=no_sleep)


def test_parse_variables():
    assert power.parse_variables("t2m, PRECTOTCORR") == ["T2M", "PRECTOTCORR"]
    for bad in ("", " , ", "T2M;DROP"):
        with pytest.raises(InputError):
            power.parse_variables(bad)


def test_cache_is_reused_only_when_complete(tmp_path):
    complete = {"properties": {"parameter": {"T2M": {"20250101": 1.0, "20250102": 2.0, "20250103": 3.0}}}}
    first = FakeSession(FakeResponse(body=complete))
    power.fetch_point(0, 0, DATES, ["T2M"], cache_dir=tmp_path, session=first, sleep=no_sleep)
    second = FakeSession()
    again = power.fetch_point(0, 0, DATES, ["T2M"], cache_dir=tmp_path, session=second, sleep=no_sleep)
    assert second.calls == [] and again["T2M"].iloc[-1] == 3.0

    refreshed = FakeSession(FakeResponse(body=complete))
    power.fetch_point(0, 0, DATES, ["T2M"], cache_dir=tmp_path, refresh=True, session=refreshed, sleep=no_sleep)
    assert len(refreshed.calls) == 1


def test_recent_days_with_fill_values_are_not_cached(tmp_path):
    session = FakeSession(FakeResponse(body=PAYLOAD))
    power.fetch_point(0, 0, DATES, ["T2M", "PRECTOTCORR"], cache_dir=tmp_path, session=session, sleep=no_sleep)
    assert list(tmp_path.glob("*.json")) == []


@pytest.mark.network
def test_real_power_api_aracaju():
    dates = parse_range("2025-01-01", "2025-01-10")
    frame = power.fetch_point(-10.91, -37.07, dates, ["T2M", "PRECTOTCORR"])
    assert len(frame) == 10 and frame["T2M"].between(15, 40).all()
    assert frame.index.name == "date"
