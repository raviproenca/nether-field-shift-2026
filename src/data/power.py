# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""NASA POWER daily point API (public, no login). Bounding boxes use their center point."""

import hashlib
import json
import re
import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import requests

from .dates import DateRange
from .errors import InputError, RemoteDataError

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
FILL_VALUE = -999.0
DEFAULT_COMMUNITY = "AG"
RETRY_STATUS = {429, 500, 502, 503, 504}
PARAMETER_PATTERN = re.compile(r"[A-Z0-9_]+")


def parse_variables(text: str) -> list[str]:
    names = [name.strip().upper() for name in text.split(",") if name.strip()]
    if not names:
        raise InputError("pass at least one POWER parameter, e.g. --variable T2M,PRECTOTCORR")
    bad = [name for name in names if not PARAMETER_PATTERN.fullmatch(name)]
    if bad:
        raise InputError(f"invalid POWER parameter name(s): {', '.join(bad)}")
    return names


def build_params(lat: float, lon: float, dates: DateRange, variables: list[str], community: str) -> dict[str, str]:
    return {
        "parameters": ",".join(variables),
        "community": community,
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start": dates.power_start,
        "end": dates.power_end,
        "format": "JSON",
    }


def _describe_error(response: requests.Response) -> str:
    try:
        body = response.json()
        detail = "; ".join(body.get("messages") or []) or body.get("header", "")
    except ValueError:
        detail = response.text[:200]
    return f"POWER API rejected the request (HTTP {response.status_code}): {detail}"


def _request_json(
    session: requests.Session, params: dict[str, str], timeout: float, retries: int, sleep: Callable[[float], None]
) -> dict:
    reason = ""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(POWER_URL, params=params, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as exc:
            reason = f"network error: {exc.__class__.__name__}"
        else:
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    raise RemoteDataError("POWER API returned a response that is not valid JSON") from None
            if response.status_code not in RETRY_STATUS:
                raise RemoteDataError(_describe_error(response))
            reason = f"HTTP {response.status_code}"
        if attempt < retries:
            sleep(2.0 * attempt)
    raise RemoteDataError(f"POWER API unavailable after {retries} attempts ({reason}). Try again later.")


def parse_response(payload: dict) -> pd.DataFrame:
    """Turn a POWER JSON payload into a DataFrame indexed by date; the fill value becomes NaN."""
    try:
        parameters = payload["properties"]["parameter"]
    except (KeyError, TypeError):
        messages = payload.get("messages") if isinstance(payload, dict) else None
        raise RemoteDataError(f"POWER API response has no data: {messages or 'unexpected format'}") from None
    if not parameters:
        raise RemoteDataError("POWER API returned no parameters for this request")
    fill = payload.get("header", {}).get("fill_value", FILL_VALUE)
    frame = pd.DataFrame(parameters).astype(float).mask(lambda df: df == fill)
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d")
    frame.index.name = "date"
    if frame.dropna(how="all").empty:
        raise RemoteDataError("POWER API returned only fill values (no data for this place and period)")
    return frame.sort_index()


def _cache_path(cache_dir: Path, params: dict[str, str]) -> Path:
    digest = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:10]
    return (
        cache_dir / f"point_{params['latitude']}_{params['longitude']}_{params['start']}_{params['end']}_{digest}.json"
    )


def fetch_point(
    lat: float,
    lon: float,
    dates: DateRange,
    variables: list[str],
    community: str = DEFAULT_COMMUNITY,
    cache_dir: Path | None = None,
    refresh: bool = False,
    session: requests.Session | None = None,
    timeout: float = 60.0,
    retries: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> pd.DataFrame:
    """Daily series for one point. The raw JSON is cached in cache_dir (ignored when refresh=True).
    Responses whose last day is still a fill value are not cached, so recent days refresh later."""
    params = build_params(lat, lon, dates, variables, community)
    cached = _cache_path(cache_dir, params) if cache_dir else None
    if cached and cached.is_file() and not refresh:
        return parse_response(json.loads(cached.read_text()))
    payload = _request_json(session or requests.Session(), params, timeout, retries, sleep)
    frame = parse_response(payload)
    if cached and not frame.iloc[-1].isna().any():
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(payload))
    return frame
