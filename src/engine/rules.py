# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Agronomic crop profiles, rule thresholds, and pure YAML validation for Field Shift."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

import yaml

from src.engine.model import Crop, Priority

DEFAULT_RULES_DIR = Path(__file__).resolve().parent / "rules"
_SUPPORTED_SCHEMA_VERSION = 1
_WEIGHT_SUM_TOLERANCE = 1e-6


# ---------------------------------------------------------------------------
# 1. Rule & profile dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WaterNeedRule:
    """Seasonal crop water requirement bounds (mm) with citation."""

    min_mm: float
    max_mm: float
    typical_mm: float
    source: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class CycleLengthRule:
    """Crop cycle duration bounds (days) with citation."""

    min_days: int
    max_days: int
    typical_days: int
    source: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class HeatLimitRule:
    """Crop thermal stress thresholds (Celsius) and sensitive phenological stage."""

    max_optimal_c: float
    critical_c: float
    sensitive_stage: str
    source: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class KcProfile:
    """FAO-56 single crop coefficient curve parameters."""

    kc_ini: float
    kc_mid: float
    kc_end: float
    source: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class PlantingCalendarRule:
    """Preferred planting window by month, decendio (1-36), and rainfall onset."""

    preferred_season: str
    start_month: int
    end_month: int
    start_decendio: int
    end_decendio: int
    min_15d_rain_onset_mm: float
    source: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class CropProfile:
    """Complete validated agronomic profile for a supported v1 crop."""

    crop: Crop
    name: str
    botanical_family: str
    fixes_nitrogen: bool
    soil_cover_rating: str
    water_need: WaterNeedRule
    cycle_length: CycleLengthRule
    heat_limit: HeatLimitRule
    kc: KcProfile
    planting_calendar: PlantingCalendarRule


@dataclass(frozen=True, slots=True)
class WaterBalanceThresholds:
    """Agroclimatic water balance, soil moisture, and 15-day onset rain thresholds."""

    severe_deficit_mm: float
    moderate_deficit_mm: float
    min_smap_surface_m3m3: float
    min_forecast_15d_rain_mm: float
    source: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class VegetationThresholds:
    """NDVI spectral thresholds for bare soil and vegetative cover classes."""

    bare_soil_ndvi_max: float
    sparse_cover_ndvi_max: float
    healthy_cover_ndvi_min: float
    source: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class TerrainThresholds:
    """Slope thresholds (%) for gentle terrain, contour planting, and erosion risk."""

    gentle_slope_max_pct: float
    contour_planting_min_slope_pct: float
    high_erosion_risk_slope_pct: float
    source: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class PriorityWeights:
    """Normalized multi-criteria scoring weights for a farmer priority."""

    water_efficiency: float
    soil_health: float
    erosion_control: float
    income_resilience: float


@dataclass(frozen=True, slots=True)
class RuleThresholds:
    """Validated agroclimatic thresholds and priority scoring weights."""

    water_balance: WaterBalanceThresholds
    vegetation_and_bare_soil: VegetationThresholds
    terrain_and_erosion: TerrainThresholds
    priority_weights: dict[Priority, PriorityWeights]


@dataclass(frozen=True, slots=True)
class EngineRules:
    """Full validated rule set consumed by the deterministic decision engine."""

    crops: dict[Crop, CropProfile]
    thresholds: RuleThresholds


# ---------------------------------------------------------------------------
# 2. Pure validation helpers (no I/O)
# ---------------------------------------------------------------------------


def _require_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be a mapping, got {type(value).__name__}")
    return value


def _require_mapping_field(
    mapping: Mapping[str, Any], key: str, context: str
) -> Mapping[str, Any]:
    if key not in mapping:
        raise ValueError(f"Missing required mapping '{context}.{key}'")
    return _require_mapping(mapping[key], f"{context}.{key}")


def _require_non_empty_str(mapping: Mapping[str, Any], key: str, context: str) -> str:
    if key not in mapping:
        raise ValueError(f"Missing required string '{context}.{key}'")
    value = mapping[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{context}.{key}' must be a non-empty string")
    return value


def _optional_url(mapping: Mapping[str, Any], context: str) -> str | None:
    url = mapping.get("url")
    if url is None:
        return None
    if not isinstance(url, str) or not url.strip():
        raise ValueError(f"'{context}.url' must be a non-empty string or null")
    return url


def _require_bool(mapping: Mapping[str, Any], key: str, context: str) -> bool:
    if key not in mapping:
        raise ValueError(f"Missing required boolean '{context}.{key}'")
    value = mapping[key]
    if not isinstance(value, bool):
        raise ValueError(
            f"'{context}.{key}' must be a boolean, got {type(value).__name__}"
        )
    return value


def _require_int(mapping: Mapping[str, Any], key: str, context: str) -> int:
    if key not in mapping:
        raise ValueError(f"Missing required integer '{context}.{key}'")
    value = mapping[key]
    # bool subclasses int in Python, so reject booleans explicitly
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"'{context}.{key}' must be an integer, got {type(value).__name__}"
        )
    return value


