# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Forecast service and response models for the Open-Meteo weather endpoint."""

from __future__ import annotations

import functools
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import requests
from pydantic import BaseModel, ConfigDict

from src.data import open_meteo
from src.data.errors import InputError, RemoteDataError
from src.data.paths import CACHE_DIR, ROOT
from src.data.regions import PRESETS
from src.engine.model import Projection, SourceAttribution
from .errors import APIError

OPEN_METEO_SOURCE_ID = "open-meteo"
OPEN_METEO_DATASET = "Open-Meteo Weather Forecast API (ECMWF IFS / NOAA GFS), CC BY 4.0"
OPEN_METEO_URL = "https://open-meteo.com/"
OPEN_METEO_NOTICE = (
    "Forecast from Open-Meteo (ECMWF IFS / NOAA GFS), not NASA satellite observations; "
    "free for non-commercial use under CC BY 4.0 (Weather data by Open-Meteo.com)."
)
DEFAULT_FORECAST_CACHE_DIR = CACHE_DIR / "api" / "open_meteo"
FORECAST_CACHE_ENV_VAR = "FORECAST_CACHE_DIR"

FORECAST_VARIABLE_META: dict[str, tuple[str, str]] = {
    **open_meteo.VARIABLE_META,
    "temperature_2m_mean": ("Mean air temperature at 2 m", "°C"),
    "water_balance": ("Daily climatic water balance (precipitation - ET0)", "mm/day"),
}

DOMAIN_VARIABLE_MAPPINGS: dict[str, tuple[str, ...]] = {
    "rain": ("precipitation_sum", "precipitation_probability_max"),
    "temperature": ("temperature_2m_max", "temperature_2m_min", "temperature_2m_mean"),
    "et0": ("et0_fao_evapotranspiration",),
    "water_balance": ("water_balance",),
    "radiation": ("shortwave_radiation_sum",),
    "wind": ("wind_speed_10m_max",),
}


def resolve_forecast_cache_dir(cache_dir: Path | str | None = None) -> Path:
    """Resolve the cache directory for Open-Meteo forecast payloads.

    Precedence:
    1. Explicit `cache_dir` argument.
    2. `FORECAST_CACHE_DIR` environment variable.
    3. Default path `data/cache/api/open_meteo`.
    """
    if cache_dir is not None:
        return Path(cache_dir)
    env_dir = os.environ.get(FORECAST_CACHE_ENV_VAR)
    if env_dir and env_dir.strip():
        return Path(env_dir.strip())
    return DEFAULT_FORECAST_CACHE_DIR


class VariableSchema(BaseModel):
    """Schema for a forecast variable."""

    model_config = ConfigDict(extra="forbid")

    name: str
    long_name: str
    unit: str


class PeriodSchema(BaseModel):
    """Temporal coverage period of the forecast."""

    model_config = ConfigDict(extra="forbid")

    start: str
    end: str


class AttributionSchema(BaseModel):
    """Data attribution matching series.schema.json."""

    model_config = ConfigDict(extra="forbid")

    dataset: str
    doi: str | None = None
    url: str
    notice: str | None = None


class SeriesPoint(BaseModel):
    """A single daily timestamp and variable values dict."""

    model_config = ConfigDict(extra="forbid")

    time: str
    values: dict[str, float | None]


class ForecastSeries(BaseModel):
    """A domain-specific series conforming to snapshot series semantics."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["open-meteo"] = OPEN_METEO_SOURCE_ID
    nasa: Literal[False] = False
    region: str
    variables: list[VariableSchema]
    aggregation: Literal["cell_mean", "nearest_cell", "window_mean"] = "nearest_cell"
    resolution: str = "~9 km (ECMWF IFS) / ~25 km (NOAA GFS)"
    period: PeriodSchema
    attribution: AttributionSchema
    points: dict[str, list[SeriesPoint]]
    series: list[SeriesPoint]

    def to_series_schema_dict(self) -> dict[str, Any]:
        """Convert into a dictionary strictly conforming to series.schema.json."""
        return {
            "source": self.source,
            "region": self.region,
            "variables": [v.model_dump() for v in self.variables],
            "aggregation": self.aggregation,
            "resolution": self.resolution,
            "period": self.period.model_dump(),
            "attribution": self.attribution.model_dump(),
            "points": {k: [pt.model_dump() for pt in v] for k, v in self.points.items()},
        }


class SourceAttributionResponse(BaseModel):
    """Source attribution model matching recommendation.schema.json#/$defs/sourceAttribution."""

    model_config = ConfigDict(extra="forbid")

    source: str
    dataset: str
    nasa: bool = False
    url: str
    doi: str | None = None
    notice: str | None = None


