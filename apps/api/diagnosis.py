# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Diagnosis service, snapshot reader, spatial matching, and response models for /diagnosis."""

from __future__ import annotations

import json
import math
import os
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.api.errors import APIError
from apps.api.sources_catalog import SOURCES_BY_ID
from src.data.municipality import municipality_code
from src.data.paths import ROOT
from src.data.regions import PRESETS
from src.engine.model import BareSoilWindow, Diagnosis, Plot, SourceAttribution

DEFAULT_DATA_DIR = ROOT / "apps" / "web" / "public" / "data"
SERGIPE_BBOX = PRESETS["sergipe"]
MAX_RADIUS_KM = 50.0
PILOT_MATCH_RADIUS_KM = 1.5
MAX_GRID_MATCH_DISTANCE_KM = 25.0
DEFAULT_BARE_SOIL_NDVI_MAX = 0.30

# Memory cache for parsed JSON files keyed by (resolved_path, mtime_ns, file_size)
_JSON_CACHE: dict[tuple[Path, int, int], dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Pydantic Response Models (Strictly adhering to JSON schemas)
# ---------------------------------------------------------------------------


class MatchedPoint(BaseModel):
    """Metadata describing the matched pilot site or grid point."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str | None = None
    kind: Literal["pilot", "grid"]
    lat: float
    lon: float
    distance_km: float


class DiagnosisPlot(BaseModel):
    """Plot envelope for the /diagnosis endpoint."""

    model_config = ConfigDict(extra="forbid")

    lat: float
    lon: float
    radius_km: float
    region: str = "sergipe"
    matched_point: MatchedPoint
    id: str | None = None
    name: str | None = None
    municipality_code: str | None = None
    elevation_m: float | None = None
    slope_mean_pct: float | None = None


class VariableSchema(BaseModel):
    """Variable spec matching docs/data-format/series.schema.json#/$defs/variable."""

    model_config = ConfigDict(extra="forbid")

    name: str
    long_name: str
    unit: str


class PeriodSchema(BaseModel):
    """Period spec matching docs/data-format/series.schema.json#/$defs/period."""

    model_config = ConfigDict(extra="forbid")

    start: str
    end: str


class AttributionSchema(BaseModel):
    """Attribution spec matching docs/data-format/series.schema.json#/$defs/attribution."""

    model_config = ConfigDict(extra="forbid")

    dataset: str
    doi: str | None = None
    url: str
    notice: str | None = None


class SeriesPoint(BaseModel):
    """Observation item matching docs/data-format/series.schema.json#/$defs/seriesPoint."""

    model_config = ConfigDict(extra="forbid")

    time: str
    values: dict[str, float | None]


class SeriesData(BaseModel):
    """Time-series envelope strictly complying with docs/data-format/series.schema.json."""

    model_config = ConfigDict(extra="forbid")

    source: str
    region: str
    variables: list[VariableSchema]
    aggregation: Literal["cell_mean", "nearest_cell", "window_mean"]
    resolution: str
    period: PeriodSchema | None = None
    attribution: AttributionSchema
    points: dict[str, list[SeriesPoint]]


class StaticDataResponse(BaseModel):
    """Static layer envelope strictly complying with docs/data-format/static.schema.json."""

    model_config = ConfigDict(extra="forbid")

    source: str
    region: str
    variables: list[VariableSchema]
    aggregation: Literal["cell_mean", "nearest_cell", "window_mean"]
    resolution: str
    attribution: AttributionSchema
    points: dict[str, dict[str, float | None]]


class BareSoilWindowResponse(BaseModel):
    """Exposed soil window matching docs/data-format/recommendation.schema.json#/$defs/bareSoilWindow."""

    model_config = ConfigDict(extra="forbid")

    start: str
    end: str
    ndvi_mean: float | None = None
    description: str | None = None


class SourceAttributionResponse(BaseModel):
    """Source attribution matching docs/data-format/recommendation.schema.json#/$defs/sourceAttribution."""

    model_config = ConfigDict(extra="forbid")

    source: str
    dataset: str
    nasa: bool = True
    url: str
    doi: str | None = None
    notice: str | None = None


class DomainSourceSpec(BaseModel):
    """Source reference mapping for a specific agro-climatic domain."""

    model_config = ConfigDict(extra="forbid")

    source: str
    nasa: bool = True


class DiagnosisSummary(BaseModel):
    """Summary metrics strictly matching docs/data-format/recommendation.schema.json#/$defs/diagnosis."""

    model_config = ConfigDict(extra="forbid")

    period_start: str
    period_end: str
    rain_total_mm: float | None = None
    rain_daily_mean_mm: float | None = None
    et0_daily_mean_mm: float | None = None
    water_balance_mm: float | None = None
    soil_moisture_surface_m3m3: float | None = None
    soil_moisture_root_kgm2: float | None = None
    temperature_mean_c: float | None = None
    temperature_max_c: float | None = None
    ndvi_mean: float | None = None
    elevation_m: float | None = None
    slope_mean_pct: float | None = None
    bare_soil_windows: list[BareSoilWindowResponse] = Field(default_factory=list)
    sources: list[SourceAttributionResponse] = Field(default_factory=list)


class DomainCoverage(BaseModel):
    """Coverage statistics for a single domain relative to its source and the aligned period."""

    model_config = ConfigDict(extra="forbid")

    source: str
    period: PeriodSchema | None = None
    expected_days: int = 0
    observed_days: int = 0
    paired_days: int = 0
    missing_days: int = 0
    complete: bool = False


class DiagnosisCoverage(BaseModel):
    """Summary alignment and completeness disclosure across daily domains."""

    model_config = ConfigDict(extra="forbid")

    period_start: str | None = None
    period_end: str | None = None
    aligned: bool
    complete: bool
    expected_days: int
    paired_days: int
    missing_days: int
    missing_dates: list[str] = Field(default_factory=list)
    domains: dict[str, DomainCoverage] = Field(default_factory=dict)


class DiagnosisResponse(BaseModel):
    """Root response model for the GET /diagnosis endpoint."""

    model_config = ConfigDict(extra="forbid")

    plot: DiagnosisPlot
    rain: SeriesData
    soil_moisture: SeriesData
    gldas: SeriesData | None = None
    temperature: SeriesData
    ndvi: SeriesData | None = None
    et0: SeriesData
    water_balance: SeriesData
    terrain: StaticDataResponse
    bare_soil_windows: list[BareSoilWindowResponse]
    summary: DiagnosisSummary
    coverage: DiagnosisCoverage
    sources: list[SourceAttributionResponse]
    domain_sources: dict[str, DomainSourceSpec]


# ---------------------------------------------------------------------------
# Validation & Parameter Check Helpers
# ---------------------------------------------------------------------------


def _validate_diagnosis_params(lat: float, lon: float, radius_km: float) -> None:
    """Validate latitude, longitude, radius, and Sergipe region bounding box."""
    if not math.isfinite(lat):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message="Invalid parameter 'lat': must be a finite number.",
        )
    if not math.isfinite(lon):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message="Invalid parameter 'lon': must be a finite number.",
        )
    if not math.isfinite(radius_km):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message="Invalid parameter 'radius_km': must be a finite number.",
        )

    if not (-89.0 <= lat <= 89.0):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message=f"Invalid parameter 'lat': latitude {lat} out of range [-89.0, 89.0].",
        )
    if not (-180.0 <= lon <= 180.0):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message=f"Invalid parameter 'lon': longitude {lon} out of range [-180.0, 180.0].",
        )
    if not (0.0 < radius_km <= MAX_RADIUS_KM):
        raise APIError(
            status_code=400,
            code="invalid_parameter",
            message=f"Invalid parameter 'radius_km': radius {radius_km} must be in (0.0, 50.0].",
        )

    if not (SERGIPE_BBOX.west <= lon <= SERGIPE_BBOX.east and SERGIPE_BBOX.south <= lat <= SERGIPE_BBOX.north):
        raise APIError(
            status_code=422,
            code="no_data",
            message=f"Location ({lat}, {lon}) is outside the Sergipe region bounds.",
        )


