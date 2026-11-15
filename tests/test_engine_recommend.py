# AI-assisted: generated with Cursor, reviewed by Lucas Feitosa
"""Tests for strategy scoring, ranking, and schema validation."""

from __future__ import annotations

import builtins
import json
import socket
import time
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from src.engine import (
    Crop,
    Diagnosis,
    Plot,
    Priority,
    Projection,
    SourceAttribution,
    StrategyKind,
    load_rules,
    recommend,
    serialize_recommendation,
)

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "data-format"
    / "recommendation.schema.json"
)
RULES = load_rules()

_DIAGNOSIS_SOURCE = SourceAttribution(
    source="power",
    dataset="NASA POWER Agroclimatology Daily v2.x",
    nasa=True,
    url="https://power.larc.nasa.gov/",
)


def get_validator() -> Draft202012Validator:
    """Load recommendation.schema.json and return a Draft 2020-12 validator."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def make_plot(**overrides: object) -> Plot:
    values: dict[str, object] = {
        "lat": -10.685,
        "lon": -37.425,
        "radius_km": 5.0,
        "region": "Agreste",
        "season": "wet",
        "previous_crops": ("maize",),
    }
    values.update(overrides)
    return Plot(**values)  # type: ignore[arg-type]


def make_diagnosis(**overrides: object) -> Diagnosis:
    values: dict[str, object] = {
        "period_start": "2026-10-09",
        "period_end": "2026-11-07",
        "rain_total_mm": 11.68,
        "temperature_mean_c": 28.01,
        "water_balance_mm": -176.85,
        "sources": (_DIAGNOSIS_SOURCE,),
    }
    values.update(overrides)
    return Diagnosis(**values)  # type: ignore[arg-type]


def make_projection(*, available: bool = False, rain_total_mm: float | None = None) -> Projection:
    return Projection(
        period_start="2026-11-08",
        period_end="2026-11-22",
        horizon_days=15,
        available=available,
        rain_total_mm=rain_total_mm,
    )


def kinds_of(recommendation) -> list[str]:
    return [strategy.kind.value for strategy in recommendation.strategies]


def test_water_priority_after_maize_ranks_conservation_first() -> None:
    recommendation = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    assert kinds_of(recommendation)[0] == "soil_water_conservation"
    assert recommendation.strategies[0].crops == ("maize", "beans")
    assert recommendation.strategies[0].water_demand_mm == 950.0
    assert "severe deficit" in recommendation.uncertainty_note


def test_income_priority_after_maize_ranks_resilient_first() -> None:
    recommendation = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.INCOME,
        RULES,
    )
    assert kinds_of(recommendation)[0] == "resilient_income_forage"
    assert recommendation.strategies[0].crops == ("maize", "cassava")


def test_priority_changes_rank_and_score() -> None:
    water = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    income = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.INCOME,
        RULES,
    )
    assert kinds_of(water) != kinds_of(income)
    assert [strategy.score for strategy in water.strategies] != [3.0, 2.0, 1.0]
    assert water.strategies[0].score != income.strategies[0].score


def test_dry_season_lowers_the_water_score() -> None:
    diagnosis = make_diagnosis()
    projection = make_projection()
    wet = recommend(
        make_plot(season="wet"),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    dry = recommend(
        make_plot(season="dry"),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    assert dry.strategies[0].score < wet.strategies[0].score


def test_semiarid_region_changes_the_score_when_balance_is_missing() -> None:
    diagnosis = make_diagnosis(water_balance_mm=None, rain_total_mm=None)
    projection = make_projection()
    semi = recommend(
        make_plot(region="Semiárido", previous_crops=()),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    agreste = recommend(
        make_plot(region="Agreste", previous_crops=()),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    assert semi.strategies[0].score != agreste.strategies[0].score


def test_steep_slope_changes_the_erosion_ranking() -> None:
    projection = make_projection()
    shared = dict(
        water_balance_mm=40.0,
        ndvi_mean=0.7,
        temperature_mean_c=26.0,
        rain_total_mm=80.0,
    )
    steep = recommend(
        make_plot(previous_crops=()),
        make_diagnosis(slope_mean_pct=12.0, **shared),
        projection,
        Crop.MAIZE,
        Priority.EROSION,
        RULES,
    )
    flat = recommend(
        make_plot(previous_crops=()),
        make_diagnosis(slope_mean_pct=1.0, **shared),
        projection,
        Crop.MAIZE,
        Priority.EROSION,
        RULES,
    )
    assert kinds_of(steep)[0] == "soil_water_conservation"
    assert kinds_of(flat)[0] == "resilient_income_forage"


def test_only_the_last_previous_crop_is_recognized() -> None:
    diagnosis = make_diagnosis()
    projection = make_projection()
    maize_last = recommend(
        make_plot(previous_crops=("beans", "maize")),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    maize_only = recommend(
        make_plot(previous_crops=("maize",)),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    unrecognized_last = recommend(
        make_plot(previous_crops=("maize", "rice")),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.INCOME,
        RULES,
    )
    no_previous = recommend(
        make_plot(previous_crops=()),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.INCOME,
        RULES,
    )
    assert kinds_of(maize_last) == kinds_of(maize_only)
    assert kinds_of(unrecognized_last) == kinds_of(no_previous)


def test_forecast_absent_still_returns_a_recommendation() -> None:
    recommendation = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(available=False),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    assert len(recommendation.strategies) == 3
    assert recommendation.uncertainty_note.startswith("The forecast is absent.")
    get_validator().validate(json.loads(json.dumps(serialize_recommendation(recommendation))))


def test_forecast_rain_is_read_when_the_projection_is_available() -> None:
    diagnosis = make_diagnosis(water_balance_mm=10.0)
    dry_forecast = recommend(
        make_plot(previous_crops=()),
        diagnosis,
        make_projection(available=True, rain_total_mm=0.0),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    wet_forecast = recommend(
        make_plot(previous_crops=()),
        diagnosis,
        make_projection(available=True, rain_total_mm=80.0),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    assert wet_forecast.strategies[0].score > dry_forecast.strategies[0].score
    assert wet_forecast.uncertainty_note == "The forecast is not an observation."


def test_repeat_call_serializes_byte_for_byte() -> None:
    args = (
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.INCOME,
        RULES,
    )
    first = json.dumps(serialize_recommendation(recommend(*args)), sort_keys=True).encode()
    second = json.dumps(serialize_recommendation(recommend(*args)), sort_keys=True).encode()
    assert first == second


def test_recommendation_validates_against_the_schema() -> None:
    recommendation = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.SOIL,
        RULES,
    )
    payload = json.loads(json.dumps(serialize_recommendation(recommendation)))
    get_validator().validate(payload)
    assert payload["validation_note"] == "The ZARC check is not done yet."
    assert payload["strategies"][0]["water_demand_mm"] > 0
    for strategy in payload["strategies"]:
        assert strategy["actions"] == []
        assert strategy["planting_schedule"] == []


def test_recommend_does_not_read_a_file_clock_or_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("recommend touched the outside world")

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(time, "time", denied)
    monkeypatch.setattr(socket, "socket", denied)
    recommendation = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    assert {strategy.kind for strategy in recommendation.strategies} == {
        StrategyKind.CURRENT_PRACTICE,
        StrategyKind.SOIL_WATER_CONSERVATION,
        StrategyKind.RESILIENT_INCOME_FORAGE,
    }
