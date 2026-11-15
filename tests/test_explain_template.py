# AI-assisted: generated with Cursor, reviewed by Guilherme
"""Template explanation covers every strategy and adds no number of its own."""

from __future__ import annotations

import re

import pytest

from src.engine.model import (
    Action,
    Crop,
    Diagnosis,
    Plot,
    Priority,
    Projection,
    Recommendation,
    Strategy,
    StrategyKind,
)
from src.explain.template import explain
from tests.test_engine_model import make_sample_recommendation

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _numbers(text: str) -> list[str]:
    return _NUMBER.findall(text)


def test_template_names_each_strategy_its_first_action_and_the_uncertainty() -> None:
    recommendation = make_sample_recommendation()
    text = explain(recommendation, lang="en")
    for strategy in recommendation.strategies:
        assert strategy.title in text
        assert strategy.actions[0].summary in text
    assert recommendation.uncertainty_note in text
    assert text.index("Uncertainty:") > text.index(recommendation.strategies[0].title)


def test_portuguese_template_uses_the_same_facts() -> None:
    recommendation = make_sample_recommendation()
    text = explain(recommendation, lang="pt-BR")
    assert "Incerteza:" in text
    assert "Uncertainty:" not in text
    for strategy in recommendation.strategies:
        assert strategy.title in text
        assert strategy.actions[0].summary in text
    assert recommendation.uncertainty_note in text


def test_every_number_in_the_text_appears_in_the_recommendation() -> None:
    recommendation = make_sample_recommendation()
    for lang in ("en", "pt-BR"):
        text = explain(recommendation, lang=lang)
        allowed = _copied_numbers(recommendation)
        for number in _numbers(text):
            assert number in allowed


def test_later_actions_and_unused_diagnosis_numbers_stay_out() -> None:
    recommendation = _one_strategy(
        water_balance_mm=99999.5,
        actions=(
            Action(code="wait", summary="Wait for the window.", timing="later", evidence="Balance is 12.5 mm."),
            Action(code="cover", summary="Keep the soil covered.", timing="now", evidence="NDVI is 0.2."),
        ),
    )
    text = explain(recommendation)
    assert "Wait for the window." in text
    assert "Keep the soil covered." not in text
    assert "12.5" not in text
    assert "99999.5" not in text
    assert "600" not in text


def test_strategies_are_ordered_by_rank_and_an_empty_list_still_states_uncertainty() -> None:
    low = _strategy(rank=2, title="second")
    high = _strategy(rank=1, title="first")
    recommendation = _recommendation((low, high))
    text = explain(recommendation)
    assert text.index("first:") < text.index("second:")
    empty = explain(_recommendation(()), lang="pt-BR")
    assert empty.startswith("Esta recomendação não tem estratégias.")
    assert "Incerteza: The forecast is absent." in empty


def test_portuguese_names_a_strategy_with_no_action() -> None:
    text = explain(_one_strategy(water_balance_mm=1.0, actions=()), lang="pt-BR")
    assert "current practice: Esta estratégia não tem ação." in text


def test_unknown_language_is_rejected() -> None:
    with pytest.raises(ValueError, match="pt-BR"):
        explain(make_sample_recommendation(), lang="es")


def _copied_numbers(recommendation: Recommendation) -> set[str]:
    parts = [recommendation.uncertainty_note]
    for strategy in recommendation.strategies:
        parts.append(strategy.title)
        if strategy.actions:
            parts.append(strategy.actions[0].summary)
    return set(_numbers("\n".join(parts)))


def _strategy(*, rank: int, title: str, actions: tuple[Action, ...] = ()) -> Strategy:
    return Strategy(
        kind=StrategyKind.CURRENT_PRACTICE,
        rank=rank,
        score=0.4,
        title=title,
        crops=("maize",),
        trade_offs=("keeps_current_calendar",),
        planting_schedule=(),
        water_demand_mm=600.0,
        breaks_pest_cycle=False,
        pest_cycle_note="",
        actions=actions,
    )


def _recommendation(strategies: tuple[Strategy, ...], water_balance_mm: float = 1.0) -> Recommendation:
    return Recommendation(
        plot=Plot(lat=-10.7, lon=-37.4, radius_km=5),
        crop=Crop.MAIZE,
        priority=Priority.WATER,
        diagnosis=Diagnosis(
            period_start="2026-10-09",
            period_end="2026-11-07",
            water_balance_mm=water_balance_mm,
        ),
        projection=Projection(
            period_start="2026-11-08",
            period_end="2026-11-22",
            horizon_days=15,
            available=False,
        ),
        strategies=strategies,
        uncertainty_note="The forecast is absent.",
        validation_note="The ZARC check is not done yet.",
    )


def _one_strategy(*, water_balance_mm: float, actions: tuple[Action, ...]) -> Recommendation:
    return _recommendation(
        (_strategy(rank=1, title="current practice", actions=actions),),
        water_balance_mm=water_balance_mm,
    )
