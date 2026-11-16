# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""ISO date parsing and range validation."""

import re
from dataclasses import dataclass
from datetime import date

from .errors import InputError


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    @property
    def power_start(self) -> str:
        return self.start.strftime("%Y%m%d")

    @property
    def power_end(self) -> str:
        return self.end.strftime("%Y%m%d")


def parse_date(text: str) -> date:
    text = text.strip()
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            raise ValueError(text)
        return date.fromisoformat(text)
    except ValueError:
        raise InputError(f"invalid date '{text}': expected YYYY-MM-DD") from None


def parse_range(start: str, end: str) -> DateRange:
    first, last = parse_date(start), parse_date(end)
    if first > last:
        raise InputError(f"start ({first}) must not be after end ({last})")
    return DateRange(first, last)
