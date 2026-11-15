# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Tests for deterministic template-based explanation and number verification."""

from __future__ import annotations

import builtins
from decimal import Decimal
import socket
import time

import pytest

from src.engine import (
    Crop,
    Diagnosis,
    Plot,
    Priority,
    Projection,
    Recommendation,
    SourceAttribution,
    Strategy,
    StrategyKind,
    load_rules,
    recommend,
)
from src.explain import (
    Language,
    SUPPORTED_LANGUAGES,
    all_numbers_in_recommendation,
    assert_numbers_in_recommendation,
    explain,
    explain_recommendation,
    extract_numeric_field_values,
    extract_recommendation_numbers,
    extract_text_numbers,
    find_ungrounded_numbers,
    normalize_language,
    render_template,
)

RULES = load_rules()

_DIAGNOSIS_SOURCE = SourceAttribution(
    source="power",
    dataset="NASA POWER Agroclimatology Daily v2.x",
    nasa=True,
    url="https://power.larc.nasa.gov/",
)

_PT_STRATEGY_LABELS = {
    StrategyKind.CURRENT_PRACTICE: "Prática atual",
    StrategyKind.SOIL_WATER_CONSERVATION: "Conservação de solo e água",
    StrategyKind.RESILIENT_INCOME_FORAGE: "Renda resiliente e forragem",
}

_PT_ACTION_LABELS = {
    "plant_in_window": "Plante durante a janela aberta.",
    "wait_for_window": "Aguarde a janela de plantio.",
    "protect_soil": "Mantenha o solo coberto.",
    "plant_on_contour": "Plante em curvas de nível.",
    "delay_if_dry": "Não plante até que o balanço hídrico se recupere.",
}

_PT_VALIDATION_TEXT = (
    "Um técnico local deve confirmar esta recomendação. "
    "A verificação do ZARC ainda não foi concluída."
)


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


def make_projection(
    *,
    available: bool = True,
    rain_total_mm: float | None = 25.0,
    horizon_days: int = 15,
) -> Projection:
    return Projection(
        period_start="2026-11-08",
        period_end="2026-11-22",
        horizon_days=horizon_days,
        available=available,
        rain_total_mm=rain_total_mm,
    )


# ---------------------------------------------------------------------------
# 1. Substring Guarantees Across All Crops and Priorities
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("crop", [Crop.MAIZE, Crop.BEANS, Crop.CASSAVA])
@pytest.mark.parametrize("priority", [Priority.WATER, Priority.SOIL, Priority.EROSION, Priority.INCOME])
def test_all_crops_and_priorities_contain_required_substrings(
    crop: Crop,
    priority: Priority,
) -> None:
    rec = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        crop,
        priority,
        RULES,
    )

    text_en = render_template(rec, lang="en")
    text_pt = render_template(rec, lang="pt-BR")

    # English guarantees
    assert rec.uncertainty_note in text_en
    assert rec.validation_note in text_en
    for strategy in rec.strategies:
        assert strategy.title in text_en
        if strategy.actions:
            assert strategy.actions[0].summary in text_en

    # Portuguese guarantees
    assert rec.uncertainty_note in text_pt
    assert rec.validation_note in text_pt
    assert _PT_VALIDATION_TEXT in text_pt
    for strategy in rec.strategies:
        assert strategy.title in text_pt
        assert _PT_STRATEGY_LABELS[strategy.kind] in text_pt
        if strategy.actions:
            first_action = strategy.actions[0]
            assert first_action.summary in text_pt
            assert _PT_ACTION_LABELS[first_action.code] in text_pt


# ---------------------------------------------------------------------------
# 2. Grounded Numbers Verification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("proj_available,proj_rain", [(True, 25.0), (True, None), (False, None)])
@pytest.mark.parametrize("water_balance", [-176.85, None])
@pytest.mark.parametrize("ndvi_mean", [0.45, 0.10, None])
@pytest.mark.parametrize("slope_pct", [12.0, 2.0])
@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_all_numbers_grounded_in_recommendation(
    proj_available: bool,
    proj_rain: float | None,
    water_balance: float | None,
    ndvi_mean: float | None,
    slope_pct: float,
    lang: str,
) -> None:
    plot = make_plot(slope_mean_pct=slope_pct)
    diagnosis = make_diagnosis(
        water_balance_mm=water_balance,
        ndvi_mean=ndvi_mean,
        slope_mean_pct=slope_pct,
    )
    projection = make_projection(
        available=proj_available,
        rain_total_mm=proj_rain,
    )
    rec = recommend(plot, diagnosis, projection, Crop.MAIZE, Priority.WATER, RULES)

    text = render_template(rec, lang=lang)
    numbers = extract_text_numbers(text)

    # Must contain at least rank, water demand, and score numbers
    assert len(numbers) > 0

    # Grounded strictly in numeric fields (include_strings=False)
    numeric_fields = extract_numeric_field_values(rec)
    rec_numbers_no_strings = extract_recommendation_numbers(rec, include_strings=False)
    assert set(numbers).issubset(numeric_fields)
    assert set(numbers).issubset(rec_numbers_no_strings)
    assert all_numbers_in_recommendation(text, rec, include_strings=False)
    assert find_ungrounded_numbers(text, rec, include_strings=False) == []

    # Grounded including strings (include_strings=True)
    rec_numbers_with_strings = extract_recommendation_numbers(rec, include_strings=True)
    assert set(numbers).issubset(rec_numbers_with_strings)
    assert all_numbers_in_recommendation(text, rec, include_strings=True)
    assert find_ungrounded_numbers(text, rec, include_strings=True) == []

    # assert_numbers_in_recommendation should not raise
    assert_numbers_in_recommendation(text, rec, include_strings=False)
    assert_numbers_in_recommendation(text, rec, include_strings=True)