class DomainSourceSpec(BaseModel):
    """Attribution spec for a domain series."""

    model_config = ConfigDict(extra="forbid")

    source: str
    nasa: bool = False


class ProjectionSummary(BaseModel):
    """Projection summary matching recommendation.schema.json#/$defs/projection."""

    model_config = ConfigDict(extra="forbid")

    period_start: str
    period_end: str
    horizon_days: int
    available: bool
    rain_total_mm: float | None = None
    rain_daily_mean_mm: float | None = None
    temperature_mean_c: float | None = None
    temperature_max_c: float | None = None
    et0_daily_mean_mm: float | None = None
    water_balance_mm: float | None = None
    sources: list[SourceAttributionResponse] = []


class ForecastPointCoord(BaseModel):
    """Point coordinate representation."""

    model_config = ConfigDict(extra="forbid")

    lat: float
    lon: float


class ForecastPlot(BaseModel):
    """Target plot geographic metadata."""

    model_config = ConfigDict(extra="forbid")

    lat: float
    lon: float
    radius_km: float
    region: str
    id: str | None = None
    name: str | None = None


class ForecastResponse(BaseModel):
    """Root response model for GET /forecast."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["open-meteo"] = OPEN_METEO_SOURCE_ID
    model: str
    nasa: Literal[False] = False
    notice: str = OPEN_METEO_NOTICE
    attribution: AttributionSchema
    plot: ForecastPlot
    point: ForecastPointCoord
    period: PeriodSchema
    horizon_days: int
    cached: bool
    cache_key: str
    variables: list[VariableSchema]
    series: list[SeriesPoint]
    rain: ForecastSeries | None = None
    temperature: ForecastSeries | None = None
    et0: ForecastSeries | None = None
    water_balance: ForecastSeries | None = None
    radiation: ForecastSeries | None = None
    wind: ForecastSeries | None = None
    domains: dict[str, ForecastSeries]
    domain_sources: dict[str, DomainSourceSpec]
    sources: list[SourceAttributionResponse]
    projection: ProjectionSummary
    summary: ProjectionSummary


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two points in kilometers."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


@functools.lru_cache(maxsize=1)
def _load_sergipe_features() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load pilots and points GeoJSON features safely if present."""
    pilots: list[dict[str, Any]] = []
    points: list[dict[str, Any]] = []

    pilots_path = ROOT / "apps" / "web" / "public" / "data" / "sergipe" / "pilots.geojson"
    if pilots_path.is_file():
        try:
            data = json.loads(pilots_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                pilots = data.get("features", [])
        except (OSError, ValueError):
            pass

    points_path = ROOT / "apps" / "web" / "public" / "data" / "sergipe" / "points.geojson"
    if points_path.is_file():
        try:
            data = json.loads(points_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                points = data.get("features", [])
        except (OSError, ValueError):
            pass

    return pilots, points


def _resolve_plot(lat: float, lon: float, radius_km: float, region: str) -> ForecastPlot:
    """Resolve plot identifier and name from local pilots or grid points when inside Sergipe."""
    if region == "sergipe":
        pilots, points = _load_sergipe_features()

        best_pilot_id: str | None = None
        best_pilot_name: str | None = None
        min_pilot_dist = float("inf")

        for feat in pilots:
            props = feat.get("properties") or {}
            coords = feat.get("geometry", {}).get("coordinates") or []
            p_lat = props.get("lat") if props.get("lat") is not None else (coords[1] if len(coords) >= 2 else None)
            p_lon = props.get("lon") if props.get("lon") is not None else (coords[0] if len(coords) >= 2 else None)
            if p_lat is not None and p_lon is not None:
                d = haversine_km(lat, lon, float(p_lat), float(p_lon))
                if d < min_pilot_dist:
                    min_pilot_dist = d
                    best_pilot_id = str(feat.get("id") or props.get("id"))
                    best_pilot_name = props.get("name")

        if best_pilot_id is not None and min_pilot_dist <= 1.5:
            return ForecastPlot(
                lat=lat,
                lon=lon,
                radius_km=radius_km,
                region=region,
                id=best_pilot_id,
                name=best_pilot_name,
            )

        best_point_id: str | None = None
        best_point_name: str | None = None
        min_point_dist = float("inf")

        for feat in points:
            props = feat.get("properties") or {}
            coords = feat.get("geometry", {}).get("coordinates") or []
            p_lat = props.get("lat") if props.get("lat") is not None else (coords[1] if len(coords) >= 2 else None)
            p_lon = props.get("lon") if props.get("lon") is not None else (coords[0] if len(coords) >= 2 else None)
            if p_lat is not None and p_lon is not None:
                d = haversine_km(lat, lon, float(p_lat), float(p_lon))
                if d < min_point_dist:
                    min_point_dist = d
                    best_point_id = str(feat.get("id") or props.get("id"))
                    best_point_name = props.get("name")

        if best_point_id is not None:
            return ForecastPlot(
                lat=lat,
                lon=lon,
                radius_km=radius_km,
                region=region,
                id=best_point_id,
                name=best_point_name,
            )

    return ForecastPlot(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        region=region,
        id="PLOT",
        name=None,
    )


def get_variable_schema(name: str) -> VariableSchema:
    """Retrieve metadata description and unit for a forecast variable."""
    meta = FORECAST_VARIABLE_META.get(name)
    if meta is not None:
        return VariableSchema(name=name, long_name=meta[0], unit=meta[1])
    long_name = name.replace("_", " ").capitalize()
    return VariableSchema(name=name, long_name=long_name, unit="")


def _validate_forecast_params(
    lat: float,
    lon: float,
    radius_km: float,
    days: int | None,
    forecast_days: int | None,
    model: str,
    variables: str | list[str] | tuple[str, ...] | None,
) -> tuple[int, str, list[str]]:
    """Validate query parameters and resolve horizon, model, and variables."""
    if not isinstance(lat, (int, float)) or not math.isfinite(lat) or not (-89.0 <= lat <= 89.0):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message=f"Invalid parameter 'lat': must be a finite number between -89.0 and 89.0, got {lat}.",
        )

    if not isinstance(lon, (int, float)) or not math.isfinite(lon) or not (-180.0 <= lon <= 180.0):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message=f"Invalid parameter 'lon': must be a finite number between -180.0 and 180.0, got {lon}.",
        )

    if not isinstance(radius_km, (int, float)) or not math.isfinite(radius_km) or not (0.0 < radius_km <= 50.0):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message=f"Invalid parameter 'radius_km': must be greater than 0 and at most 50.0 km, got {radius_km}.",
        )

    if days is not None and forecast_days is not None and days != forecast_days:
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message=f"Conflicting parameters: days={days} and forecast_days={forecast_days}. Provide only one.",
        )

    resolved_days = days if days is not None else (forecast_days if forecast_days is not None else open_meteo.DEFAULT_FORECAST_DAYS)
    if isinstance(resolved_days, bool) or not isinstance(resolved_days, int) or not (1 <= resolved_days <= open_meteo.MAX_FORECAST_DAYS):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message=f"Invalid parameter: forecast horizon must be an integer between 1 and {open_meteo.MAX_FORECAST_DAYS}, got {resolved_days}.",
        )

    if not isinstance(model, str):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message=f"Invalid parameter 'model': expected string, got {type(model).__name__}.",
        )

    model_key = model.strip().lower()
    if not model_key or model_key not in open_meteo.SUPPORTED_MODELS:
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message=f"Invalid parameter 'model': unsupported model '{model}'. Choose from {', '.join(open_meteo.SUPPORTED_MODELS)}.",
        )

    if variables is not None:
        if isinstance(variables, str):
            try:
                selected_vars = open_meteo.parse_variables(variables)
            except InputError as err:
                raise APIError(status_code=400, code="invalid_parameter", message=str(err)) from err
        elif isinstance(variables, (list, tuple)):
            try:
                selected_vars = open_meteo.parse_variables(",".join(variables))
            except InputError as err:
                raise APIError(status_code=400, code="invalid_parameter", message=str(err)) from err
        else:
            raise APIError(
                status_code=400,
                code="invalid_parameter",
                message=f"Invalid parameter 'variables': expected string or list of strings, got {type(variables).__name__}.",
            )
    else:
        selected_vars = list(open_meteo.DEFAULT_VARIABLES)

    return resolved_days, model_key, selected_vars


