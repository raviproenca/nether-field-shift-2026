# AI-assisted: generated with Cursor; pending review by the team.
"""Strategy generation and ranking for the Field Shift decision engine.

Ranking follows the rule engine described by Kalaivani et al., IEEE CICT 2025,
DOI 10.1109/CICT67193.2025.11399212: do not repeat the previous crop's
botanical family, and after a nitrogen-depleting crop prefer a legume. The
farmer's priority breaks ties only. The logistic-regression model in that
paper is not used.

IEEE holds the copyright. This module cites those two rules and does not
reproduce the paper's text or figures.
"""

from __future__ import annotations

from dataclasses import dataclass

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

@dataclass(frozen=True, slots=True)
class CropRole:
    """Botanical family and nitrogen role for one v1 crop."""

    family: str
    nitrogen: str


# Qualitative metadata kept beside the rules: family and nutrient impact.
CROP_ROLES: dict[Crop, CropRole] = {
    Crop.MAIZE: CropRole("Poaceae", "nitrogen-depleting"),
    Crop.BEANS: CropRole("Fabaceae", "nitrogen-fixing"),
    Crop.CASSAVA: CropRole("Euphorbiaceae", "neither"),
}

_RECOGNIZED_PREVIOUS: dict[str, Crop] = {crop.value: crop for crop in Crop}

_TIE_BREAK: dict[StrategyKind, int] = {
    StrategyKind.SOIL_WATER_CONSERVATION: 2,
    StrategyKind.RESILIENT_INCOME_FORAGE: 1,
    StrategyKind.CURRENT_PRACTICE: 0,
}

_TRADE_OFF: dict[StrategyKind, str] = {
    StrategyKind.CURRENT_PRACTICE: "keeps_current_calendar",
    StrategyKind.SOIL_WATER_CONSERVATION: "favors_cover_and_soil",
    StrategyKind.RESILIENT_INCOME_FORAGE: "favors_forage_or_income",
}

_SOIL_WATER_PRIORITIES = frozenset({Priority.SOIL, Priority.WATER, Priority.EROSION})

_FORECAST_NOT_OBSERVATION = "The forecast is not an observation."
_FORECAST_ABSENT = "The forecast is absent."
_ZARC_NOT_DONE = "The ZARC check is not done yet."


def _recognized_previous(plot: Plot) -> Crop | None:
    """Return the last previous crop when it is maize, beans, or cassava."""
    if not plot.previous_crops:
        return None
    return _RECOGNIZED_PREVIOUS.get(plot.previous_crops[-1])


def _strategy_crops(kind: StrategyKind, crop: Crop) -> tuple[str, ...]:
    """Selected crop, plus the companion defined for that strategy kind."""
    if kind is StrategyKind.CURRENT_PRACTICE:
        return (crop.value,)
    if kind is StrategyKind.SOIL_WATER_CONSERVATION:
        companion = Crop.CASSAVA if crop is Crop.BEANS else Crop.BEANS
    else:
        companion = Crop.CASSAVA if crop is Crop.MAIZE else Crop.MAIZE
    return (crop.value, companion.value)


def _family_break(crops: tuple[str, ...], previous: Crop | None) -> int:
    """1 when the strategy introduces a family other than the previous crop's."""
    if previous is None:
        return 1
    previous_family = CROP_ROLES[previous].family
    introduced = any(CROP_ROLES[Crop(name)].family != previous_family for name in crops)
    return 1 if introduced else 0


def _nutrient_recovery(crops: tuple[str, ...], previous: Crop | None) -> int:
    """1 when a nitrogen-depleting previous crop is followed by beans."""
    if previous is None:
        return 0
    if CROP_ROLES[previous].nitrogen != "nitrogen-depleting":
        return 0
    return 1 if Crop.BEANS.value in crops else 0


def _priority_fit(kind: StrategyKind, priority: Priority) -> int:
    """1 when the strategy matches the farmer's priority. Ties only."""
    if kind is StrategyKind.SOIL_WATER_CONSERVATION and priority in _SOIL_WATER_PRIORITIES:
        return 1
    if kind is StrategyKind.RESILIENT_INCOME_FORAGE and priority == Priority.INCOME:
        return 1
    return 0


def _rank_key(
    kind: StrategyKind,
    crops: tuple[str, ...],
    previous: Crop | None,
    priority: Priority,
) -> tuple[int, int, int, int]:
    return (
        _family_break(crops, previous),
        _nutrient_recovery(crops, previous),
        _priority_fit(kind, priority),
        _TIE_BREAK[kind],
    )


def recommend(
    plot: Plot,
    diagnosis: Diagnosis,
    projection: Projection,
    crop: Crop,
    priority: Priority,
) -> Recommendation:
    """Return the three v1 strategies ordered by the rotation rules.

    The same inputs always produce the same recommendation. This function
    does not read files, the clock, the network, or a trained model.
    """
    previous = _recognized_previous(plot)
    ranked = sorted(
        (
            (kind, _strategy_crops(kind, crop))
            for kind in (
                StrategyKind.CURRENT_PRACTICE,
                StrategyKind.SOIL_WATER_CONSERVATION,
                StrategyKind.RESILIENT_INCOME_FORAGE,
            )
        ),
        key=lambda item: _rank_key(item[0], item[1], previous, priority),
        reverse=True,
    )
    strategies = tuple(
        Strategy(
            kind=kind,
            rank=rank,
            score=float(4 - rank),
            title=kind.value.replace("_", " "),
            crops=crops,
            trade_offs=(_TRADE_OFF[kind],),
            planting_schedule=(),
            water_demand_mm=0.0,
            breaks_pest_cycle=False,
            pest_cycle_note="",
            actions=(),
        )
        for rank, (kind, crops) in enumerate(ranked, start=1)
    )
    uncertainty_note = (
        _FORECAST_NOT_OBSERVATION if projection.available else _FORECAST_ABSENT
    )
    return Recommendation(
        plot=plot,
        crop=crop,
        priority=priority,
        diagnosis=diagnosis,
        projection=projection,
        strategies=strategies,
        uncertainty_note=uncertainty_note,
        validation_note=_ZARC_NOT_DONE,
        sources=diagnosis.sources + projection.sources,
    )
