# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Validation and extraction of numbers grounded in agronomic recommendations."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import fields, is_dataclass
from decimal import Decimal
import math
import re
from typing import Any

from src.engine.model import Recommendation

_NUMBER_PATTERN = re.compile(r"(?<![0-9A-Za-z])-?\d+(?:[.,]\d+)?")


def _iter_leaf_values(item: Any) -> Iterator[Any]:
    """Recursively yield all leaf values in dataclasses, sequences, and mappings."""
    if is_dataclass(item) and not isinstance(item, type):
        for f in fields(item):
            yield from _iter_leaf_values(getattr(item, f.name))
    elif isinstance(item, (list, tuple)):
        for elem in item:
            yield from _iter_leaf_values(elem)
    elif isinstance(item, dict):
        for k, v in item.items():
            yield from _iter_leaf_values(k)
            yield from _iter_leaf_values(v)
    else:
        yield item


def extract_text_numbers(text: str) -> list[Decimal]:
    """Find all numeric matches in text, normalize commas to periods, and convert to Decimal."""
    matches = _NUMBER_PATTERN.findall(text)
    return [Decimal(match.replace(",", ".")) for match in matches]


def extract_numeric_field_values(recommendation: Recommendation) -> set[Decimal]:
    """Recursively traverse recommendation dataclass hierarchy and collect numeric field values."""
    numbers: set[Decimal] = set()
    for val in _iter_leaf_values(recommendation):
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if isinstance(val, float) and not math.isfinite(val):
                continue
            numbers.add(Decimal(str(val)))
    return numbers


def extract_recommendation_numbers(
    recommendation: Recommendation,
    *,
    include_strings: bool = True,
) -> set[Decimal]:
    """Extract all valid Decimal numbers from a Recommendation.

    Always includes int and float fields. If include_strings is True, also
    traverses string fields and extracts all numbers found within them.
    """
    numbers = extract_numeric_field_values(recommendation)
    if not include_strings:
        return numbers

    for val in _iter_leaf_values(recommendation):
        if isinstance(val, str):
            for num in extract_text_numbers(val):
                numbers.add(num)
    return numbers


def find_ungrounded_numbers(
    text: str,
    recommendation: Recommendation,
    *,
    include_strings: bool = True,
) -> list[Decimal]:
    """Return all Decimal numbers from text not present in recommendation."""
    valid_numbers = extract_recommendation_numbers(
        recommendation,
        include_strings=include_strings,
    )
    return [
        num
        for num in extract_text_numbers(text)
        if num not in valid_numbers
    ]


def all_numbers_in_recommendation(
    text: str,
    recommendation: Recommendation,
    *,
    include_strings: bool = True,
) -> bool:
    """Return True if all numbers in text are grounded in recommendation."""
    return len(find_ungrounded_numbers(text, recommendation, include_strings=include_strings)) == 0


def assert_numbers_in_recommendation(
    text: str,
    recommendation: Recommendation,
    *,
    include_strings: bool = True,
) -> None:
    """Raise ValueError if text contains any numbers not found in recommendation."""
    ungrounded = find_ungrounded_numbers(
        text,
        recommendation,
        include_strings=include_strings,
    )
    if ungrounded:
        joined = ", ".join(str(n) for n in ungrounded)
        raise ValueError(
            f"Explanation contains numbers not found in Recommendation: {joined}"
        )