def _sum_or_none(values: list[float | None]) -> float | None:
    non_null = [v for v in values if v is not None]
    return round(sum(non_null), 3) if non_null else None


def _mean_or_none(values: list[float | None]) -> float | None:
    non_null = [v for v in values if v is not None]
    return round(sum(non_null) / len(non_null), 3) if non_null else None


def _max_or_none(values: list[float | None]) -> float | None:
    non_null = [v for v in values if v is not None]
    return round(max(non_null), 3) if non_null else None


def _fetch_open_meteo_frame(
    lat: float,
    lon: float,
    selected_vars: list[str],
    horizon_days: int,
    model_key: str,
    resolved_cache_dir: Path,
    session: requests.Session | None = None,
) -> tuple[pd.DataFrame, bool]:
    """Fetch forecast DataFrame from Open-Meteo with caching and error mapping."""
    params_for_cache = open_meteo.build_params(
        lat=lat,
        lon=lon,
        variables=selected_vars,
        forecast_days=horizon_days,
        model=model_key,
    )
    cache_file = open_meteo.cache_path(resolved_cache_dir, params_for_cache)
    was_cached = open_meteo._fresh_cache(cache_file, open_meteo.CACHE_TTL_SECONDS) is not None

    try:
        frame = open_meteo.fetch_forecast(
            lat=lat,
            lon=lon,
            variables=selected_vars,
            forecast_days=horizon_days,
            model=model_key,
            cache_dir=resolved_cache_dir,
            session=session,
        )
    except InputError as err:
        raise APIError(status_code=400, code="invalid_parameter", message=str(err)) from err
    except RemoteDataError as err:
        err_msg = str(err)
        err_lower = err_msg.lower()
        if "timeout" in err_lower or "timed out" in err_lower:
            raise APIError(status_code=504, code="upstream_timeout", message=err_msg) from err
        if (
            "only null values" in err_lower
            or "no daily forecast data" in err_lower
            or "no forecast variables" in err_lower
        ):
            raise APIError(status_code=422, code="no_data", message=err_msg) from err
        raise APIError(status_code=502, code="upstream_error", message=err_msg) from err

    frame = frame.sort_index()
    if frame.empty:
        raise APIError(status_code=422, code="no_data", message="No daily forecast data returned.")

    return frame, was_cached