def _require_float(mapping: Mapping[str, Any], key: str, context: str) -> float:
    if key not in mapping:
        raise ValueError(f"Missing required number '{context}.{key}'")
    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"'{context}.{key}' must be a number, got {type(value).__name__}"
        )
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"'{context}.{key}' must be finite, got {value!r}")
    return result


def _validate_schema_version(raw: Mapping[str, Any], context: str) -> None:
    if "schema_version" not in raw:
        return
    version = raw["schema_version"]
    if isinstance(version, bool) or version != _SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"{context}: unsupported schema_version {version!r} "
            f"(expected {_SUPPORTED_SCHEMA_VERSION})"
        )


def _validate_min_typical_max(
    low: float,
    typical: float,
    high: float,
    context: str,
    *,
    min_allowed: float = 0.0,
    strictly_positive: bool = False,
) -> None:
    if strictly_positive and low <= min_allowed:
        raise ValueError(f"{context}: minimum value must be > {min_allowed}, got {low}")
    if not strictly_positive and low < min_allowed:
        raise ValueError(
            f"{context}: minimum value must be >= {min_allowed}, got {low}"
        )
    if not (low <= typical <= high):
        raise ValueError(
            f"{context}: expected min <= typical <= max, got {low} <= {typical} <= {high}"
        )


# ---------------------------------------------------------------------------
# 3. Crop profile parsers (no I/O)
# ---------------------------------------------------------------------------


def _parse_water_need(raw: Mapping[str, Any], context: str) -> WaterNeedRule:
    ctx = f"{context}.water_need_mm"
    data = _require_mapping_field(raw, "water_need_mm", context)
    min_mm = _require_float(data, "min_mm", ctx)
    max_mm = _require_float(data, "max_mm", ctx)
    typical_mm = _require_float(data, "typical_mm", ctx)
    source = _require_non_empty_str(data, "source", ctx)
    url = _optional_url(data, ctx)
    _validate_min_typical_max(min_mm, typical_mm, max_mm, ctx)
    return WaterNeedRule(
        min_mm=min_mm,
        max_mm=max_mm,
        typical_mm=typical_mm,
        source=source,
        url=url,
    )


def _parse_cycle_length(raw: Mapping[str, Any], context: str) -> CycleLengthRule:
    ctx = f"{context}.cycle_length_days"
    data = _require_mapping_field(raw, "cycle_length_days", context)
    min_days = _require_int(data, "min_days", ctx)
    max_days = _require_int(data, "max_days", ctx)
    typical_days = _require_int(data, "typical_days", ctx)
    source = _require_non_empty_str(data, "source", ctx)
    url = _optional_url(data, ctx)
    _validate_min_typical_max(
        min_days, typical_days, max_days, ctx, min_allowed=0, strictly_positive=True
    )
    return CycleLengthRule(
        min_days=min_days,
        max_days=max_days,
        typical_days=typical_days,
        source=source,
        url=url,
    )


def _parse_heat_limit(raw: Mapping[str, Any], context: str) -> HeatLimitRule:
    ctx = f"{context}.heat_limit_c"
    data = _require_mapping_field(raw, "heat_limit_c", context)
    max_optimal_c = _require_float(data, "max_optimal_c", ctx)
    critical_c = _require_float(data, "critical_c", ctx)
    sensitive_stage = _require_non_empty_str(data, "sensitive_stage", ctx)
    source = _require_non_empty_str(data, "source", ctx)
    url = _optional_url(data, ctx)
    if max_optimal_c > critical_c:
        raise ValueError(
            f"{ctx}: expected max_optimal_c <= critical_c, "
            f"got {max_optimal_c} > {critical_c}"
        )
    return HeatLimitRule(
        max_optimal_c=max_optimal_c,
        critical_c=critical_c,
        sensitive_stage=sensitive_stage,
        source=source,
        url=url,
    )