# ---------------------------------------------------------------------------
# Snapshot Loading & Caching Helpers
# ---------------------------------------------------------------------------


def resolve_data_dir(data_dir: Path | str | None = None) -> Path:
    """Resolve data directory precedence: explicit param -> env var -> DEFAULT_DATA_DIR."""
    if data_dir is not None:
        return Path(data_dir).resolve()
    env_dir = os.environ.get("DIAGNOSIS_DATA_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return DEFAULT_DATA_DIR.resolve()


def load_json_snapshot(file_path: Path) -> dict[str, Any]:
    """Load and cache a JSON snapshot file using (path, mtime_ns, size) validation."""
    try:
        stat = file_path.stat()
    except FileNotFoundError:
        raise APIError(
            status_code=503,
            code="server_not_configured",
            message=f"Snapshot file not found: {file_path.name}",
        ) from None
    except OSError as err:
        raise APIError(
            status_code=503,
            code="server_not_configured",
            message=f"Failed to access snapshot file {file_path.name}: {err}",
        ) from None

    cache_key = (file_path.resolve(), stat.st_mtime_ns, stat.st_size)
    cached = _JSON_CACHE.get(cache_key)
    if cached is not None:
        return cached

    try:
        content = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as err:
        raise APIError(
            status_code=503,
            code="server_not_configured",
            message=f"Failed to parse snapshot JSON {file_path.name}: {err}",
        ) from None

    _JSON_CACHE[cache_key] = content
    return content


def _load_optional_snapshot(file_path: Path) -> dict[str, Any] | None:
    """Load an optional snapshot JSON file if present and readable, returning None otherwise."""
    if file_path.is_file():
        try:
            return load_json_snapshot(file_path)
        except Exception:
            return None
    return None


def get_bare_soil_threshold() -> float:
    """Read sparse_cover_ndvi_max from src/engine/rules/thresholds.yaml or fallback to 0.30."""
    candidates = (
        ROOT / "src" / "engine" / "rules" / "thresholds.yaml",
        ROOT / "src" / "engine" / "thresholds.yaml",
    )
    for p in candidates:
        if p.is_file():
            try:
                import yaml  # type: ignore[import-not-found]

                data = yaml.safe_load(p.read_text(encoding="utf-8"))
                val = data.get("vegetation_and_bare_soil", {}).get("sparse_cover_ndvi_max")
                if val is not None and isinstance(val, (int, float)):
                    return float(val)
            except Exception:
                pass
    return DEFAULT_BARE_SOIL_NDVI_MAX


# ---------------------------------------------------------------------------
# Spatial Matching Helpers
# ---------------------------------------------------------------------------


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    r = 6371.0  # Mean radius of the Earth in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def _is_valid_coord(lat_val: Any, lon_val: Any) -> tuple[bool, float, float]:
    """Validate finite latitude in [-90, 90] and longitude in [-180, 180]."""
    try:
        lat_f = float(lat_val)
        lon_f = float(lon_val)
        if (
            math.isfinite(lat_f)
            and math.isfinite(lon_f)
            and -90.0 <= lat_f <= 90.0
            and -180.0 <= lon_f <= 180.0
        ):
            return True, lat_f, lon_f
    except (TypeError, ValueError):
        pass
    return False, 0.0, 0.0


def load_points_and_pilots(
    sergipe_dir: Path,
) -> tuple[dict[str, tuple[float, float, str | None]], list[dict[str, Any]]]:
    """Load known coordinates for Sergipe grid points and named pilot sites."""
    grid_pts: dict[str, tuple[float, float, str | None]] = {}
    pilots_list: list[dict[str, Any]] = []

    # 1. Load pilots.geojson if present
    pilots_file = sergipe_dir / "pilots.geojson"
    if pilots_file.is_file():
        try:
            p_data = load_json_snapshot(pilots_file)
            for feat in p_data.get("features", []):
                if not isinstance(feat, dict):
                    continue
                props = feat.get("properties") or {}
                pid = props.get("id") or feat.get("id")
                geom = feat.get("geometry") or {}
                coords = geom.get("coordinates") if isinstance(geom, dict) else None
                plat = props.get("lat")
                if plat is None and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    plat = coords[1]
                plon = props.get("lon")
                if plon is None and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    plon = coords[0]

                if pid is not None and plat is not None and plon is not None:
                    valid, lat_f, lon_f = _is_valid_coord(plat, plon)
                    if valid:
                        raw_r = props.get("radius_km", 5.0)
                        try:
                            radius_f = float(raw_r)
                            if not math.isfinite(radius_f) or radius_f <= 0:
                                radius_f = 5.0
                        except (TypeError, ValueError):
                            radius_f = 5.0
                        pilot_entry = {
                            "id": str(pid),
                            "name": props.get("name"),
                            "lat": lat_f,
                            "lon": lon_f,
                            "radius_km": radius_f,
                        }
                        pilots_list.append(pilot_entry)
                        grid_pts[str(pid)] = (lat_f, lon_f, props.get("name"))
        except Exception:
            pass

    # 2. Load points.geojson if present
    points_file = sergipe_dir / "points.geojson"
    if points_file.is_file():
        try:
            pt_data = load_json_snapshot(points_file)
            for feat in pt_data.get("features", []):
                if not isinstance(feat, dict):
                    continue
                props = feat.get("properties") or {}
                ptid = props.get("id") or feat.get("id")
                geom = feat.get("geometry") or {}
                coords = geom.get("coordinates") if isinstance(geom, dict) else None
                ptlat = props.get("lat")
                if ptlat is None and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    ptlat = coords[1]
                ptlon = props.get("lon")
                if ptlon is None and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    ptlon = coords[0]

                if ptid is not None and ptlat is not None and ptlon is not None:
                    valid, lat_f, lon_f = _is_valid_coord(ptlat, ptlon)
                    if valid:
                        grid_pts[str(ptid)] = (lat_f, lon_f, props.get("name"))
        except Exception:
            pass

    return grid_pts, pilots_list


def find_matched_point(
    lat: float,
    lon: float,
    grid_pts: dict[str, tuple[float, float, str | None]],
    pilots_list: list[dict[str, Any]],
    available_point_ids: set[str] | None = None,
    radius_km: float = 5.0,
) -> dict[str, Any]:
    """Select the closest pilot (within 1.5 km) or nearest grid point within maximum distance."""
    # 1. Pilot matching within PILOT_MATCH_RADIUS_KM (1.5 km)
    closest_pilot: dict[str, Any] | None = None
    min_pilot_dist = float("inf")
    for p in pilots_list:
        dist = haversine_km(lat, lon, p["lat"], p["lon"])
        if dist < min_pilot_dist:
            min_pilot_dist = dist
            closest_pilot = p

    if closest_pilot is not None and min_pilot_dist <= PILOT_MATCH_RADIUS_KM:
        return {
            "id": closest_pilot["id"],
            "name": closest_pilot.get("name"),
            "kind": "pilot",
            "lat": closest_pilot["lat"],
            "lon": closest_pilot["lon"],
            "distance_km": round(min_pilot_dist, 3),
        }

    # 2. Nearest grid point matching
    if not grid_pts:
        raise APIError(
            status_code=422,
            code="no_data",
            message="No grid or pilot points with known coordinates available in snapshot data.",
        )

    pilot_ids = {p["id"] for p in pilots_list}
    best_id: str | None = None
    min_grid_dist = float("inf")

    # Prefer non-pilot grid point
    for pt_id, (pt_lat, pt_lon, _) in grid_pts.items():
        if pt_id in pilot_ids:
            continue
        dist = haversine_km(lat, lon, pt_lat, pt_lon)
        if dist < min_grid_dist:
            min_grid_dist = dist
            best_id = pt_id

    # Fallback to any point in grid_pts if only pilot points exist
    if best_id is None:
        for pt_id, (pt_lat, pt_lon, _) in grid_pts.items():
            dist = haversine_km(lat, lon, pt_lat, pt_lon)
            if dist < min_grid_dist:
                min_grid_dist = dist
                best_id = pt_id

    if best_id is None:
        raise APIError(
            status_code=422,
            code="no_data",
            message="No grid or pilot points with known coordinates available in snapshot data.",
        )

    max_allowed_km = max(radius_km, MAX_GRID_MATCH_DISTANCE_KM)
    if min_grid_dist > max_allowed_km:
        raise APIError(
            status_code=422,
            code="no_data",
            message=(
                f"Nearest known point '{best_id}' is {min_grid_dist:.2f} km away, "
                f"exceeding maximum match distance {max_allowed_km:.2f} km."
            ),
        )

    pt_lat, pt_lon, pt_name = grid_pts[best_id]
    return {
        "id": best_id,
        "name": pt_name,
        "kind": "grid",
        "lat": pt_lat,
        "lon": pt_lon,
        "distance_km": round(min_grid_dist, 3),
    }


def extract_point_data_for_source(
    source_dict: dict[str, Any],
    matched_point: dict[str, Any],
    grid_pts: dict[str, tuple[float, float, str | None]] | None = None,
) -> Any:
    """Extract observations strictly for the matched point ID, returning None if absent."""
    points_map = source_dict.get("points", {})
    if not isinstance(points_map, dict):
        return None
    matched_id = matched_point["id"]
    return points_map.get(matched_id)


def _count_non_null_ndvi(points: list[dict[str, Any]] | None) -> int:
    """Count observations that contain a valid non-null NDVI value."""
    if not points:
        return 0
    count = 0
    for obs in points:
        if isinstance(obs, dict):
            vals = obs.get("values", {})
            v = vals.get("NDVI") if "NDVI" in vals else vals.get("ndvi")
            if v is not None:
                count += 1
    return count


def _resolve_ndvi_source(
    viirs_data: dict[str, Any] | None,
    modis_data: dict[str, Any] | None,
    matched_point: dict[str, Any],
    grid_pts: dict[str, tuple[float, float, str | None]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None, str | None]:
    """Select the active NDVI source (VIIRS fallback to MODIS if empty, or None)."""
    if viirs_data is not None:
        v_pt = extract_point_data_for_source(viirs_data, matched_point, grid_pts)
        if _count_non_null_ndvi(v_pt) > 0:
            return viirs_data, v_pt, "viirs"
        if modis_data is not None:
            m_pt = extract_point_data_for_source(modis_data, matched_point, grid_pts)
            return modis_data, m_pt, "modis"
        return viirs_data, v_pt, "viirs"

    if modis_data is not None:
        m_pt = extract_point_data_for_source(modis_data, matched_point, grid_pts)
        return modis_data, m_pt, "modis"

    return None, None, None


# ---------------------------------------------------------------------------
# Calendar Expansion & Time-Series Construction Helpers
# ---------------------------------------------------------------------------


def expand_daily_series(
    point_data: list[dict[str, Any]] | None,
    period: dict[str, Any] | None,
    variables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expand daily observations onto an exact, contiguous calendar spine (inclusive)."""
    obs_by_date: dict[str, dict[str, Any]] = {}
    if point_data:
        for item in point_data:
            if isinstance(item, dict) and "time" in item:
                obs_by_date[item["time"]] = item.get("values", {})

    var_names = [v["name"] for v in variables]

    if not period or not period.get("start") or not period.get("end"):
        sorted_times = sorted(obs_by_date.keys())
        return [
            {
                "time": t,
                "values": {v: obs_by_date[t].get(v) for v in var_names},
            }
            for t in sorted_times
        ]

    start_d = date.fromisoformat(period["start"])
    end_d = date.fromisoformat(period["end"])

    calendar_points: list[dict[str, Any]] = []
    curr = start_d
    while curr <= end_d:
        t_str = curr.isoformat()
        day_vals = obs_by_date.get(t_str)
        values_dict: dict[str, float | None] = {}
        for v in var_names:
            if day_vals is not None and v in day_vals:
                raw_val = day_vals[v]
                values_dict[v] = float(raw_val) if raw_val is not None else None
            else:
                values_dict[v] = None
        calendar_points.append({"time": t_str, "values": values_dict})
        curr += timedelta(days=1)

    return calendar_points


def slice_series(
    source_dict: dict[str, Any],
    matched_point_id: str,
    point_data: list[dict[str, Any]] | None,
    target_variable_names: set[str],
    daily: bool = True,
    fallback_variables: list[VariableSchema] | None = None,
) -> SeriesData:
    """Build a series.schema.json compliant SeriesData object for a target variable slice."""
    all_vars = source_dict.get("variables", [])
    matching_vars = [v for v in all_vars if v.get("name") in target_variable_names]

    if not matching_vars and fallback_variables:
        var_models = fallback_variables
    elif not matching_vars and all_vars:
        var_models = [
            VariableSchema(
                name=v["name"],
                long_name=v.get("long_name", v["name"]),
                unit=v.get("unit", "dimensionless"),
            )
            for v in all_vars[:1]
        ]
    else:
        var_models = [
            VariableSchema(
                name=v["name"],
                long_name=v.get("long_name", v["name"]),
                unit=v.get("unit", "dimensionless"),
            )
            for v in matching_vars
        ]

    vars_dict_list = [{"name": vm.name, "long_name": vm.long_name, "unit": vm.unit} for vm in var_models]
    period_dict = source_dict.get("period")
    period_model = (
        PeriodSchema(start=period_dict["start"], end=period_dict["end"])
        if period_dict and period_dict.get("start") and period_dict.get("end")
        else None
    )

    if daily:
        expanded = expand_daily_series(point_data, period_dict, vars_dict_list)
    else:
        # Multi-day composite or monthly: sort chronologically, preserve None
        sorted_items = sorted(
            [item for item in (point_data or []) if isinstance(item, dict) and "time" in item],
            key=lambda x: str(x.get("time", "")),
        )
        expanded = []
        for item in sorted_items:
            t = item["time"]
            vals = item.get("values", {})
            v_dict: dict[str, float | None] = {}
            for vm in var_models:
                raw_v = vals.get(vm.name)
                v_dict[vm.name] = float(raw_v) if raw_v is not None else None
            expanded.append({"time": t, "values": v_dict})

    raw_attr = source_dict.get("attribution", {})
    attr_model = AttributionSchema(
        dataset=str(raw_attr.get("dataset", "")),
        doi=raw_attr.get("doi"),
        url=str(raw_attr.get("url", "https://earthdata.nasa.gov/")),
        notice=raw_attr.get("notice"),
    )

    series_points = [SeriesPoint(time=item["time"], values=item["values"]) for item in expanded]

    return SeriesData(
        source=str(source_dict.get("source", "")),
        region=str(source_dict.get("region", "sergipe")),
        variables=var_models,
        aggregation=source_dict.get("aggregation", "cell_mean"),
        resolution=str(source_dict.get("resolution", "")),
        period=period_model,
        attribution=attr_model,
        points={matched_point_id: series_points} if series_points else {},
    )


def slice_static(
    source_dict: dict[str, Any],
    matched_point_id: str,
    point_data: dict[str, Any] | None,
) -> StaticDataResponse:
    """Build a static.schema.json compliant StaticDataResponse object."""
    all_vars = source_dict.get("variables", [])
    var_models = [
        VariableSchema(
            name=v["name"],
            long_name=v.get("long_name", v["name"]),
            unit=v.get("unit", "dimensionless"),
        )
        for v in all_vars
    ]
    raw_attr = source_dict.get("attribution", {})
    attr_model = AttributionSchema(
        dataset=str(raw_attr.get("dataset", "")),
        doi=raw_attr.get("doi"),
        url=str(raw_attr.get("url", "https://earthdata.nasa.gov/")),
        notice=raw_attr.get("notice"),
    )

    pt_vals: dict[str, float | None] = {}
    for vm in var_models:
        val = point_data.get(vm.name) if isinstance(point_data, dict) else None
        pt_vals[vm.name] = float(val) if val is not None else None

    return StaticDataResponse(
        source=str(source_dict.get("source", "srtm")),
        region=str(source_dict.get("region", "sergipe")),
        variables=var_models,
        aggregation=source_dict.get("aggregation", "window_mean"),
        resolution=str(source_dict.get("resolution", "30 m (1 arc-second)")),
        attribution=attr_model,
        points={matched_point_id: pt_vals},
    )


def compute_bare_soil_windows(
    ndvi_points: list[dict[str, Any]] | None,
    period_end: str | None = None,
    threshold: float = DEFAULT_BARE_SOIL_NDVI_MAX,
) -> list[BareSoilWindow]:
    """Scan chronological NDVI composite observations for contiguous runs where NDVI <= threshold."""
    if not ndvi_points:
        return []

    sorted_obs: list[tuple[date, float]] = []
    for item in sorted(ndvi_points, key=lambda x: str(x.get("time", ""))):
        t_str = item.get("time")
        if not t_str:
            continue
        try:
            d = date.fromisoformat(t_str)
        except ValueError:
            continue
        vals = item.get("values", {})
        val = vals.get("NDVI") if "NDVI" in vals else vals.get("ndvi")
        if val is not None and isinstance(val, (int, float)):
            sorted_obs.append((d, float(val)))

    if not sorted_obs:
        return []

    parsed_period_end: date | None = None
    if period_end:
        try:
            parsed_period_end = date.fromisoformat(period_end)
        except ValueError:
            parsed_period_end = None

    windows: list[BareSoilWindow] = []
    current_run: list[tuple[date, float]] = []

    def _flush_run(run: list[tuple[date, float]]) -> BareSoilWindow:
        start_d = run[0][0]
        last_d = run[-1][0]
        candidate_end = last_d + timedelta(days=15)
        if parsed_period_end is not None and parsed_period_end >= last_d:
            end_d = min(candidate_end, parsed_period_end)
        else:
            end_d = candidate_end
        mean_ndvi = round(sum(v for _, v in run) / len(run), 3)
        desc = f"Bare soil / sparse vegetation window (mean NDVI {mean_ndvi:.3f})"
        return BareSoilWindow(
            start=start_d.isoformat(),
            end=end_d.isoformat(),
            ndvi_mean=mean_ndvi,
            description=desc,
        )

    for d, val in sorted_obs:
        if val <= threshold:
            current_run.append((d, val))
        else:
            if current_run:
                windows.append(_flush_run(current_run))
                current_run = []

    if current_run:
        windows.append(_flush_run(current_run))

    return windows


def build_source_attribution(
    source_id: str,
    snapshot_dict: dict[str, Any] | None,
    notice_suffix: str | None = None,
) -> SourceAttribution:
    """Build a SourceAttribution dataclass using snapshot attribution and catalog metadata."""
    catalog_entry = SOURCES_BY_ID.get(source_id)
    raw_attr = snapshot_dict.get("attribution", {}) if snapshot_dict else {}

    dataset = (
        raw_attr.get("dataset")
        or (catalog_entry.attribution.dataset if catalog_entry else source_id.upper())
    )
    url = (
        raw_attr.get("url")
        or (catalog_entry.attribution.url if catalog_entry else "https://earthdata.nasa.gov/")
    )
    doi = raw_attr.get("doi") if "doi" in raw_attr else (catalog_entry.attribution.doi if catalog_entry else None)
    base_notice = (
        raw_attr.get("notice")
        if "notice" in raw_attr
        else (catalog_entry.attribution.notice if catalog_entry else None)
    )

    combined_notice: str | None = None
    if base_notice and notice_suffix:
        combined_notice = f"{base_notice} {notice_suffix}".strip()
    elif base_notice:
        combined_notice = str(base_notice).strip()
    elif notice_suffix:
        combined_notice = str(notice_suffix).strip()

    return SourceAttribution(
        source=source_id,
        dataset=str(dataset),
        nasa=True,
        url=str(url),
        doi=str(doi) if doi else None,
        notice=combined_notice,
    )


def to_bare_soil_window_responses(windows: Sequence[BareSoilWindow]) -> list[BareSoilWindowResponse]:
    """Convert BareSoilWindow domain dataclasses to BareSoilWindowResponse models."""
    return [
        BareSoilWindowResponse(
            start=w.start,
            end=w.end,
            ndvi_mean=w.ndvi_mean,
            description=w.description,
        )
        for w in windows
    ]


def to_source_attribution_responses(sources: Sequence[SourceAttribution]) -> list[SourceAttributionResponse]:
    """Convert SourceAttribution domain dataclasses to SourceAttributionResponse models."""
    return [
        SourceAttributionResponse(
            source=s.source,
            dataset=s.dataset,
            nasa=s.nasa,
            url=s.url,
            doi=s.doi,
            notice=s.notice,
        )
        for s in sources
    ]


# ---------------------------------------------------------------------------
# Summary Metric Computation Helpers
# ---------------------------------------------------------------------------


def _collect_non_null_values(
    points: list[SeriesPoint] | list[dict[str, Any]],
    var_names: tuple[str, ...],
) -> list[float]:
    """Extract non-null float values from series points matching any of the candidate variable names."""
    result: list[float] = []
    for p in points:
        vals = p.values if isinstance(p, SeriesPoint) else p.get("values", {})
        for name in var_names:
            if name in vals and vals[name] is not None:
                try:
                    result.append(float(vals[name]))
                    break
                except (ValueError, TypeError):
                    pass
    return result


def _extract_dated_values(
    points: Sequence[SeriesPoint | dict[str, Any]],
    var_names: tuple[str, ...],
) -> dict[str, float]:
    """Map each ISO date string (time) to its non-null finite float value matching var_names."""
    result: dict[str, float] = {}
    for p in points:
        t = p.time if isinstance(p, SeriesPoint) else p.get("time")
        if not t or not isinstance(t, str):
            continue
        vals = p.values if isinstance(p, SeriesPoint) else p.get("values", {})
        if not isinstance(vals, dict):
            continue
        for name in var_names:
            if name in vals and vals[name] is not None:
                try:
                    val = float(vals[name])
                    if math.isfinite(val):
                        result[t] = val
                        break
                except (ValueError, TypeError):
                    pass
    return result


def _calendar_dates_between(start_str: str, end_str: str) -> list[str]:
    """Return all inclusive ISO calendar date strings between start_str and end_str."""
    try:
        start_d = date.fromisoformat(start_str)
        end_d = date.fromisoformat(end_str)
    except (ValueError, TypeError):
        return []
    if start_d > end_d:
        return []
    dates: list[str] = []
    curr = start_d
    one_day = timedelta(days=1)
    while curr <= end_d:
        dates.append(curr.isoformat())
        curr += one_day
    return dates


def _build_domain_coverage(
    source_name: str,
    source_period: dict[str, str] | None,
    val_map: dict[str, float],
    overlap_dates: list[str],
) -> DomainCoverage:
    """Build DomainCoverage statistics for a single domain."""
    if not source_period or not source_period.get("start") or not source_period.get("end"):
        return DomainCoverage(
            source=source_name,
            period=None,
            expected_days=0,
            observed_days=0,
            paired_days=0,
            missing_days=0,
            complete=False,
        )
    own_dates = _calendar_dates_between(source_period["start"], source_period["end"])
    expected_days = len(own_dates)
    observed_days = len(val_map)
    paired_days = len([d for d in overlap_dates if d in val_map])
    missing_days = max(0, expected_days - observed_days)
    complete = (expected_days > 0 and observed_days >= expected_days)
    return DomainCoverage(
        source=source_name,
        period=PeriodSchema(start=source_period["start"], end=source_period["end"]),
        expected_days=expected_days,
        observed_days=observed_days,
        paired_days=paired_days,
        missing_days=missing_days,
        complete=complete,
    )


def _compute_summary_metrics(
    matched_id: str,
    rain_series: SeriesData,
    temperature_series: SeriesData,
    et0_series: SeriesData,
    water_balance_series: SeriesData,
    soil_moisture_series: SeriesData,
    gldas_series: SeriesData | None,
    ndvi_series: SeriesData | None,
    terrain_static: StaticDataResponse,
    power_data: dict[str, Any],
    imerg_data: dict[str, Any],
    smap_data: dict[str, Any],
    power_pt: list[dict[str, Any]] | None,
    imerg_pt: list[dict[str, Any]] | None,
    smap_pt: list[dict[str, Any]] | None,
    gldas_pt: list[dict[str, Any]] | None = None,
    ndvi_pt: list[dict[str, Any]] | None = None,
) -> tuple[str, str, dict[str, float | None], DiagnosisCoverage, dict[str, str]]:
    """Compute period_start, period_end, summary scalar indicators, coverage disclosure, and notices."""
    rain_period = (
        imerg_data.get("period")
        if (imerg_pt is not None and imerg_data.get("period") and imerg_data["period"].get("start") and imerg_data["period"].get("end"))
        else None
    )
    power_period = (
        power_data.get("period")
        if (power_pt is not None and power_data.get("period") and power_data["period"].get("start") and power_data["period"].get("end"))
        else None
    )
    smap_period = (
        smap_data.get("period")
        if (smap_pt is not None and smap_data.get("period") and smap_data["period"].get("start") and smap_data["period"].get("end"))
        else None
    )

    power_var_names = {v.get("name") for v in power_data.get("variables", []) if isinstance(v, dict)}
    et0_declared = bool(power_var_names & {"ET0_FAO56", "et0", "ET0"})

    rain_map = (
        _extract_dated_values(rain_series.points.get(matched_id, []), ("precipitation", "precipitation_mm"))
        if imerg_pt is not None
        else {}
    )
    temp_map = (
        _extract_dated_values(temperature_series.points.get(matched_id, []), ("T2M",))
        if power_pt is not None
        else {}
    )
    temp_max_map = (
        _extract_dated_values(temperature_series.points.get(matched_id, []), ("T2M_MAX",))
        if power_pt is not None
        else {}
    )
    et0_map = (
        _extract_dated_values(et0_series.points.get(matched_id, []), ("ET0_FAO56", "et0", "ET0"))
        if (power_pt is not None and et0_declared)
        else {}
    )
    smap_map = (
        _extract_dated_values(soil_moisture_series.points.get(matched_id, []), ("soil_moisture", "sm_surface"))
        if smap_pt is not None
        else {}
    )

    if (
        rain_period
        and power_period
        and rain_period.get("start")
        and power_period.get("start")
        and rain_period.get("end")
        and power_period.get("end")
    ):
        overlap_start = max(rain_period["start"], power_period["start"])
        overlap_end = min(rain_period["end"], power_period["end"])
        periods_overlap = overlap_start <= overlap_end
    else:
        overlap_start = None
        overlap_end = None
        periods_overlap = False

    if periods_overlap and overlap_start and overlap_end:
        overlap_calendar = _calendar_dates_between(overlap_start, overlap_end)
        expected_days = len(overlap_calendar)
        if et0_declared:
            paired_dates = [d for d in overlap_calendar if d in rain_map and d in temp_map and d in et0_map]
        else:
            paired_dates = [d for d in overlap_calendar if d in rain_map and d in temp_map]
        paired_days = len(paired_dates)
        missing_dates = [d for d in overlap_calendar if d not in set(paired_dates)]
        missing_days = len(missing_dates)
    else:
        overlap_calendar = []
        expected_days = 0
        paired_dates = []
        paired_days = 0
        missing_dates = []
        missing_days = 0

    if (not periods_overlap) or paired_days == 0:
        aligned = False
        complete = False
        rain_total = None
        rain_mean = None
        et0_mean = None
        water_balance = None
        temp_mean = None
        temp_max = None
        sm_surface = None

        active_periods = [
            p for p in (power_period, rain_period, smap_period)
            if p and p.get("start") and p.get("end")
        ]
        if active_periods:
            best_period = max(active_periods, key=lambda p: (str(p.get("end")), str(p.get("start"))))
            period_start = str(best_period["start"])
            period_end = str(best_period["end"])
        else:
            period_start = "2026-01-01"
            period_end = "2026-01-01"
        if period_start > period_end:
            period_end = period_start

        cov_period_start = overlap_start if periods_overlap else None
        cov_period_end = overlap_end if periods_overlap else None
    else:
        aligned = True
        period_start = overlap_start  # type: ignore[assignment]
        period_end = overlap_end  # type: ignore[assignment]
        sources_same_period = (
            rain_period is not None
            and power_period is not None
            and rain_period.get("start") == overlap_start
            and rain_period.get("end") == overlap_end
            and power_period.get("start") == overlap_start
            and power_period.get("end") == overlap_end
        )
        complete = (missing_days == 0) and sources_same_period

        rain_vals = [rain_map[d] for d in paired_dates]
        rain_total = round(sum(rain_vals), 2)
        rain_mean = round(sum(rain_vals) / paired_days, 2)

        temp_vals = [temp_map[d] for d in paired_dates]
        temp_mean = round(sum(temp_vals) / paired_days, 2)

        tmax_vals = [temp_max_map[d] for d in paired_dates if d in temp_max_map]
        temp_max = round(max(tmax_vals), 2) if tmax_vals else None

        if et0_declared:
            et0_vals = [et0_map[d] for d in paired_dates]
            et0_mean = round(sum(et0_vals) / paired_days, 2)
            water_balance = round(sum(rain_map[d] - et0_map[d] for d in paired_dates), 2)
        else:
            et0_mean = None
            water_balance = None

        aligned_smap = [smap_map[d] for d in overlap_calendar if d in smap_map]
        sm_surface = round(sum(aligned_smap) / len(aligned_smap), 3) if aligned_smap else None

        cov_period_start = overlap_start
        cov_period_end = overlap_end

    sm_root: float | None = None
    if gldas_series is not None and gldas_pt is not None:
        gl_pts = gldas_series.points.get(matched_id, [])
        root_vals = _collect_non_null_values(
            gl_pts,
            ("SoilMoi10_40cm_inst", "RootMoist_inst", "GWETROOT", "SoilMoi0_10cm_inst"),
        )
        if root_vals:
            sm_root = round(sum(root_vals) / len(root_vals), 2)

    ndvi_mean: float | None = None
    if ndvi_series is not None and ndvi_pt is not None:
        nv_pts = ndvi_series.points.get(matched_id, [])
        nv_vals = _collect_non_null_values(nv_pts, ("NDVI", "ndvi"))
        if nv_vals:
            ndvi_mean = round(sum(nv_vals) / len(nv_vals), 3)

    terrain_pts = terrain_static.points.get(matched_id, {})
    elevation_m = terrain_pts.get("elevation_m")
    slope_mean_pct = terrain_pts.get("slope_mean_pct")

    domains: dict[str, DomainCoverage] = {
        "rain": _build_domain_coverage("imerg", rain_period, rain_map, overlap_calendar),
        "temperature": _build_domain_coverage("power", power_period, temp_map, overlap_calendar),
        "soil_moisture": _build_domain_coverage("smap", smap_period, smap_map, overlap_calendar),
    }
    if et0_declared:
        domains["et0"] = _build_domain_coverage("power", power_period, et0_map, overlap_calendar)
        wb_map = {d: rain_map[d] - et0_map[d] for d in rain_map if d in et0_map}
        domains["water_balance"] = _build_domain_coverage("power", power_period, wb_map, overlap_calendar)

    coverage_model = DiagnosisCoverage(
        period_start=cov_period_start,
        period_end=cov_period_end,
        aligned=aligned,
        complete=complete,
        expected_days=expected_days,
        paired_days=paired_days,
        missing_days=missing_days,
        missing_dates=missing_dates,
        domains=domains,
    )

    coverage_notice_by_source: dict[str, str] = {}
    if not aligned:
        disjoint_msg = (
            "Disjoint or unpaired daily source periods; summary aggregates kept unknown (null)."
        )
        for s in ("imerg", "power", "smap"):
            coverage_notice_by_source[s] = disjoint_msg
    elif not complete:
        partial_msg = (
            f"Aligned summary period {period_start}..{period_end}: "
            f"{paired_days}/{expected_days} paired days ({missing_days} missing)."
        )
        for s in ("imerg", "power", "smap"):
            coverage_notice_by_source[s] = partial_msg

    scalars = {
        "rain_total_mm": rain_total,
        "rain_daily_mean_mm": rain_mean,
        "et0_daily_mean_mm": et0_mean,
        "water_balance_mm": water_balance,
        "soil_moisture_surface_m3m3": sm_surface,
        "soil_moisture_root_kgm2": sm_root,
        "temperature_mean_c": temp_mean,
        "temperature_max_c": temp_max,
        "ndvi_mean": ndvi_mean,
        "elevation_m": elevation_m,
        "slope_mean_pct": slope_mean_pct,
    }

    return period_start, period_end, scalars, coverage_model, coverage_notice_by_source


# ---------------------------------------------------------------------------
# Core Service Orchestrator
# ---------------------------------------------------------------------------


def _load_and_process_diagnosis(
    lat: float,
    lon: float,
    radius_km: float = 5.0,
    data_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Execute validation, snapshot reading, spatial matching, and domain slicing."""
    _validate_diagnosis_params(lat, lon, radius_km)

    resolved_dir = resolve_data_dir(data_dir)
    sergipe_dir = resolved_dir / "sergipe"
    if not sergipe_dir.is_dir():
        raise APIError(
            status_code=503,
            code="server_not_configured",
            message=f"Snapshot directory not found: {sergipe_dir}",
        )

    # Core required snapshot files
    power_data = load_json_snapshot(sergipe_dir / "power.json")
    imerg_data = load_json_snapshot(sergipe_dir / "imerg.json")
    smap_data = load_json_snapshot(sergipe_dir / "smap.json")
    srtm_data = load_json_snapshot(sergipe_dir / "srtm.json")

    # Optional snapshot files loaded with unified helper
    gldas_data = _load_optional_snapshot(sergipe_dir / "gldas.json")
    viirs_data = _load_optional_snapshot(sergipe_dir / "viirs.json")
    modis_data = _load_optional_snapshot(sergipe_dir / "modis.json")

    # Spatial matching
    grid_pts, pilots_list = load_points_and_pilots(sergipe_dir)
    available_ids = set(power_data.get("points", {}).keys())
    matched_point = find_matched_point(
        lat,
        lon,
        grid_pts,
        pilots_list,
        available_ids,
        radius_km=radius_km,
    )
    matched_id = matched_point["id"]

    # Extract point data
    imerg_pt = extract_point_data_for_source(imerg_data, matched_point, grid_pts)
    smap_pt = extract_point_data_for_source(smap_data, matched_point, grid_pts)
    power_pt = extract_point_data_for_source(power_data, matched_point, grid_pts)
    srtm_pt = extract_point_data_for_source(srtm_data, matched_point, grid_pts)

    ndvi_data, ndvi_pt, ndvi_source = _resolve_ndvi_source(
        viirs_data, modis_data, matched_point, grid_pts
    )
    gldas_pt = (
        extract_point_data_for_source(gldas_data, matched_point, grid_pts)
        if gldas_data is not None
        else None
    )

    if imerg_pt is None and smap_pt is None and power_pt is None and srtm_pt is None:
        raise APIError(
            status_code=422,
            code="no_data",
            message=f"No snapshot data available for matched point '{matched_id}'.",
        )

    # Domain series slices
    rain_series = slice_series(
        imerg_data,
        matched_id,
        imerg_pt,
        {"precipitation", "precipitation_mm"},
        daily=True,
    )
    soil_moisture_series = slice_series(
        smap_data,
        matched_id,
        smap_pt,
        {"soil_moisture", "sm_surface"},
        daily=True,
    )
    temperature_series = slice_series(
        power_data,
        matched_id,
        power_pt,
        {"T2M", "T2M_MIN", "T2M_MAX"},
        daily=True,
    )
    et0_series = slice_series(
        power_data,
        matched_id,
        power_pt,
        {"ET0_FAO56"},
        daily=True,
        fallback_variables=[
            VariableSchema(
                name="ET0_FAO56",
                long_name="Reference evapotranspiration, FAO-56 Penman-Monteith (derived from POWER)",
                unit="mm/day",
            )
        ],
    )
    water_balance_series = slice_series(
        power_data,
        matched_id,
        power_pt,
        {"WATER_BALANCE"},
        daily=True,
        fallback_variables=[
            VariableSchema(
                name="WATER_BALANCE",
                long_name="Precipitation minus ET0 (derived from POWER)",
                unit="mm/day",
            )
        ],
    )
    terrain_static = slice_static(srtm_data, matched_id, srtm_pt)

    ndvi_series = (
        slice_series(ndvi_data, matched_id, ndvi_pt, {"NDVI", "ndvi"}, daily=False)
        if ndvi_data is not None
        else None
    )
    gldas_series = (
        slice_series(
            gldas_data,
            matched_id,
            gldas_pt,
            {"SoilMoi0_10cm_inst", "SoilMoi10_40cm_inst", "Rainf_f_tavg"},
            daily=False,
        )
        if gldas_data is not None
        else None
    )

    # Bare soil windows detection
    bare_soil_threshold = get_bare_soil_threshold()
    bare_windows = compute_bare_soil_windows(
        ndvi_pt,
        period_end=ndvi_data.get("period", {}).get("end") if ndvi_data else None,
        threshold=bare_soil_threshold,
    )

    # Summary metrics
    (
        period_start,
        period_end,
        scalars,
        coverage_model,
        coverage_notice_by_source,
    ) = _compute_summary_metrics(
        matched_id=matched_id,
        rain_series=rain_series,
        temperature_series=temperature_series,
        et0_series=et0_series,
        water_balance_series=water_balance_series,
        soil_moisture_series=soil_moisture_series,
        gldas_series=gldas_series,
        ndvi_series=ndvi_series,
        terrain_static=terrain_static,
        power_data=power_data,
        imerg_data=imerg_data,
        smap_data=smap_data,
        power_pt=power_pt,
        imerg_pt=imerg_pt,
        smap_pt=smap_pt,
        gldas_pt=gldas_pt,
        ndvi_pt=ndvi_pt,
    )

    # Source Attributions
    source_attributions: list[SourceAttribution] = [
        build_source_attribution("imerg", imerg_data, coverage_notice_by_source.get("imerg")),
        build_source_attribution("smap", smap_data, coverage_notice_by_source.get("smap")),
        build_source_attribution("power", power_data, coverage_notice_by_source.get("power")),
        build_source_attribution("srtm", srtm_data, coverage_notice_by_source.get("srtm")),
    ]
    if ndvi_data is not None and ndvi_source is not None:
        source_attributions.append(build_source_attribution(ndvi_source, ndvi_data, coverage_notice_by_source.get(ndvi_source)))
    if gldas_data is not None:
        source_attributions.append(build_source_attribution("gldas", gldas_data, coverage_notice_by_source.get("gldas")))

    domain_sources: dict[str, DomainSourceSpec] = {
        "rain": DomainSourceSpec(source="imerg", nasa=True),
        "soil_moisture": DomainSourceSpec(source="smap", nasa=True),
        "temperature": DomainSourceSpec(source="power", nasa=True),
        "et0": DomainSourceSpec(source="power", nasa=True),
        "water_balance": DomainSourceSpec(source="power", nasa=True),
        "terrain": DomainSourceSpec(source="srtm", nasa=True),
    }
    if ndvi_series is not None and ndvi_source is not None:
        domain_sources["ndvi"] = DomainSourceSpec(source=ndvi_source, nasa=True)
    if gldas_series is not None:
        domain_sources["gldas"] = DomainSourceSpec(source="gldas", nasa=True)

    # Common response representations
    bare_windows_responses = to_bare_soil_window_responses(bare_windows)
    source_attribution_responses = to_source_attribution_responses(source_attributions)

    code = municipality_code(lat, lon)

    plot_model = DiagnosisPlot(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        region="sergipe",
        matched_point=MatchedPoint(
            id=matched_point["id"],
            name=matched_point["name"],
            kind=matched_point["kind"],
            lat=matched_point["lat"],
            lon=matched_point["lon"],
            distance_km=matched_point["distance_km"],
        ),
        id=matched_point["id"],
        name=matched_point["name"],
        municipality_code=code,
        elevation_m=scalars["elevation_m"],
        slope_mean_pct=scalars["slope_mean_pct"],
    )

    engine_plot = Plot(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        id=matched_point["id"],
        name=matched_point["name"],
        region="sergipe",
        municipality_code=code,
        elevation_m=scalars["elevation_m"],
        slope_mean_pct=scalars["slope_mean_pct"],
    )

    engine_diagnosis = Diagnosis(
        period_start=period_start,
        period_end=period_end,
        rain_total_mm=scalars["rain_total_mm"],
        rain_daily_mean_mm=scalars["rain_daily_mean_mm"],
        et0_daily_mean_mm=scalars["et0_daily_mean_mm"],
        water_balance_mm=scalars["water_balance_mm"],
        soil_moisture_surface_m3m3=scalars["soil_moisture_surface_m3m3"],
        soil_moisture_root_kgm2=scalars["soil_moisture_root_kgm2"],
        temperature_mean_c=scalars["temperature_mean_c"],
        temperature_max_c=scalars["temperature_max_c"],
        ndvi_mean=scalars["ndvi_mean"],
        elevation_m=scalars["elevation_m"],
        slope_mean_pct=scalars["slope_mean_pct"],
        bare_soil_windows=tuple(bare_windows),
        sources=tuple(source_attributions),
    )

    summary_model = DiagnosisSummary(
        period_start=period_start,
        period_end=period_end,
        rain_total_mm=scalars["rain_total_mm"],
        rain_daily_mean_mm=scalars["rain_daily_mean_mm"],
        et0_daily_mean_mm=scalars["et0_daily_mean_mm"],
        water_balance_mm=scalars["water_balance_mm"],
        soil_moisture_surface_m3m3=scalars["soil_moisture_surface_m3m3"],
        soil_moisture_root_kgm2=scalars["soil_moisture_root_kgm2"],
        temperature_mean_c=scalars["temperature_mean_c"],
        temperature_max_c=scalars["temperature_max_c"],
        ndvi_mean=scalars["ndvi_mean"],
        elevation_m=scalars["elevation_m"],
        slope_mean_pct=scalars["slope_mean_pct"],
        bare_soil_windows=bare_windows_responses,
        sources=source_attribution_responses,
    )

    return {
        "plot_model": plot_model,
        "rain": rain_series,
        "soil_moisture": soil_moisture_series,
        "gldas": gldas_series,
        "temperature": temperature_series,
        "ndvi": ndvi_series,
        "et0": et0_series,
        "water_balance": water_balance_series,
        "terrain": terrain_static,
        "bare_windows": bare_windows,
        "bare_windows_responses": bare_windows_responses,
        "summary_model": summary_model,
        "coverage": coverage_model,
        "source_attributions": source_attributions,
        "source_attribution_responses": source_attribution_responses,
        "domain_sources": domain_sources,
        "engine_plot": engine_plot,
        "engine_diagnosis": engine_diagnosis,
    }


def build_engine_diagnosis(
    lat: float,
    lon: float,
    radius_km: float = 5.0,
    data_dir: Path | str | None = None,
) -> tuple[Plot, Diagnosis]:
    """Build src.engine.model.Plot and src.engine.model.Diagnosis for recommendation pipeline."""
    result = _load_and_process_diagnosis(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        data_dir=data_dir,
    )
    return result["engine_plot"], result["engine_diagnosis"]


def build_diagnosis_response(
    lat: float,
    lon: float,
    radius_km: float = 5.0,
    data_dir: Path | str | None = None,
) -> DiagnosisResponse:
    """Build the complete DiagnosisResponse for GET /diagnosis."""
    result = _load_and_process_diagnosis(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        data_dir=data_dir,
    )
    return DiagnosisResponse(
        plot=result["plot_model"],
        rain=result["rain"],
        soil_moisture=result["soil_moisture"],
        gldas=result["gldas"],
        temperature=result["temperature"],
        ndvi=result["ndvi"],
        et0=result["et0"],
        water_balance=result["water_balance"],
        terrain=result["terrain"],
        bare_soil_windows=result["bare_windows_responses"],
        summary=result["summary_model"],
        coverage=result["coverage"],
        sources=result["source_attribution_responses"],
        domain_sources=result["domain_sources"],
    )
