# AI-assisted: generated with Cursor; pending review by the team.
"""Tests for strategy generation, ranking, and schema validation."""

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
    recommend,
    serialize_recommendation,
)

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "data-format"
    / "recommendation.schema.json"
)

_DIAGNOSIS_SOURCE = SourceAttribution(
    source="power",
    dataset="NASA POWER Agroclimatology Daily v2.x",
    nasa=True,
    url="https://power.larc.nasa.gov/",
)
_PROJECTION_SOURCE = SourceAttribution(
    source="open_meteo",
    dataset="Open-Meteo 15-day Forecast API (ECMWF/GFS)",
    nasa=False,
    url="https://open-meteo.com/",
    notice="CC BY 4.0 (non-commercial demo use)",
)


def get_validator() -> Draft202012Validator:
    """Load recommendation.schema.json and return a Draft 2020-12 validator."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def make_plot(previous_crops: tuple[str, ...] = ()) -> Plot:
    return Plot(
        lat=-10.685,
        lon=-37.425,
        radius_km=5.0,
        previous_crops=previous_crops,
    )


def make_diagnosis() -> Diagnosis:
    return Diagnosis(
        period_start="2026-08-15",
        period_end="2026-11-12",
        sources=(_DIAGNOSIS_SOURCE,),
    )


def make_projection(*, available: bool = True) -> Projection:
    return Projection(
        period_start="2026-11-15",
        period_end="2026-11-29",
        horizon_days=15,
        available=available,
        sources=(_PROJECTION_SOURCE,),
    )


def kinds_of(recommendation) -> list[str]:
    return [strategy.kind.value for strategy in recommendation.strategies]


def test_strategy_crops_follow_the_three_fixed_roles() -> None:
    diagnosis = make_diagnosis()
    projection = make_projection()
    plot = make_plot()
    expected = {
        Crop.MAIZE: {
            "current_practice": ("maize",),
            "soil_water_conservation": ("maize", "beans"),
            "resilient_income_forage": ("maize", "cassava"),
        },
        Crop.BEANS: {
            "current_practice": ("beans",),
            "soil_water_conservation": ("beans", "cassava"),
            "resilient_income_forage": ("beans", "maize"),
        },
        Crop.CASSAVA: {
            "current_practice": ("cassava",),
            "soil_water_conservation": ("cassava", "beans"),
            "resilient_income_forage": ("cassava", "maize"),
        },
    }
    for crop, crops_by_kind in expected.items():
        recommendation = recommend(plot, diagnosis, projection, crop, Priority.SOIL)
        for strategy in recommendation.strategies:
            assert strategy.crops == crops_by_kind[strategy.kind.value]


def test_after_maize_income_ranks_soil_water_conservation_first() -> None:
    recommendation = recommend(
        make_plot(("maize",)),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.INCOME,
    )
    assert kinds_of(recommendation) == [
        "soil_water_conservation",
        "resilient_income_forage",
        "current_practice",
    ]
    soil = recommendation.strategies[0]
    assert soil.crops == ("maize", "beans")


def test_after_beans_income_ranks_resilient_first_and_current_last() -> None:
    recommendation = recommend(
        make_plot(("beans",)),
        make_diagnosis(),
        make_projection(),
        Crop.BEANS,
        Priority.INCOME,
    )
    assert kinds_of(recommendation) == [
        "resilient_income_forage",
        "soil_water_conservation",
        "current_practice",
    ]
    assert recommendation.strategies[0].crops == ("beans", "maize")
    assert recommendation.strategies[2].crops == ("beans",)


@pytest.mark.parametrize("priority", [Priority.WATER, Priority.SOIL, Priority.EROSION, Priority.INCOME])
def test_after_maize_any_priority_ranks_soil_water_conservation_first(priority: Priority) -> None:
    recommendation = recommend(
        make_plot(("maize",)),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        priority,
    )
    assert recommendation.strategies[0].kind is StrategyKind.SOIL_WATER_CONSERVATION


def test_after_maize_water_matches_income_rank_one() -> None:
    shared = (make_plot(("maize",)), make_diagnosis(), make_projection(), Crop.MAIZE)
    income = recommend(*shared, Priority.INCOME)
    water = recommend(*shared, Priority.WATER)
    assert income.strategies[0].kind is StrategyKind.SOIL_WATER_CONSERVATION
    assert water.strategies[0].kind is StrategyKind.SOIL_WATER_CONSERVATION


def test_no_previous_crop_income_ranks_resilient_then_soil_then_current() -> None:
    recommendation = recommend(
        make_plot(()),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.INCOME,
    )
    assert kinds_of(recommendation) == [
        "resilient_income_forage",
        "soil_water_conservation",
        "current_practice",
    ]


@pytest.mark.parametrize("priority", [Priority.SOIL, Priority.WATER, Priority.EROSION])
def test_no_previous_crop_soil_water_or_erosion_ranks_conservation_first(
    priority: Priority,
) -> None:
    recommendation = recommend(
        make_plot(()),
        make_diagnosis(),
        make_projection(),
        Crop.CASSAVA,
        priority,
    )
    assert kinds_of(recommendation) == [
        "soil_water_conservation",
        "resilient_income_forage",
        "current_practice",
    ]


def test_only_the_last_previous_crop_is_recognized() -> None:
    diagnosis = make_diagnosis()
    projection = make_projection()
    maize_last = recommend(
        make_plot(("beans", "maize")),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.INCOME,
    )
    maize_only = recommend(
        make_plot(("maize",)),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.INCOME,
    )
    unrecognized_last = recommend(
        make_plot(("maize", "rice")),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.INCOME,
    )
    no_previous = recommend(
        make_plot(()),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.INCOME,
    )
    assert kinds_of(maize_last) == kinds_of(maize_only)
    assert kinds_of(unrecognized_last) == kinds_of(no_previous)


def test_previous_beans_or_cassava_do_not_count_as_nitrogen_depleting() -> None:
    diagnosis = make_diagnosis()
    projection = make_projection()
    expected = [
        "resilient_income_forage",
        "soil_water_conservation",
        "current_practice",
    ]
    for previous in ("beans", "cassava"):
        recommendation = recommend(
            make_plot((previous,)),
            diagnosis,
            projection,
            Crop.MAIZE,
            Priority.INCOME,
        )
        assert kinds_of(recommendation) == expected
        assert recommendation.strategies[0].crops == ("maize", "cassava")


def test_unknown_previous_label_is_treated_as_no_recognized_previous_crop() -> None:
    diagnosis = make_diagnosis()
    projection = make_projection()
    unknown = recommend(
        make_plot(("rice",)),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.INCOME,
    )
    recognized_absent = recommend(
        make_plot(()),
        diagnosis,
        projection,
        Crop.MAIZE,
        Priority.INCOME,
    )
    assert kinds_of(unknown) == kinds_of(recognized_absent)
    assert kinds_of(unknown) == [
        "resilient_income_forage",
        "soil_water_conservation",
        "current_practice",
    ]


def test_forecast_absent_still_returns_a_recommendation() -> None:
    recommendation = recommend(
        make_plot(("maize",)),
        make_diagnosis(),
        make_projection(available=False),
        Crop.MAIZE,
        Priority.WATER,
    )
    assert len(recommendation.strategies) == 3
    assert recommendation.uncertainty_note == "The forecast is absent."
    get_validator().validate(json.loads(json.dumps(serialize_recommendation(recommendation))))


def test_forecast_available_says_it_is_not_an_observation() -> None:
    recommendation = recommend(
        make_plot(("maize",)),
        make_diagnosis(),
        make_projection(available=True),
        Crop.BEANS,
        Priority.SOIL,
    )
    assert recommendation.uncertainty_note == "The forecast is not an observation."


def test_repeat_call_serializes_byte_for_byte() -> None:
    args = (
        make_plot(("maize",)),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.INCOME,
    )
    first = json.dumps(serialize_recommendation(recommend(*args))).encode("utf-8")
    second = json.dumps(serialize_recommendation(recommend(*args))).encode("utf-8")
    assert first == second


def test_recommendation_validates_and_leaves_story_1_4_fields_empty() -> None:
    validator = get_validator()
    recommendation = recommend(
        make_plot(("maize",)),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.INCOME,
    )
    payload = json.loads(json.dumps(serialize_recommendation(recommendation)))
    validator.validate(payload)

    assert [strategy["rank"] for strategy in payload["strategies"]] == [1, 2, 3]
    assert [strategy["score"] for strategy in payload["strategies"]] == [3.0, 2.0, 1.0]
    assert payload["validation_note"] == "The ZARC check is not done yet."
    assert [source["source"] for source in payload["sources"]] == ["power", "open_meteo"]
    assert [source["nasa"] for source in payload["sources"]] == [True, False]
    trade_offs = {
        "current_practice": "keeps_current_calendar",
        "soil_water_conservation": "favors_cover_and_soil",
        "resilient_income_forage": "favors_forage_or_income",
    }
    for strategy in payload["strategies"]:
        assert strategy["title"] == strategy["kind"].replace("_", " ")
        assert strategy["trade_offs"] == [trade_offs[strategy["kind"]]]
        assert strategy["actions"] == []
        assert strategy["planting_schedule"] == []
        assert strategy["water_demand_mm"] == 0
        assert strategy["breaks_pest_cycle"] is False
        assert strategy["pest_cycle_note"] == ""


def test_recommend_does_not_read_a_file_clock_network_or_model(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("recommend touched the outside world")

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(time, "time", denied)
    monkeypatch.setattr(socket, "socket", denied)

    recommendation = recommend(
        make_plot(("maize",)),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
    )
    assert {strategy.kind for strategy in recommendation.strategies} == {
        StrategyKind.CURRENT_PRACTICE,
        StrategyKind.SOIL_WATER_CONSERVATION,
        StrategyKind.RESILIENT_INCOME_FORAGE,
    }