def _derive_daily_records(
    frame: pd.DataFrame,
) -> tuple[list[tuple[str, dict[str, float | None]]], list[str]]:
    """Build chronological daily records with derived temperature mean and water balance."""
    daily_records: list[tuple[str, dict[str, float | None]]] = []
    has_temp_mean = "temperature_2m_mean" in frame.columns
    has_temp_max = "temperature_2m_max" in frame.columns
    has_temp_min = "temperature_2m_min" in frame.columns
    has_precip = "precipitation_sum" in frame.columns
    has_et0 = "et0_fao_evapotranspiration" in frame.columns
    has_wb = "water_balance" in frame.columns

    for ts, row in frame.iterrows():
        day_str = ts.strftime("%Y-%m-%d")
        row_dict: dict[str, float | None] = {}
        for col in frame.columns:
            val = row[col]
            row_dict[col] = None if pd.isna(val) else round(float(val), 3)

        if not has_temp_mean and (has_temp_max or has_temp_min):
            t_max = row_dict.get("temperature_2m_max")
            t_min = row_dict.get("temperature_2m_min")
            if t_max is not None and t_min is not None:
                row_dict["temperature_2m_mean"] = round((t_max + t_min) / 2.0, 3)
            elif t_max is not None:
                row_dict["temperature_2m_mean"] = t_max
            elif t_min is not None:
                row_dict["temperature_2m_mean"] = t_min
            else:
                row_dict["temperature_2m_mean"] = None

        if not has_wb and (has_precip and has_et0):
            p_val = row_dict.get("precipitation_sum")
            e_val = row_dict.get("et0_fao_evapotranspiration")
            if p_val is not None and e_val is not None:
                row_dict["water_balance"] = round(p_val - e_val, 3)
            else:
                row_dict["water_balance"] = None

        daily_records.append((day_str, row_dict))

    all_var_names: list[str] = list(frame.columns)
    if not has_temp_mean and (has_temp_max or has_temp_min):
        all_var_names.append("temperature_2m_mean")
    if not has_wb and (has_precip and has_et0):
        all_var_names.append("water_balance")

    return daily_records, all_var_names


