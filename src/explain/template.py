# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Deterministic, pure template-based explanation generator for recommendations."""

from __future__ import annotations

from typing import Literal

from src.engine.model import Recommendation
from src.explain.numbers import assert_numbers_in_recommendation

Language = Literal["en", "pt-BR"]
SUPPORTED_LANGUAGES: tuple[Language, ...] = ("en", "pt-BR")

_CROP_TRANSLATIONS_EN: dict[str, str] = {
    "maize": "maize",
    "beans": "beans",
    "cassava": "cassava",
}

_CROP_TRANSLATIONS_PT: dict[str, str] = {
    "maize": "milho",
    "beans": "feijão",
    "cassava": "mandioca",
}

_PRIORITY_TRANSLATIONS_EN: dict[str, str] = {
    "water": "water",
    "soil": "soil",
    "erosion": "erosion",
    "income": "income",
}

_PRIORITY_TRANSLATIONS_PT: dict[str, str] = {
    "water": "água",
    "soil": "solo",
    "erosion": "erosão",
    "income": "renda",
}

_STRATEGY_TITLES_EN: dict[str, str] = {
    "current_practice": "Current practice",
    "soil_water_conservation": "Soil and water conservation",
    "resilient_income_forage": "Resilient income or forage",
}

_STRATEGY_TITLES_PT: dict[str, str] = {
    "current_practice": "Prática atual",
    "soil_water_conservation": "Conservação de solo e água",
    "resilient_income_forage": "Renda resiliente e forragem",
}

_ACTION_TRANSLATIONS_PT: dict[str, str] = {
    "plant_in_window": "Plante durante a janela aberta.",
    "wait_for_window": "Aguarde a janela de plantio.",
    "protect_soil": "Mantenha o solo coberto.",
    "plant_on_contour": "Plante em curvas de nível.",
    "delay_if_dry": "Não plante até que o balanço hídrico se recupere.",
}

_UNCERTAINTY_MAP_PT: tuple[tuple[str, str], ...] = (
    ("The forecast is not an observation.", "A previsão não é uma observação."),
    ("The forecast is absent.", "A previsão está ausente."),
    (
        "Water balance is below the severe deficit threshold.",
        "O balanço hídrico está abaixo do limite de déficit severo.",
    ),
    ("Water balance is missing.", "O balanço hídrico está ausente."),
    ("NDVI is missing.", "O NDVI está ausente."),
)

_VALIDATION_EN = (
    "A local technician must confirm this advice. The ZARC check is not done yet."
)
_VALIDATION_PT = (
    "Um técnico local deve confirmar esta recomendação. "
    "A verificação do ZARC ainda não foi concluída."
)


def normalize_language(lang: str | None = None) -> Language:
    """Normalize language code to supported literal or raise ValueError."""
    if lang is None:
        return "en"
    cleaned = lang.strip().lower()
    if cleaned in ("en", "en-us", "en_us"):
        return "en"
    if cleaned in ("pt-br", "pt_br", "pt"):
        return "pt-BR"
    raise ValueError(
        f"Unsupported language: {lang!r}. Supported languages: 'en', 'pt-BR'."
    )


def _render_en(rec: Recommendation) -> str:
    crop_str = _CROP_TRANSLATIONS_EN.get(rec.crop.value, rec.crop.value)
    prio_str = _PRIORITY_TRANSLATIONS_EN.get(rec.priority.value, rec.priority.value)

    lines: list[str] = [
        "# Agronomic Recommendation",
        "",
        "Context:",
        f"- Crop: {crop_str}",
        f"- Priority: {prio_str}",
    ]

    diag = rec.diagnosis
    if diag.rain_total_mm is not None or diag.water_balance_mm is not None:
        lines.append("")
        lines.append("Observed climate:")
        if diag.rain_total_mm is not None:
            lines.append(f"- Observed rainfall: {diag.rain_total_mm} mm")
        if diag.water_balance_mm is not None:
            lines.append(f"- Water balance: {diag.water_balance_mm} mm")

    proj = rec.projection
    lines.append("")
    if proj.available:
        lines.append("Weather forecast:")
        lines.append(f"- Forecast horizon: {proj.horizon_days} days")
        if proj.rain_total_mm is not None:
            lines.append(f"- Forecast rainfall: {proj.rain_total_mm} mm")
    else:
        lines.append("Weather forecast:")
        lines.append("- Forecast data is absent.")

    lines.append("")
    lines.append("Ranked Strategies:")
    for strategy in rec.strategies:
        title_en = _STRATEGY_TITLES_EN.get(strategy.kind.value, strategy.title)
        if title_en != strategy.title:
            title_header = f"{title_en} ({strategy.title})"
        else:
            title_header = strategy.title
        crops_str = ", ".join(
            _CROP_TRANSLATIONS_EN.get(c, c) for c in strategy.crops
        )
        lines.append(f"Strategy {strategy.rank}: {title_header}")
        lines.append(f"- Crops: {crops_str}")
        lines.append(f"- Water demand: {strategy.water_demand_mm} mm")
        lines.append(f"- Score: {strategy.score}")
        if strategy.actions:
            first_action = strategy.actions[0]
            lines.append(f"- Recommended action: {first_action.summary}")
        else:
            lines.append("- Recommended action: No specific actions recommended.")
        lines.append("")

    lines.append("Notes and Validation:")
    lines.append(f"- Uncertainty: {rec.uncertainty_note}")
    lines.append(f"- Validation: {rec.validation_note}")

    return "\n".join(lines)