def test_numeric_field_values_vs_recommendation_numbers_with_strings() -> None:
    rec = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    field_nums = extract_numeric_field_values(rec)
    nums_no_strings = extract_recommendation_numbers(rec, include_strings=False)
    assert field_nums == nums_no_strings

    # Create a recommendation where a string field explicitly contains a number not in numeric fields
    rec_with_numbered_string = Recommendation(
        plot=rec.plot,
        crop=rec.crop,
        priority=rec.priority,
        diagnosis=rec.diagnosis,
        projection=rec.projection,
        strategies=rec.strategies,
        uncertainty_note=rec.uncertainty_note + " Reference code 9999.99 applies.",
        validation_note=rec.validation_note,
        sources=rec.sources,
    )

    field_nums_numbered = extract_numeric_field_values(rec_with_numbered_string)
    nums_no_strings_numbered = extract_recommendation_numbers(
        rec_with_numbered_string, include_strings=False
    )
    nums_with_strings_numbered = extract_recommendation_numbers(
        rec_with_numbered_string, include_strings=True
    )

    # 9999.99 is absent in numeric fields, but present when include_strings=True
    assert Decimal("9999.99") not in field_nums_numbered
    assert Decimal("9999.99") not in nums_no_strings_numbered
    assert Decimal("9999.99") in nums_with_strings_numbered
    assert field_nums_numbered == nums_no_strings_numbered
    assert field_nums_numbered.issubset(nums_with_strings_numbered)


# ---------------------------------------------------------------------------
# 3. Number Validator Rejection of Ungrounded Numbers
# ---------------------------------------------------------------------------


def test_number_validator_detects_and_rejects_hallucinations() -> None:
    rec = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    base_text = render_template(rec, lang="en")

    # Valid base text
    assert all_numbers_in_recommendation(base_text, rec)

    # Hallucinated positive float
    text_with_fake = base_text + "\nFake yield estimate: 9999.99 kg/ha"
    assert not all_numbers_in_recommendation(text_with_fake, rec)
    assert Decimal("9999.99") in find_ungrounded_numbers(text_with_fake, rec)

    # Hallucinated negative int
    text_with_neg = base_text + "\nOffset by -42 units."
    assert not all_numbers_in_recommendation(text_with_neg, rec)
    assert Decimal("-42") in find_ungrounded_numbers(text_with_neg, rec)

    # Hallucinated comma-decimal
    text_with_comma = base_text + "\nExpected growth 12,34 cm."
    assert not all_numbers_in_recommendation(text_with_comma, rec)
    assert Decimal("12.34") in find_ungrounded_numbers(text_with_comma, rec)

    # Error message format
    with pytest.raises(
        ValueError,
        match=r"Explanation contains numbers not found in Recommendation: 9999.99",
    ):
        assert_numbers_in_recommendation(text_with_fake, rec)


def test_number_validator_reports_multiple_ungrounded_numbers() -> None:
    rec = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    corrupted_text = "Analysis with 1234 and 5678."
    ungrounded = find_ungrounded_numbers(corrupted_text, rec)
    assert ungrounded == [Decimal("1234"), Decimal("5678")]

    with pytest.raises(
        ValueError,
        match=r"Explanation contains numbers not found in Recommendation: 1234, 5678",
    ):
        assert_numbers_in_recommendation(corrupted_text, rec)


# ---------------------------------------------------------------------------
# 4. Language Handling and Normalization
# ---------------------------------------------------------------------------


