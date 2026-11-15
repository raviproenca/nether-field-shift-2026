# AI-assisted: generated with Cursor, reviewed by Guilherme
"""Turn a Recommendation into short template text in English or Brazilian Portuguese.

The template copies strategy titles, the first action summary, and the
uncertainty note. It does not add a number of its own and does not change
the Recommendation.
"""

from __future__ import annotations

from src.engine.model import Recommendation, Strategy

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


def explain(recommendation: Recommendation, lang: str = "en") -> str:
    """Return the fixed template for ``recommendation`` in ``lang``.

    ``lang`` is ``en`` or ``pt-BR``. The dashboard default is English.
    """
    if lang not in _LANGS:
        raise ValueError(f"lang must be en or pt-BR, got {lang!r}")
    lines = [_strategy_line(strategy, lang) for strategy in _by_rank(recommendation)]
    if not lines:
        lines.append(_NO_STRATEGIES[lang])
    lines.append(_UNCERTAINTY[lang].format(note=recommendation.uncertainty_note))
    return "\n".join(lines)


def _by_rank(recommendation: Recommendation) -> tuple[Strategy, ...]:
    return tuple(sorted(recommendation.strategies, key=lambda strategy: strategy.rank))


def _strategy_line(strategy: Strategy, lang: str) -> str:
    title = strategy.title
    if not strategy.actions:
        return f"{title}: {_NO_ACTION[lang]}"
    return f"{title}: {strategy.actions[0].summary}"