def _parse_kc(raw: Mapping[str, Any], context: str) -> KcProfile:
    ctx = f"{context}.kc"
    data = _require_mapping_field(raw, "kc", context)
    kc_ini = _require_float(data, "kc_ini", ctx)
    kc_mid = _require_float(data, "kc_mid", ctx)
    kc_end = _require_float(data, "kc_end", ctx)
    source = _require_non_empty_str(data, "source", ctx)
    url = _optional_url(data, ctx)
    for field_name, val in (("kc_ini", kc_ini), ("kc_mid", kc_mid), ("kc_end", kc_end)):
        if val < 0.0:
            raise ValueError(f"{ctx}.{field_name} must be >= 0, got {val}")
    return KcProfile(
        kc_ini=kc_ini,
        kc_mid=kc_mid,
        kc_end=kc_end,
        source=source,
        url=url,
    )


def _parse_planting_calendar(
    raw: Mapping[str, Any], context: str
) -> PlantingCalendarRule:
    ctx = f"{context}.planting_calendar"
    data = _require_mapping_field(raw, "planting_calendar", context)
    preferred_season = _require_non_empty_str(data, "preferred_season", ctx)
    start_month = _require_int(data, "start_month", ctx)
    end_month = _require_int(data, "end_month", ctx)
    start_decendio = _require_int(data, "start_decendio", ctx)
    end_decendio = _require_int(data, "end_decendio", ctx)
    min_15d_rain_onset_mm = _require_float(data, "min_15d_rain_onset_mm", ctx)
    source = _require_non_empty_str(data, "source", ctx)
    url = _optional_url(data, ctx)

    for field_name, month in (("start_month", start_month), ("end_month", end_month)):
        if not (1 <= month <= 12):
            raise ValueError(f"{ctx}.{field_name} must be in 1..12, got {month}")
    for field_name, decendio in (
        ("start_decendio", start_decendio),
        ("end_decendio", end_decendio),
    ):
        if not (1 <= decendio <= 36):
            raise ValueError(f"{ctx}.{field_name} must be in 1..36, got {decendio}")
    if min_15d_rain_onset_mm < 0.0:
        raise ValueError(
            f"{ctx}.min_15d_rain_onset_mm must be >= 0, got {min_15d_rain_onset_mm}"
        )

    return PlantingCalendarRule(
        preferred_season=preferred_season,
        start_month=start_month,
        end_month=end_month,
        start_decendio=start_decendio,
        end_decendio=end_decendio,
        min_15d_rain_onset_mm=min_15d_rain_onset_mm,
        source=source,
        url=url,
    )


def _parse_crop_profile(crop: Crop, raw: Mapping[str, Any]) -> CropProfile:
    ctx = f"crops.{crop.value}"
    entry = _require_mapping(raw, ctx)
    if "id" in entry:
        crop_id = _require_non_empty_str(entry, "id", ctx)
        if crop_id != crop.value:
            raise ValueError(
                f"{ctx}.id must match crop key {crop.value!r}, got {crop_id!r}"
            )
    return CropProfile(
        crop=crop,
        name=_require_non_empty_str(entry, "name", ctx),
        botanical_family=_require_non_empty_str(entry, "botanical_family", ctx),
        fixes_nitrogen=_require_bool(entry, "fixes_nitrogen", ctx),
        soil_cover_rating=_require_non_empty_str(entry, "soil_cover_rating", ctx),
        water_need=_parse_water_need(entry, ctx),
        cycle_length=_parse_cycle_length(entry, ctx),
        heat_limit=_parse_heat_limit(entry, ctx),
        kc=_parse_kc(entry, ctx),
        planting_calendar=_parse_planting_calendar(entry, ctx),
    )


def parse_crop_profiles(raw: Mapping[str, Any]) -> dict[Crop, CropProfile]:
    """Validate and parse a crop-profiles mapping into typed CropProfile instances."""
    root = _require_mapping(raw, "crops rules")
    _validate_schema_version(root, "crops rules")

    if "crops" not in root:
        raise ValueError("Missing required top-level mapping 'crops'")
    crops_map = _require_mapping(root["crops"], "crops")

    expected_keys = {crop.value for crop in Crop}
    missing = [crop.value for crop in Crop if crop.value not in crops_map]
    if missing:
        raise ValueError(f"Missing required crop profile(s): {', '.join(missing)}")
    extra = [key for key in crops_map if key not in expected_keys]
    if extra:
        raise ValueError(
            f"Unknown crop profile(s): {', '.join(str(k) for k in extra)}"
        )

    return {crop: _parse_crop_profile(crop, crops_map[crop.value]) for crop in Crop}


# ---------------------------------------------------------------------------
# 4. Threshold parsers (no I/O)
# ---------------------------------------------------------------------------


