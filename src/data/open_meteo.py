# AI-assisted: generated with Antigravity, reviewed by dudxyz & Lucas Feitosa
"""Open-Meteo weather & FAO-56 ET0 forecast connector (up to 15 days, free CC BY 4.0, no key)."""

import hashlib
import json
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from .errors import InputError, RemoteDataError

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_MODEL = "best_match"
SUPPORTED_MODELS = ("best_match", "ecmwf_ifs", "ecmwf_ifs025", "gfs_seamless")
DEFAULT_FORECAST_DAYS = 15
MAX_FORECAST_DAYS = 16
CACHE_TTL_SECONDS = 6 * 3600
RETRY_STATUS = {429, 500, 502, 503, 504}
VARIABLE_PATTERN = re.compile(r"[a-z0-9_]+")
ATTRIBUTION = "Open-Meteo Weather Forecast API (ECMWF IFS / NOAA GFS), CC BY 4.0 (https://open-meteo.com/)"

VARIABLE_META: dict[str, tuple[str, str]] = {
    "temperature_2m_max": ("Maximum air temperature at 2 m", "°C"),
    "temperature_2m_min": ("Minimum air temperature at 2 m", "°C"),
    "precipitation_sum": ("Daily precipitation sum", "mm/day"),
    "precipitation_probability_max": ("Maximum daily precipitation probability", "%"),
    "et0_fao_evapotranspiration": ("FAO-56 reference evapotranspiration (ET0)", "mm/day"),
    "shortwave_radiation_sum": ("Daily shortwave solar radiation sum", "MJ/m²/day"),
    "wind_speed_10m_max": ("Maximum wind speed at 10 m", "km/h"),
}
DEFAULT_VARIABLES = tuple(VARIABLE_META.keys())


def parse_variables(text: str | None) -> list[str]:
    """Parse comma-separated Open-Meteo daily variables (defaults to agroclimatic + FAO-56 ET0 set)."""
    if not text or not text.strip():
        return list(DEFAULT_VARIABLES)
    names = [name.strip().lower() for name in text.split(",") if name.strip()]
    if not names:
        raise InputError("pass at least one Open-Meteo daily variable")
    bad = [name for name in names if not VARIABLE_PATTERN.fullmatch(name)]
    if bad:
        raise InputError(f"invalid Open-Meteo variable name(s): {', '.join(bad)}")
    return names


def build_params(
    lat: float,
    lon: float,
    variables: list[str],
    forecast_days: int = DEFAULT_FORECAST_DAYS,
    model: str = DEFAULT_MODEL,
    timezone: str = "UTC",
) -> dict[str, str | int]:
    """Validate inputs and construct Open-Meteo forecast query parameters."""
    if not (-89.0 <= lat <= 89.0):
        raise InputError(f"latitude must be within +-89, got {lat}")
    if not (-180.0 <= lon <= 180.0):
        raise InputError(f"longitude must be within +-180, got {lon}")
    if not 1 <= forecast_days <= MAX_FORECAST_DAYS:
        raise InputError(f"forecast_days must be between 1 and {MAX_FORECAST_DAYS}, got {forecast_days}")
    model_key = model.strip().lower()
    if model_key not in SUPPORTED_MODELS:
        raise InputError(f"unsupported Open-Meteo model '{model}': choose from {', '.join(SUPPORTED_MODELS)}")
    return {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "daily": ",".join(variables),
        "forecast_days": forecast_days,
        "models": model_key,
        "timezone": timezone,
    }


def _describe_error(response: requests.Response) -> str:
    detail = ""
    try:
        body = response.json()
        if isinstance(body, dict):
            detail = str(body.get("reason") or body.get("error") or "")
    except ValueError:
        pass
    detail = detail or str(response.text or "")[:200]
    return f"Open-Meteo API rejected the request (HTTP {response.status_code}): {detail}"


def _request_json(
    session: requests.Session,
    params: dict[str, str | int],
    timeout: float,
    retries: int,
    sleep: Callable[[float], None],
) -> dict:
    reason = ""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(FORECAST_URL, params=params, timeout=timeout)
        except requests.RequestException as exc:
            reason = f"network error: {exc.__class__.__name__}"
        else:
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    raise RemoteDataError("Open-Meteo API returned invalid JSON") from None
            if response.status_code not in RETRY_STATUS:
                raise RemoteDataError(_describe_error(response))
            reason = f"HTTP {response.status_code}"
        if attempt < retries:
            sleep(2.0 * attempt)
    raise RemoteDataError(f"Open-Meteo API unavailable after {retries} attempts ({reason}). Try again later.")