def _build_domain_series(
    daily_records: list[tuple[str, dict[str, float | None]]],
    all_var_names: list[str],
    region: str,
    plot_key: str,
    period: PeriodSchema,
    attribution: AttributionSchema,
) -> dict[str, ForecastSeries]:
    """Group daily records by domain and build ForecastSeries objects."""
    domains: dict[str, ForecastSeries] = {}

    for d_name, candidate_vars in DOMAIN_VARIABLE_MAPPINGS.items():
        domain_active_vars = [v for v in candidate_vars if v in all_var_names]
        if domain_active_vars:
            domain_points: list[SeriesPoint] = []
            for day_str, row_dict in daily_records:
                d_vals = {v: row_dict.get(v) for v in domain_active_vars}
                domain_points.append(SeriesPoint(time=day_str, values=d_vals))

            domains[d_name] = ForecastSeries(
                source=OPEN_METEO_SOURCE_ID,
                nasa=False,
                region=region,
                variables=[get_variable_schema(v) for v in domain_active_vars],
                aggregation="nearest_cell",
                resolution="~9 km (ECMWF IFS) / ~25 km (NOAA GFS)",
                period=period,
                attribution=attribution,
                points={plot_key: domain_points},
                series=domain_points,
            )

    return domains


def _build_projection_summary(
    daily_records: list[tuple[str, dict[str, float | None]]],
    period: PeriodSchema,
    source_attribution: SourceAttributionResponse,
) -> ProjectionSummary:
    """Aggregate daily metrics into a recommendation projection summary."""
    precip_values = [
        row_dict.get("precipitation_sum") for _, row_dict in daily_records if "precipitation_sum" in row_dict
    ]
    rain_total_mm = _sum_or_none(precip_values)
    rain_daily_mean_mm = _mean_or_none(precip_values)

    temp_mean_values = [
        row_dict.get("temperature_2m_mean") for _, row_dict in daily_records if "temperature_2m_mean" in row_dict
    ]
    temperature_mean_c = _mean_or_none(temp_mean_values)

    temp_max_values = [
        row_dict.get("temperature_2m_max") for _, row_dict in daily_records if "temperature_2m_max" in row_dict
    ]
    temperature_max_c = _max_or_none(temp_max_values)

    et0_values = [
        row_dict.get("et0_fao_evapotranspiration")
        for _, row_dict in daily_records
        if "et0_fao_evapotranspiration" in row_dict
    ]
    et0_daily_mean_mm = _mean_or_none(et0_values)

    wb_values = [row_dict.get("water_balance") for _, row_dict in daily_records if "water_balance" in row_dict]
    water_balance_mm = _sum_or_none(wb_values)

    return ProjectionSummary(
        period_start=period.start,
        period_end=period.end,
        horizon_days=len(daily_records),
        available=True,
        rain_total_mm=rain_total_mm,
        rain_daily_mean_mm=rain_daily_mean_mm,
        temperature_mean_c=temperature_mean_c,
        temperature_max_c=temperature_max_c,
        et0_daily_mean_mm=et0_daily_mean_mm,
        water_balance_mm=water_balance_mm,
        sources=[source_attribution],
    )


