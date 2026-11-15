# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Domain model types and pure serialization for the Field Shift decision engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import StrEnum
from typing import Any


# ---------------------------------------------------------------------------
# 1.1 Standard enums / identifiers (ARCHITECTURE-SPINE.md)
# ---------------------------------------------------------------------------


class Crop(StrEnum):
    """Supported v1 crops for Sergipe family farming."""

    MAIZE = "maize"
    BEANS = "beans"
    CASSAVA = "cassava"


class Priority(StrEnum):
    """Farmer optimization priority."""

    WATER = "water"
    SOIL = "soil"
    EROSION = "erosion"
    INCOME = "income"


class StrategyKind(StrEnum):
    """Canonical strategy archetypes compared by the engine."""

    CURRENT_PRACTICE = "current_practice"
    SOIL_WATER_CONSERVATION = "soil_water_conservation"
    RESILIENT_INCOME_FORAGE = "resilient_income_forage"


# ---------------------------------------------------------------------------
# 1.2 Plot context & agronomic input types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SoilInfo:
    """Source-agnostic soil characteristics for a plot."""

    texture: str | None = None
    organic_carbon_g_kg: float | None = None
    ph: float | None = None
    water_holding_capacity_mm: float | None = None
    notes: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class Plot:
    """Geographic, terrain, and agronomic context of a farm plot."""

    lat: float
    lon: float
    radius_km: float
    id: str | None = None
    name: str | None = None
    region: str | None = None
    municipality_code: str | None = None
    elevation_m: float | None = None
    slope_mean_deg: float | None = None
    slope_mean_pct: float | None = None
    soil: SoilInfo | None = None
    season: str | None = None
    previous_crops: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Ensure previous_crops is always an immutable tuple even if a list is passed
        if not isinstance(self.previous_crops, tuple):
            object.__setattr__(self, "previous_crops", tuple(self.previous_crops))


# ---------------------------------------------------------------------------
# 1.3 Diagnosis & Projection types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceAttribution:
    """Traceability metadata for NASA and third-party datasets."""

    source: str
    dataset: str
    nasa: bool
    url: str
    doi: str | None = None
    notice: str | None = None


@dataclass(frozen=True, slots=True)
class BareSoilWindow:
    """Detected period of exposed/bare soil from vegetation indices (FR-6)."""

    start: str
    end: str
    ndvi_mean: float | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class Diagnosis:
    """Recent and seasonal agro-climatic summary derived from src/data/."""

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
    bare_soil_windows: tuple[BareSoilWindow, ...] = ()
    sources: tuple[SourceAttribution, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.bare_soil_windows, tuple):
            object.__setattr__(self, "bare_soil_windows", tuple(self.bare_soil_windows))
        if not isinstance(self.sources, tuple):
            object.__setattr__(self, "sources", tuple(self.sources))


@dataclass(frozen=True, slots=True)
class Projection:
    """Short-term weather forecast summary (e.g. 15-day Open-Meteo, nasa=False)."""

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
    sources: tuple[SourceAttribution, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.sources, tuple):
            object.__setattr__(self, "sources", tuple(self.sources))


# ---------------------------------------------------------------------------
# 1.4 Output types: Strategies & Recommendation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Action:
    """Concrete recommended action with a single-line evidence citation (FR-10)."""

    code: str
    summary: str
    timing: str
    evidence: str


@dataclass(frozen=True, slots=True)
class CropSchedule:
    """Planting window, cycle duration, and water demand for a crop in a strategy."""

    crop: str
    planting_start: str
    planting_end: str
    cycle_days: int
    water_demand_mm: float


@dataclass(frozen=True, slots=True)
class Strategy:
    """Ranked crop/rotation strategy with trade-offs, schedule, and actions."""

    kind: StrategyKind
    rank: int
    score: float
    title: str
    crops: tuple[str, ...]
    trade_offs: tuple[str, ...]
    planting_schedule: tuple[CropSchedule, ...]
    water_demand_mm: float
    breaks_pest_cycle: bool
    pest_cycle_note: str
    actions: tuple[Action, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.crops, tuple):
            object.__setattr__(self, "crops", tuple(self.crops))
        if not isinstance(self.trade_offs, tuple):
            object.__setattr__(self, "trade_offs", tuple(self.trade_offs))
        if not isinstance(self.planting_schedule, tuple):
            object.__setattr__(self, "planting_schedule", tuple(self.planting_schedule))
        if not isinstance(self.actions, tuple):
            object.__setattr__(self, "actions", tuple(self.actions))


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Complete deterministic output produced by the decision engine."""

    plot: Plot
    crop: Crop
    priority: Priority
    diagnosis: Diagnosis
    projection: Projection
    strategies: tuple[Strategy, ...]
    uncertainty_note: str
    validation_note: str
    sources: tuple[SourceAttribution, ...] = ()
    schema_version: int = field(default=1, kw_only=False)

    def __post_init__(self) -> None:
        if not isinstance(self.strategies, tuple):
            object.__setattr__(self, "strategies", tuple(self.strategies))
        if not isinstance(self.sources, tuple):
            object.__setattr__(self, "sources", tuple(self.sources))

    def to_dict(self) -> dict[str, Any]:
        """Return a pure JSON-serializable dict with snake_case keys."""
        return serialize_recommendation(self)


# ---------------------------------------------------------------------------
# 1.5 Pure deterministic serialization
# ---------------------------------------------------------------------------


def _to_serializable(obj: Any) -> Any:
    """Recursively convert dataclasses, StrEnums, and tuples into plain JSON types."""
    if isinstance(obj, StrEnum):
        return str(obj.value)
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_serializable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, (tuple, list)):
        return [_to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _to_serializable(v) for k, v in obj.items()}
    return obj


def serialize_recommendation(recommendation: Recommendation) -> dict[str, Any]:
    """Convert a Recommendation into a deterministic, JSON-ready dictionary."""
    result = _to_serializable(recommendation)
    # Put schema_version first for clean, deterministic key ordering
    ordered: dict[str, Any] = {"schema_version": result.pop("schema_version", 1)}
    ordered.update(result)
    return ordered