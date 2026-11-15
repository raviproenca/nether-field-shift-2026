# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Template-based agronomic explanation module without AI/LLM dependencies."""

from src.explain.numbers import (
    all_numbers_in_recommendation,
    assert_numbers_in_recommendation,
    extract_numeric_field_values,
    extract_recommendation_numbers,
    extract_text_numbers,
    find_ungrounded_numbers,
)
from src.explain.template import (
    Language,
    SUPPORTED_LANGUAGES,
    explain,
    explain_recommendation,
    normalize_language,
    render_template,
)

__all__ = [
    "Language",
    "SUPPORTED_LANGUAGES",
    "all_numbers_in_recommendation",
    "assert_numbers_in_recommendation",
    "explain",
    "explain_recommendation",
    "extract_numeric_field_values",
    "extract_recommendation_numbers",
    "extract_text_numbers",
    "find_ungrounded_numbers",
    "normalize_language",
    "render_template",
]