def build_forecast_response(
    lat: float,
    lon: float,
    radius_km: float = 5.0,
    days: int | None = None,
    forecast_days: int | None = None,
    model: str = "best_match",
    variables: str | list[str] | tuple[str, ...] | None = None,
    cache_dir: Path | str | None = None,
    session: requests.Session | None = None,
) -> ForecastResponse:
    """Fetch, derive metrics, and construct full ForecastResponse for a geographic location."""
    horizon_days, model_key, selected_vars = _validate_forecast_params(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        days=days,
        forecast_days=forecast_days,
        model=model,
        variables=variables,
    )

    sergipe_bbox = PRESETS.get("sergipe")
    if sergipe_bbox and (sergipe_bbox.south <= lat <= sergipe_bbox.north) and (sergipe_bbox.west <= lon <= sergipe_bbox.east):
        region = "sergipe"
    else:
        region = "external"

    plot = _resolve_plot(lat=lat, lon=lon, radius_km=radius_km, region=region)
    resolved_cache_dir = resolve_forecast_cache_dir(cache_dir)
    cache_key = f"open-meteo:{round(lat, 2):.2f}:{round(lon, 2):.2f}:{horizon_days}d:{model_key}"

    frame, was_cached = _fetch_open_meteo_frame(
        lat=lat,
        lon=lon,
        selected_vars=selected_vars,
        horizon_days=horizon_days,
        model_key=model_key,
        resolved_cache_dir=resolved_cache_dir,
        session=session,
    )

    daily_records, all_var_names = _derive_daily_records(frame)
    variables_schema_list = [get_variable_schema(v) for v in all_var_names]
    series_points = [SeriesPoint(time=day_str, values=row_vals) for day_str, row_vals in daily_records]

    period_schema = PeriodSchema(
        start=frame.index.min().strftime("%Y-%m-%d"),
        end=frame.index.max().strftime("%Y-%m-%d"),
    )
    attribution_schema = AttributionSchema(
        dataset=OPEN_METEO_DATASET,
        doi=None,
        url=OPEN_METEO_URL,
        notice=OPEN_METEO_NOTICE,
    )
    open_meteo_source_attr = SourceAttributionResponse(
        source=OPEN_METEO_SOURCE_ID,
        dataset=OPEN_METEO_DATASET,
        nasa=False,
        url=OPEN_METEO_URL,
        doi=None,
        notice=OPEN_METEO_NOTICE,
    )

    plot_key = plot.id or "PLOT"
    domains = _build_domain_series(
        daily_records=daily_records,
        all_var_names=all_var_names,
        region=region,
        plot_key=plot_key,
        period=period_schema,
        attribution=attribution_schema,
    )
    domain_sources = {d_name: DomainSourceSpec(source=OPEN_METEO_SOURCE_ID, nasa=False) for d_name in domains}

    projection_summary = _build_projection_summary(
        daily_records=daily_records,
        period=period_schema,
        source_attribution=open_meteo_source_attr,
    )

    return ForecastResponse(
        source=OPEN_METEO_SOURCE_ID,
        model=model_key,
        nasa=False,
        notice=OPEN_METEO_NOTICE,
        attribution=attribution_schema,
        plot=plot,
        point=ForecastPointCoord(lat=round(lat, 4), lon=round(lon, 4)),
        period=period_schema,
        horizon_days=horizon_days,
        cached=was_cached,
        cache_key=cache_key,
        variables=variables_schema_list,
        series=series_points,
        rain=domains.get("rain"),
        temperature=domains.get("temperature"),
        et0=domains.get("et0"),
        water_balance=domains.get("water_balance"),
        radiation=domains.get("radiation"),
        wind=domains.get("wind"),
        domains=domains,
        domain_sources=domain_sources,
        sources=[open_meteo_source_attr],
        projection=projection_summary,
        summary=projection_summary,
    )


def build_engine_projection(
    lat: float,
    lon: float,
    forecast_days: int = 15,
    model: str = "best_match",
    cache_dir: Path | str | None = None,
    session: requests.Session | None = None,
    allow_unavailable: bool = True,
) -> Projection:
    """Fetch weather forecast and build a Projection domain model instance for the decision engine."""
    source_attr = SourceAttribution(
        source=OPEN_METEO_SOURCE_ID,
        dataset=OPEN_METEO_DATASET,
        nasa=False,
        url=OPEN_METEO_URL,
        doi=None,
        notice=OPEN_METEO_NOTICE,
    )

    try:
        resp = build_forecast_response(
            lat=lat,
            lon=lon,
            days=forecast_days,
            model=model,
            cache_dir=cache_dir,
            session=session,
        )
        proj_sum = resp.projection
        return Projection(
            period_start=proj_sum.period_start,
            period_end=proj_sum.period_end,
            horizon_days=proj_sum.horizon_days,
            available=proj_sum.available,
            rain_total_mm=proj_sum.rain_total_mm,
            rain_daily_mean_mm=proj_sum.rain_daily_mean_mm,
            temperature_mean_c=proj_sum.temperature_mean_c,
            temperature_max_c=proj_sum.temperature_max_c,
            et0_daily_mean_mm=proj_sum.et0_daily_mean_mm,
            water_balance_mm=proj_sum.water_balance_mm,
            sources=(source_attr,),
        )
    except APIError as exc:
        if allow_unavailable and exc.status_code in {422, 502, 504}:
            today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return Projection(
                period_start=today_iso,
                period_end=today_iso,
                horizon_days=forecast_days,
                available=False,
                sources=(source_attr,),
            )
        raise
    except RemoteDataError as exc:
        if allow_unavailable:
            today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return Projection(
                period_start=today_iso,
                period_end=today_iso,
                horizon_days=forecast_days,
                available=False,
                sources=(source_attr,),
            )
        raise