def _parse_water_balance(raw: Mapping[str, Any]) -> WaterBalanceThresholds:
    ctx = "water_balance"
    data = _require_mapping_field(raw, "water_balance", "thresholds")
    severe_deficit_mm = _require_float(data, "severe_deficit_mm", ctx)
    moderate_deficit_mm = _require_float(data, "moderate_deficit_mm", ctx)
    min_smap_surface_m3m3 = _require_float(data, "min_smap_surface_m3m3", ctx)
    min_forecast_15d_rain_mm = _require_float(data, "min_forecast_15d_rain_mm", ctx)
    source = _require_non_empty_str(data, "source", ctx)
    url = _optional_url(data, ctx)

    if severe_deficit_mm > moderate_deficit_mm:
        raise ValueError(
            f"{ctx}: expected severe_deficit_mm <= moderate_deficit_mm, "
            f"got {severe_deficit_mm} > {moderate_deficit_mm}"
        )
    if not (0.0 <= min_smap_surface_m3m3 <= 1.0):
        raise ValueError(
            f"{ctx}.min_smap_surface_m3m3 must be in [0.0, 1.0], "
            f"got {min_smap_surface_m3m3}"
        )
    if min_forecast_15d_rain_mm < 0.0:
        raise ValueError(
            f"{ctx}.min_forecast_15d_rain_mm must be >= 0, "
            f"got {min_forecast_15d_rain_mm}"
        )

    return WaterBalanceThresholds(
        severe_deficit_mm=severe_deficit_mm,
        moderate_deficit_mm=moderate_deficit_mm,
        min_smap_surface_m3m3=min_smap_surface_m3m3,
        min_forecast_15d_rain_mm=min_forecast_15d_rain_mm,
        source=source,
        url=url,
    )


def _parse_vegetation(raw: Mapping[str, Any]) -> VegetationThresholds:
    ctx = "vegetation_and_bare_soil"
    data = _require_mapping_field(raw, "vegetation_and_bare_soil", "thresholds")
    bare_soil_ndvi_max = _require_float(data, "bare_soil_ndvi_max", ctx)
    sparse_cover_ndvi_max = _require_float(data, "sparse_cover_ndvi_max", ctx)
    healthy_cover_ndvi_min = _require_float(data, "healthy_cover_ndvi_min", ctx)
    source = _require_non_empty_str(data, "source", ctx)
    url = _optional_url(data, ctx)

    if not (
        -1.0
        <= bare_soil_ndvi_max
        <= sparse_cover_ndvi_max
        <= healthy_cover_ndvi_min
        <= 1.0
    ):
        raise ValueError(
            f"{ctx}: expected -1.0 <= bare_soil_ndvi_max <= sparse_cover_ndvi_max "
            f"<= healthy_cover_ndvi_min <= 1.0, got {bare_soil_ndvi_max}, "
            f"{sparse_cover_ndvi_max}, {healthy_cover_ndvi_min}"
        )

    return VegetationThresholds(
        bare_soil_ndvi_max=bare_soil_ndvi_max,
        sparse_cover_ndvi_max=sparse_cover_ndvi_max,
        healthy_cover_ndvi_min=healthy_cover_ndvi_min,
        source=source,
        url=url,
    )


def _parse_terrain(raw: Mapping[str, Any]) -> TerrainThresholds:
    ctx = "terrain_and_erosion"
    data = _require_mapping_field(raw, "terrain_and_erosion", "thresholds")
    gentle_slope_max_pct = _require_float(data, "gentle_slope_max_pct", ctx)
    contour_planting_min_slope_pct = _require_float(
        data, "contour_planting_min_slope_pct", ctx
    )
    high_erosion_risk_slope_pct = _require_float(
        data, "high_erosion_risk_slope_pct", ctx
    )
    source = _require_non_empty_str(data, "source", ctx)
    url = _optional_url(data, ctx)

    if not (
        0.0
        <= gentle_slope_max_pct
        <= contour_planting_min_slope_pct
        <= high_erosion_risk_slope_pct
    ):
        raise ValueError(
            f"{ctx}: expected 0.0 <= gentle_slope_max_pct <= "
            f"contour_planting_min_slope_pct <= high_erosion_risk_slope_pct, got "
            f"{gentle_slope_max_pct}, {contour_planting_min_slope_pct}, "
            f"{high_erosion_risk_slope_pct}"
        )

    return TerrainThresholds(
        gentle_slope_max_pct=gentle_slope_max_pct,
        contour_planting_min_slope_pct=contour_planting_min_slope_pct,
        high_erosion_risk_slope_pct=high_erosion_risk_slope_pct,
        source=source,
        url=url,
    )


