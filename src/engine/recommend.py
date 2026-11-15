# AI-assisted: generated with Cursor, reviewed by Lucas Feitosa
"""Strategy generation and ranking for the Field Shift decision engine.

Scores use EngineRules loaded by the caller (crops.yaml and thresholds.yaml),
the Diagnosis, the Projection, and the plot region and season. Priority
weights from the rules change the ranking. This function does not read files.

Ranking cites the rotation rules in Kalaivani et al., IEEE CICT 2025,
DOI 10.1109/CICT67193.2025.11399212: do not repeat the previous crop's
botanical family, and after a non-fixing crop prefer a legume. IEEE holds
the copyright. This module does not reproduce the paper's text or figures.
"""

from __future__ import annotations

from src.engine.model import (
    Crop,
    Diagnosis,
    Plot,
    Priority,
    Projection,
    Recommendation,
    Strategy,
    StrategyKind,
)
from src.engine.rules import CropProfile, EngineRules

_COVER = {
    "low_initial": 0.25,
    "low": 0.25,
    "medium": 0.55,
    "medium_high": 0.8,
    "high": 1.0,
}

_INCOME_BASE = {
    StrategyKind.CURRENT_PRACTICE: 0.35,
    StrategyKind.SOIL_WATER_CONSERVATION: 0.45,
    StrategyKind.RESILIENT_INCOME_FORAGE: 0.9,
}

_TIE_BREAK = {
    StrategyKind.SOIL_WATER_CONSERVATION: 2,
    StrategyKind.RESILIENT_INCOME_FORAGE: 1,
    StrategyKind.CURRENT_PRACTICE: 0,
}

_TRADE_OFF = {
    StrategyKind.CURRENT_PRACTICE: "keeps_current_calendar",
    StrategyKind.SOIL_WATER_CONSERVATION: "favors_cover_and_soil",
    StrategyKind.RESILIENT_INCOME_FORAGE: "favors_forage_or_income",
}

_FORECAST_NOT_OBSERVATION = "The forecast is not an observation."
_FORECAST_ABSENT = "The forecast is absent."
_SEVERE_DEFICIT = " Water balance is below the severe deficit threshold."
_ZARC_NOT_DONE = "The ZARC check is not done yet."


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _recognized_previous(plot: Plot, rules: EngineRules) -> CropProfile | None:
    """Last previous crop when it is one of the v1 profiles."""
    if not plot.previous_crops:
        return None
    try:
        crop = Crop(plot.previous_crops[-1])
    except ValueError:
        return None
    return rules.crops.get(crop)


def _strategy_crops(kind: StrategyKind, crop: Crop) -> tuple[Crop, ...]:
    """Selected crop, plus the companion defined for that strategy kind."""
    if kind is StrategyKind.CURRENT_PRACTICE:
        return (crop,)
    if kind is StrategyKind.SOIL_WATER_CONSERVATION:
        companion = Crop.CASSAVA if crop is Crop.BEANS else Crop.BEANS
    else:
        companion = Crop.CASSAVA if crop is Crop.MAIZE else Crop.MAIZE
    return (crop, companion)


def _profiles(crops: tuple[Crop, ...], rules: EngineRules) -> tuple[CropProfile, ...]:
    return tuple(rules.crops[crop] for crop in crops)


def _family_break(profiles: tuple[CropProfile, ...], previous: CropProfile | None) -> bool:
    """True only when every crop in the strategy is outside the previous family.

    A companion does not earn the break while the previous family is still planted.
    """
    if previous is None:
        return True
    return all(profile.botanical_family != previous.botanical_family for profile in profiles)


def _cover(profiles: tuple[CropProfile, ...]) -> float:
    ratings = [_COVER.get(profile.soil_cover_rating, 0.5) for profile in profiles]
    return sum(ratings) / len(ratings)


