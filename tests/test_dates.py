# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
from datetime import date

import pytest

from src.data.dates import parse_date, parse_range
from src.data.errors import InputError


def test_valid_range():
    dates = parse_range("2025-01-01", "2025-12-31")
    assert (dates.start, dates.end) == (date(2025, 1, 1), date(2025, 12, 31))
    assert (dates.power_start, dates.power_end) == ("20250101", "20251231")


def test_same_day_is_valid():
    assert parse_range("2025-03-01", "2025-03-01").start == date(2025, 3, 1)


@pytest.mark.parametrize("text", ["", "2025-13-01", "2025-02-30", "01/02/2025", "20250101", "2025-1-1", "abc"])
def test_invalid_date(text):
    with pytest.raises(InputError):
        parse_date(text)


def test_start_after_end():
    with pytest.raises(InputError, match="must not be after"):
        parse_range("2025-02-01", "2025-01-01")