def _parse_priority_weights(raw: Mapping[str, Any]) -> dict[Priority, PriorityWeights]:
    pw_map = _require_mapping_field(raw, "priority_weights", "thresholds")

    expected_keys = {priority.value for priority in Priority}
    missing = [priority.value for priority in Priority if priority.value not in pw_map]
    if missing:
        raise ValueError(
            f"Missing required priority_weights entry(ies): {', '.join(missing)}"
        )
    extra = [key for key in pw_map if key not in expected_keys]
    if extra:
        raise ValueError(
            f"Unknown priority_weights entry(ies): {', '.join(str(k) for k in extra)}"
        )

    parsed: dict[Priority, PriorityWeights] = {}
    weight_fields = (
        "water_efficiency",
        "soil_health",
        "erosion_control",
        "income_resilience",
    )
    for priority in Priority:
        ctx = f"priority_weights.{priority.value}"
        entry = _require_mapping(pw_map[priority.value], ctx)
        values = {
            field_name: _require_float(entry, field_name, ctx)
            for field_name in weight_fields
        }
        for field_name, weight in values.items():
            if not (0.0 <= weight <= 1.0):
                raise ValueError(
                    f"{ctx}.{field_name} must be in [0.0, 1.0], got {weight}"
                )
        total = sum(values.values())
        if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
            raise ValueError(
                f"{ctx} weights must sum to 1.0 (tolerance {_WEIGHT_SUM_TOLERANCE}), "
                f"got {total:.8f}"
            )
        parsed[priority] = PriorityWeights(**values)
    return parsed


def parse_thresholds(raw: Mapping[str, Any]) -> RuleThresholds:
    """Validate and parse thresholds and priority weights into RuleThresholds."""
    root = _require_mapping(raw, "thresholds rules")
    _validate_schema_version(root, "thresholds rules")

    return RuleThresholds(
        water_balance=_parse_water_balance(root),
        vegetation_and_bare_soil=_parse_vegetation(root),
        terrain_and_erosion=_parse_terrain(root),
        priority_weights=_parse_priority_weights(root),
    )


def parse_rules(
    crops_raw: Mapping[str, Any], thresholds_raw: Mapping[str, Any]
) -> EngineRules:
    """Validate and combine parsed crop and threshold mappings into EngineRules."""
    return EngineRules(
        crops=parse_crop_profiles(crops_raw),
        thresholds=parse_thresholds(thresholds_raw),
    )


# ---------------------------------------------------------------------------
# 5. YAML file loaders
# ---------------------------------------------------------------------------


def _load_yaml_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Rules YAML file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, Mapping):
        raise ValueError(
            f"Rules YAML file {path} must have a top-level mapping, "
            f"got {type(data).__name__}"
        )
    return data


def load_crop_profiles(path: Path | None = None) -> dict[Crop, CropProfile]:
    """Load and validate crop profiles from YAML (defaults to rules/crops.yaml)."""
    target = Path(path) if path is not None else DEFAULT_RULES_DIR / "crops.yaml"
    return parse_crop_profiles(_load_yaml_mapping(target))


def load_thresholds(path: Path | None = None) -> RuleThresholds:
    """Load and validate rule thresholds from YAML (defaults to rules/thresholds.yaml)."""
    target = Path(path) if path is not None else DEFAULT_RULES_DIR / "thresholds.yaml"
    return parse_thresholds(_load_yaml_mapping(target))


def load_rules(rules_dir: Path | None = None) -> EngineRules:
    """Load and validate both crops.yaml and thresholds.yaml from rules_dir."""
    base_dir = Path(rules_dir) if rules_dir is not None else DEFAULT_RULES_DIR
    return EngineRules(
        crops=load_crop_profiles(base_dir / "crops.yaml"),
        thresholds=load_thresholds(base_dir / "thresholds.yaml"),
    )


__all__ = [
    "DEFAULT_RULES_DIR",
    "CropProfile",
    "CycleLengthRule",
    "EngineRules",
    "HeatLimitRule",
    "KcProfile",
    "PlantingCalendarRule",
    "PriorityWeights",
    "RuleThresholds",
    "TerrainThresholds",
    "VegetationThresholds",
    "WaterBalanceThresholds",
    "WaterNeedRule",
    "load_crop_profiles",
    "load_rules",
    "load_thresholds",
    "parse_crop_profiles",
    "parse_rules",
    "parse_thresholds",
]