def _season_fit(plot: Plot, profiles: tuple[CropProfile, ...]) -> float:
    if not plot.season:
        return 0.5
    season = plot.season.casefold()
    matches = [
        profile.planting_calendar.preferred_season.casefold() == season
        for profile in profiles
    ]
    return sum(1.0 if match else 0.0 for match in matches) / len(matches)


def _balance_mm(plot: Plot, diagnosis: Diagnosis, rules: EngineRules) -> float | None:
    if diagnosis.water_balance_mm is not None:
        return diagnosis.water_balance_mm
    region = (plot.region or "").casefold()
    if "semi" in region:
        return rules.thresholds.water_balance.moderate_deficit_mm
    return None


def _water_efficiency(
    plot: Plot,
    diagnosis: Diagnosis,
    projection: Projection,
    profiles: tuple[CropProfile, ...],
    rules: EngineRules,
) -> float:
    thresholds = rules.thresholds.water_balance
    balance = _balance_mm(plot, diagnosis, rules)
    demand = sum(profile.water_need.typical_mm for profile in profiles) / len(profiles)
    max_demand = max(profile.water_need.typical_mm for profile in rules.crops.values())
    demand_ratio = demand / max_demand if max_demand else 1.0
    if balance is None:
        stress = 0.5
    elif balance <= thresholds.severe_deficit_mm:
        stress = 1.0
    elif balance <= thresholds.moderate_deficit_mm:
        stress = 0.6
    else:
        stress = 0.15
    if (
        diagnosis.soil_moisture_surface_m3m3 is not None
        and diagnosis.soil_moisture_surface_m3m3 < thresholds.min_smap_surface_m3m3
    ):
        stress = max(stress, 0.8)
    if (
        balance is None
        and diagnosis.rain_total_mm is not None
        and diagnosis.rain_total_mm < thresholds.min_forecast_15d_rain_mm
    ):
        stress = max(stress, 0.6)
    fit = 1.0 - stress * demand_ratio
    if not projection.available or projection.rain_total_mm is None:
        forecast = 0.0 if not projection.available else 0.5
    else:
        needed = max(
            thresholds.min_forecast_15d_rain_mm,
            max(profile.planting_calendar.min_15d_rain_onset_mm for profile in profiles),
        )
        forecast = 1.0 if projection.rain_total_mm >= needed else 0.25
    return _clamp(0.65 * fit + 0.20 * forecast + 0.15 * _season_fit(plot, profiles))


def _soil_health(
    diagnosis: Diagnosis,
    profiles: tuple[CropProfile, ...],
    previous: CropProfile | None,
    rules: EngineRules,
) -> float:
    introduces_fixer = any(
        profile.fixes_nitrogen
        and (previous is None or profile.botanical_family != previous.botanical_family)
        for profile in profiles
    )
    recovery = 1.0 if previous is not None and not previous.fixes_nitrogen and introduces_fixer else 0.0
    cover = _cover(profiles)
    vegetation = rules.thresholds.vegetation_and_bare_soil
    ndvi = diagnosis.ndvi_mean
    if ndvi is None:
        vegetation_score = 0.5
    elif ndvi <= vegetation.bare_soil_ndvi_max:
        vegetation_score = cover
    elif ndvi >= vegetation.healthy_cover_ndvi_min:
        vegetation_score = 0.7
    else:
        vegetation_score = 0.5 + 0.3 * cover
    family = 1.0 if _family_break(profiles, previous) else 0.0
    return _clamp(0.45 * recovery + 0.25 * cover + 0.20 * vegetation_score + 0.10 * family)


def _erosion_control(
    plot: Plot,
    diagnosis: Diagnosis,
    profiles: tuple[CropProfile, ...],
    rules: EngineRules,
) -> float:
    slope = diagnosis.slope_mean_pct
    if slope is None:
        slope = plot.slope_mean_pct
    if slope is None:
        return 0.5
    cover = _cover(profiles)
    terrain = rules.thresholds.terrain_and_erosion
    if slope >= terrain.high_erosion_risk_slope_pct:
        return cover
    if slope >= terrain.contour_planting_min_slope_pct:
        return _clamp(0.4 + 0.6 * cover)
    return 0.75