def test_language_normalization_and_variants() -> None:
    rec = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )

    # Constant and supported languages iteration
    assert SUPPORTED_LANGUAGES == ("en", "pt-BR")
    for supported_lang in SUPPORTED_LANGUAGES:
        lang_code: Language = supported_lang
        assert normalize_language(lang_code) == lang_code

    # Default is English
    assert render_template(rec) == render_template(rec, lang="en")
    assert normalize_language(None) == "en"

    # Supported variants
    assert normalize_language("en") == "en"
    assert normalize_language("EN") == "en"
    assert normalize_language("en-US") == "en"
    assert normalize_language("en_us") == "en"
    assert normalize_language("pt-BR") == "pt-BR"
    assert normalize_language("pt-br") == "pt-BR"
    assert normalize_language("pt_br") == "pt-BR"
    assert normalize_language("pt") == "pt-BR"
    assert normalize_language("  PT-BR  ") == "pt-BR"

    # Distinct outputs
    text_en = render_template(rec, lang="en")
    text_pt = render_template(rec, lang="pt-BR")
    assert text_en != text_pt
    assert "Agronomic Recommendation" in text_en
    assert "Recomendação Agronômica" in text_pt

    # Aliases
    assert explain(rec, lang="en") == text_en
    assert explain_recommendation(rec, lang="pt-BR") == text_pt

    # Unsupported language
    with pytest.raises(
        ValueError,
        match=r"Unsupported language: 'es'\. Supported languages: 'en', 'pt-BR'\.",
    ):
        normalize_language("es")

    with pytest.raises(
        ValueError,
        match=r"Unsupported language: 'fr'\. Supported languages: 'en', 'pt-BR'\.",
    ):
        render_template(rec, lang="fr")


# ---------------------------------------------------------------------------
# 5. Determinism and Purity
# ---------------------------------------------------------------------------


def test_render_template_is_deterministic() -> None:
    rec = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    first_en = render_template(rec, lang="en")
    first_pt = render_template(rec, lang="pt-BR")

    for _ in range(10):
        assert render_template(rec, lang="en") == first_en
        assert render_template(rec, lang="pt-BR") == first_pt


def test_render_template_does_not_read_file_clock_or_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("render_template accessed external environment")

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(time, "time", denied)
    monkeypatch.setattr(socket, "socket", denied)

    rec = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    text_en = render_template(rec, lang="en")
    text_pt = render_template(rec, lang="pt-BR")
    assert len(text_en) > 0
    assert len(text_pt) > 0


# ---------------------------------------------------------------------------
# 6. Edge Cases
# ---------------------------------------------------------------------------


def test_strategy_with_empty_actions() -> None:
    rec = recommend(
        make_plot(),
        make_diagnosis(),
        make_projection(),
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )
    # Strip actions from all strategies
    strategies_without_actions = tuple(
        Strategy(
            kind=s.kind,
            rank=s.rank,
            score=s.score,
            title=s.title,
            crops=s.crops,
            trade_offs=s.trade_offs,
            planting_schedule=s.planting_schedule,
            water_demand_mm=s.water_demand_mm,
            breaks_pest_cycle=s.breaks_pest_cycle,
            pest_cycle_note=s.pest_cycle_note,
            actions=(),
        )
        for s in rec.strategies
    )
    rec_empty_actions = Recommendation(
        plot=rec.plot,
        crop=rec.crop,
        priority=rec.priority,
        diagnosis=rec.diagnosis,
        projection=rec.projection,
        strategies=strategies_without_actions,
        uncertainty_note=rec.uncertainty_note,
        validation_note=rec.validation_note,
        sources=rec.sources,
    )

    text_en = render_template(rec_empty_actions, lang="en")
    assert "No specific actions recommended." in text_en
    assert all_numbers_in_recommendation(text_en, rec_empty_actions, include_strings=False)

    text_pt = render_template(rec_empty_actions, lang="pt-BR")
    assert "Nenhuma ação específica recomendada." in text_pt
    assert all_numbers_in_recommendation(text_pt, rec_empty_actions, include_strings=False)


def test_diagnosis_all_optional_numeric_fields_none() -> None:
    diag_none = Diagnosis(
        period_start="2026-10-09",
        period_end="2026-11-07",
        rain_total_mm=None,
        water_balance_mm=None,
        temperature_mean_c=None,
        temperature_max_c=None,
        ndvi_mean=None,
        elevation_m=None,
        slope_mean_pct=None,
    )
    proj_none = Projection(
        period_start="2026-11-08",
        period_end="2026-11-22",
        horizon_days=15,
        available=False,
        rain_total_mm=None,
    )
    rec = recommend(
        make_plot(),
        diag_none,
        proj_none,
        Crop.MAIZE,
        Priority.WATER,
        RULES,
    )

    for lang in ("en", "pt-BR"):
        text = render_template(rec, lang=lang)
        assert "None" not in text
        assert "none" not in text.lower().split()
        assert len(extract_text_numbers(text)) > 0
        assert all_numbers_in_recommendation(text, rec, include_strings=False)
