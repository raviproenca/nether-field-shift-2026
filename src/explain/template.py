# AI-assisted: generated with Cursor, reviewed by Guilherme
"""Turn a Recommendation into short template text in English or Brazilian Portuguese.

The template copies strategy titles, the first action summary, and the
uncertainty note. It does not add a number of its own and does not change
the Recommendation.
"""

from __future__ import annotations

from src.engine.model import Crop, Priority, Recommendation, Strategy

_LANGS = ("en", "pt-BR")

_NO_ACTION = {
    "en": "This strategy has no action.",
    "pt-BR": "Esta estratégia não tem ação.",
}

_NO_STRATEGIES = {
    "en": "This recommendation has no strategies.",
    "pt-BR": "Esta recomendação não tem estratégias.",
}

_UNCERTAINTY = {
    "en": "Uncertainty: {note}",
    "pt-BR": "Incerteza: {note}",
}

_INPUTS = {
    "en": "Inputs — last crop grown: {previous}; intended crop: {crop}; priority: {priority}.",
    "pt-BR": "Entradas — última cultura cultivada: {previous}; cultura pretendida: {crop}; prioridade: {priority}.",
}

_SCORE_NOTE = {
    "en": "Rule scores compare fit to the selected priority and available evidence; they are not yield probabilities.",
    "pt-BR": "As notas comparam a adequação à prioridade escolhida e às evidências disponíveis; não são probabilidades de rendimento.",
}

_PREVIOUS_UNKNOWN = {"en": "unknown / none", "pt-BR": "não informada"}
_CROP_LABELS = {
    "en": {Crop.MAIZE: "maize", Crop.BEANS: "beans", Crop.CASSAVA: "cassava"},
    "pt-BR": {Crop.MAIZE: "milho", Crop.BEANS: "feijão", Crop.CASSAVA: "mandioca"},
}
_PRIORITY_LABELS = {
    "en": {Priority.WATER: "water", Priority.SOIL: "soil", Priority.EROSION: "erosion", Priority.INCOME: "income"},
    "pt-BR": {Priority.WATER: "água", Priority.SOIL: "solo", Priority.EROSION: "erosão", Priority.INCOME: "renda"},
}
_ROTATION_LABELS = {"en": "rotation", "pt-BR": "rotação"}
_SCORE_LABELS = {"en": "score", "pt-BR": "nota"}
_ACTION_LABELS = {"en": "Action", "pt-BR": "Ação"}
_TRADE_OFF_LABELS = {
    "en": {
        "keeps_current_calendar": "keeps the current calendar and routine",
        "favors_cover_and_soil": "favors soil cover and soil health",
        "favors_forage_or_income": "favors forage and income",
    },
    "pt-BR": {
        "keeps_current_calendar": "mantém o calendário e a rotina atuais",
        "favors_cover_and_soil": "favorece a cobertura e a saúde do solo",
        "favors_forage_or_income": "favorece forragem e renda",
    },
}


def explain(recommendation: Recommendation, lang: str = "en") -> str:
    """Return the fixed template for ``recommendation`` in ``lang``.

    ``lang`` is ``en`` or ``pt-BR``. The dashboard default is English.
    """
    if lang not in _LANGS:
        raise ValueError(f"lang must be en or pt-BR, got {lang!r}")
    last_crop = recommendation.plot.previous_crops[-1] if recommendation.plot.previous_crops else None
    crop_labels = _CROP_LABELS[lang]
    priority_labels = _PRIORITY_LABELS[lang]
    lines = [
        _INPUTS[lang].format(
            previous=crop_labels.get(last_crop, last_crop) if last_crop else _PREVIOUS_UNKNOWN[lang],
            crop=crop_labels.get(recommendation.crop, recommendation.crop.value),
            priority=priority_labels.get(recommendation.priority, recommendation.priority.value),
        ),
        _SCORE_NOTE[lang],
    ]
    strategies = _by_rank(recommendation)
    lines.extend(_strategy_line(strategy, lang) for strategy in strategies)
    if not strategies:
        lines.append(_NO_STRATEGIES[lang])
    lines.append(_UNCERTAINTY[lang].format(note=recommendation.uncertainty_note))
    return "\n".join(lines)


def _by_rank(recommendation: Recommendation) -> tuple[Strategy, ...]:
    return tuple(sorted(recommendation.strategies, key=lambda strategy: strategy.rank))


def _strategy_line(strategy: Strategy, lang: str) -> str:
    crops = " + ".join(_CROP_LABELS[lang].get(crop, crop) for crop in strategy.crops)
    trade_offs = "; ".join(_TRADE_OFF_LABELS[lang].get(item, item) for item in strategy.trade_offs)
    action = strategy.actions[0].summary if strategy.actions else _NO_ACTION[lang]
    pest_label = "Pest-cycle assessment" if lang == "en" else "Ciclo de pragas"
    trade_label = "Trade-off" if lang == "en" else "Contrapartida"
    return (
        f"#{strategy.rank} {strategy.title} — {_ROTATION_LABELS[lang]}: {crops}; "
        f"{_SCORE_LABELS[lang]}: {strategy.score:g}. {trade_label}: {trade_offs}. "
        f"{_ACTION_LABELS[lang]}: {action} {pest_label}: {strategy.pest_cycle_note}"
    )