def _heat_fit(diagnosis: Diagnosis, profiles: tuple[CropProfile, ...]) -> float:
    temperature = diagnosis.temperature_max_c
    if temperature is None:
        temperature = diagnosis.temperature_mean_c
    if temperature is None:
        return 1.0
    fits: list[float] = []
    for profile in profiles:
        if temperature >= profile.heat_limit.critical_c:
            fits.append(0.0)
        elif temperature >= profile.heat_limit.max_optimal_c:
            fits.append(0.5)
        else:
            fits.append(1.0)
    return min(fits)


def _income_resilience(
    kind: StrategyKind,
    diagnosis: Diagnosis,
    profiles: tuple[CropProfile, ...],
) -> float:
    return _clamp(0.7 * _INCOME_BASE[kind] + 0.3 * _heat_fit(diagnosis, profiles))


def _score(
    kind: StrategyKind,
    plot: Plot,
    diagnosis: Diagnosis,
    projection: Projection,
    profiles: tuple[CropProfile, ...],
    previous: CropProfile | None,
    priority: Priority,
    rules: EngineRules,
) -> float:
    weights = rules.thresholds.priority_weights[priority]
    total = (
        weights.water_efficiency
        * _water_efficiency(plot, diagnosis, projection, profiles, rules)
        + weights.soil_health * _soil_health(diagnosis, profiles, previous, rules)
        + weights.erosion_control * _erosion_control(plot, diagnosis, profiles, rules)
        + weights.income_resilience * _income_resilience(kind, diagnosis, profiles)
    )
    return round(total, 6)


def recommend(
    plot: Plot,
    diagnosis: Diagnosis,
    projection: Projection,
    crop: Crop,
    priority: Priority,
    rules: EngineRules,
) -> Recommendation:
    """Return the three v1 strategies ranked by the weighted rule score.

    The same inputs always produce the same recommendation. The caller loads
    ``rules``; this function does not read files, the clock, or the network.
    """
    previous = _recognized_previous(plot, rules)
    ranked = sorted(
        (
            (
                kind,
                crops,
                _score(
                    kind,
                    plot,
                    diagnosis,
                    projection,
                    _profiles(crops, rules),
                    previous,
                    priority,
                    rules,
                ),
            )
            for kind, crops in (
                (strategy_kind, _strategy_crops(strategy_kind, crop))
                for strategy_kind in (
                    StrategyKind.CURRENT_PRACTICE,
                    StrategyKind.SOIL_WATER_CONSERVATION,
                    StrategyKind.RESILIENT_INCOME_FORAGE,
                )
            )
        ),
        key=lambda item: (item[2], _TIE_BREAK[item[0]]),
        reverse=True,
    )
    strategies = tuple(
        Strategy(
            kind=kind,
            rank=rank,
            score=score,
            title=kind.value.replace("_", " "),
            crops=tuple(item.value for item in crops),
            trade_offs=(_TRADE_OFF[kind],),
            planting_schedule=(),
            water_demand_mm=round(
                sum(rules.crops[item].water_need.typical_mm for item in crops),
                2,
            ),
            breaks_pest_cycle=False,
            pest_cycle_note="",
            actions=(),
        )
        for rank, (kind, crops, score) in enumerate(ranked, start=1)
    )
    balance = diagnosis.water_balance_mm
    severe = rules.thresholds.water_balance.severe_deficit_mm
    uncertainty = _FORECAST_NOT_OBSERVATION if projection.available else _FORECAST_ABSENT
    if balance is not None and balance <= severe:
        uncertainty += _SEVERE_DEFICIT
    return Recommendation(
        plot=plot,
        crop=crop,
        priority=priority,
        diagnosis=diagnosis,
        projection=projection,
        strategies=strategies,
        uncertainty_note=uncertainty,
        validation_note=_ZARC_NOT_DONE,
        sources=diagnosis.sources + projection.sources,
    )