def _render_pt(rec: Recommendation) -> str:
    crop_str = _CROP_TRANSLATIONS_PT.get(rec.crop.value, rec.crop.value)
    prio_str = _PRIORITY_TRANSLATIONS_PT.get(rec.priority.value, rec.priority.value)

    lines: list[str] = [
        "# Recomendação Agronômica",
        "",
        "Contexto:",
        f"- Cultura: {crop_str}",
        f"- Prioridade: {prio_str}",
    ]

    diag = rec.diagnosis
    if diag.rain_total_mm is not None or diag.water_balance_mm is not None:
        lines.append("")
        lines.append("Clima observado:")
        if diag.rain_total_mm is not None:
            lines.append(f"- Chuva observada: {diag.rain_total_mm} mm")
        if diag.water_balance_mm is not None:
            lines.append(f"- Balanço hídrico: {diag.water_balance_mm} mm")

    proj = rec.projection
    lines.append("")
    if proj.available:
        lines.append("Previsão meteorológica:")
        lines.append(f"- Horizonte de previsão: {proj.horizon_days} dias")
        if proj.rain_total_mm is not None:
            lines.append(f"- Chuva prevista: {proj.rain_total_mm} mm")
    else:
        lines.append("Previsão meteorológica:")
        lines.append("- Previsão meteorológica ausente.")

    lines.append("")
    lines.append("Estratégias classificadas:")
    for strategy in rec.strategies:
        title_pt = _STRATEGY_TITLES_PT.get(strategy.kind.value, strategy.title)
        if title_pt != strategy.title:
            title_header = f"{title_pt} ({strategy.title})"
        else:
            title_header = strategy.title
        crops_str = ", ".join(
            _CROP_TRANSLATIONS_PT.get(c, c) for c in strategy.crops
        )
        lines.append(f"Estratégia {strategy.rank}: {title_header}")
        lines.append(f"- Culturas: {crops_str}")
        lines.append(f"- Demanda hídrica: {strategy.water_demand_mm} mm")
        lines.append(f"- Pontuação: {strategy.score}")
        if strategy.actions:
            first_action = strategy.actions[0]
            action_pt = _ACTION_TRANSLATIONS_PT.get(first_action.code, first_action.summary)
            if action_pt != first_action.summary:
                action_text = f"{action_pt} ({first_action.summary})"
            else:
                action_text = first_action.summary
            lines.append(f"- Ação recomendada: {action_text}")
        else:
            lines.append("- Ação recomendada: Nenhuma ação específica recomendada.")
        lines.append("")

    lines.append("Notas e Validação:")

    unc_pt = rec.uncertainty_note
    for en, pt in _UNCERTAINTY_MAP_PT:
        unc_pt = unc_pt.replace(en, pt)
    if unc_pt != rec.uncertainty_note:
        lines.append(f"- Incerteza: {unc_pt} ({rec.uncertainty_note})")
    else:
        lines.append(f"- Incerteza: {rec.uncertainty_note}")

    val_pt = rec.validation_note.replace(_VALIDATION_EN, _VALIDATION_PT)
    if val_pt != rec.validation_note:
        lines.append(f"- Validação: {val_pt} ({rec.validation_note})")
    else:
        lines.append(f"- Validação: {rec.validation_note}")

    return "\n".join(lines)


def render_template(recommendation: Recommendation, lang: str = "en") -> str:
    """Render deterministic explanation for recommendation without hardcoded numbers."""
    normalized = normalize_language(lang)
    if normalized == "en":
        text = _render_en(recommendation)
    else:
        text = _render_pt(recommendation)

    assert_numbers_in_recommendation(text, recommendation)
    return text


def explain_recommendation(recommendation: Recommendation, lang: str = "en") -> str:
    """Alias for render_template."""
    return render_template(recommendation, lang=lang)


def explain(recommendation: Recommendation, lang: str = "en") -> str:
    """Alias for render_template."""
    return render_template(recommendation, lang=lang)