def parse_response(payload: dict) -> pd.DataFrame:
    """Turn an Open-Meteo daily forecast payload into a DataFrame indexed by date."""
    if not isinstance(payload, dict) or payload.get("error"):
        reason = payload.get("reason") if isinstance(payload, dict) else "unexpected format"
        raise RemoteDataError(f"Open-Meteo API returned an error: {reason or 'unexpected format'}")
    daily = payload.get("daily")
    if not isinstance(daily, dict) or "time" not in daily or not daily["time"]:
        raise RemoteDataError("Open-Meteo API response has no daily forecast data")
    dates = pd.to_datetime(daily["time"], format="%Y-%m-%d")
    columns = {key: values for key, values in daily.items() if key != "time"}
    if not columns:
        raise RemoteDataError("Open-Meteo API returned no forecast variables")
    frame = pd.DataFrame(columns, index=dates).astype(float)
    frame.index.name = "date"
    if frame.dropna(how="all").empty:
        raise RemoteDataError("Open-Meteo API returned only null values for this location")
    return frame.sort_index()


def _norm_coord_str(val: str | int | float) -> str:
    r = round(float(val), 2)
    return "0.00" if r == 0.0 else f"{r:.2f}"


def _normalize_params_for_cache(params: dict[str, str | int]) -> dict[str, str | int]:
    normalized = dict(params)
    if "latitude" in normalized:
        normalized["latitude"] = _norm_coord_str(normalized["latitude"])
    if "longitude" in normalized:
        normalized["longitude"] = _norm_coord_str(normalized["longitude"])
    return normalized


def cache_path(cache_dir: Path, params: dict[str, str | int]) -> Path:
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    norm_params = _normalize_params_for_cache(params)
    digest = hashlib.sha256(json.dumps({**norm_params, "day": stamp}, sort_keys=True).encode()).hexdigest()[:16]
    return cache_dir / f"{digest}.json"


def stale_cache_path(cache_dir: Path, params: dict[str, str | int]) -> Path:
    norm_params = _normalize_params_for_cache(params)
    digest = hashlib.sha256(json.dumps(norm_params, sort_keys=True).encode()).hexdigest()[:16]
    return cache_dir / f"{digest}.stale.json"


def _read_cache_file(path: Path | None) -> dict | None:
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _fresh_cache(path: Path, ttl_seconds: int) -> dict | None:
    if not path.is_file():
        return None
    if (time.time() - path.stat().st_mtime) > ttl_seconds:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def fetch_forecast(
    lat: float,
    lon: float,
    variables: list[str] | None = None,
    forecast_days: int = DEFAULT_FORECAST_DAYS,
    model: str = DEFAULT_MODEL,
    timezone: str = "UTC",
    cache_dir: Path | None = None,
    refresh: bool = False,
    ttl_seconds: int = CACHE_TTL_SECONDS,
    timeout: float = 30.0,
    retries: int = 3,
    session: requests.Session | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> pd.DataFrame:
    """Fetch a 1..16-day forecast table (date index, metric columns) with optional file caching."""
    selected = variables if variables is not None else list(DEFAULT_VARIABLES)
    params = build_params(lat, lon, selected, forecast_days=forecast_days, model=model, timezone=timezone)
    target = cache_path(cache_dir, params) if cache_dir else None
    stale_target = stale_cache_path(cache_dir, params) if cache_dir else None
    if target and not refresh:
        cached = _fresh_cache(target, ttl_seconds)
        if cached is not None:
            return parse_response(cached)
    http = session or requests.Session()
    try:
        payload = _request_json(http, params, timeout=timeout, retries=retries, sleep=sleep)
    except RemoteDataError:
        if cache_dir:
            stale_payload = _read_cache_file(target) or _read_cache_file(stale_target)
            if stale_payload is not None:
                return parse_response(stale_payload)
        raise
    frame = parse_response(payload)
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload_str = json.dumps(payload)
        target.write_text(payload_str, encoding="utf-8")
        if stale_target:
            stale_target.write_text(payload_str, encoding="utf-8")
    return frame


def to_api_response(
    frame: pd.DataFrame,
    lat: float,
    lon: float,
    model: str = DEFAULT_MODEL,
    cached: bool = False,
) -> dict:
    """Format a forecast DataFrame using the same response envelope conventions as apps/api/openapi.yaml."""
    variables = [
        {
            "name": col,
            "long_name": VARIABLE_META.get(col, (col, "unknown"))[0],
            "unit": VARIABLE_META.get(col, (col, "unknown"))[1],
        }
        for col in frame.columns
    ]
    series = []
    for ts, row in frame.iterrows():
        values = {col: (None if pd.isna(row[col]) else round(float(row[col]), 3)) for col in frame.columns}
        series.append({"time": ts.strftime("%Y-%m-%d"), "values": values})
    return {
        "source": "open-meteo",
        "model": model,
        "nasa": False,
        "notice": "Weather forecast from Open-Meteo (ECMWF/GFS), not NASA satellite observations.",
        "attribution": ATTRIBUTION,
        "variables": variables,
        "point": {"lat": round(lat, 4), "lon": round(lon, 4)},
        "period": {
            "start": frame.index.min().strftime("%Y-%m-%d"),
            "end": frame.index.max().strftime("%Y-%m-%d"),
        },
        "cached": cached,
        "series": series,
    }
