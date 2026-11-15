# AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
"""Compare engine planting windows with the ZARC (MAPA) reference for a municipality.

The reference is the Sergipe CSV that ``python -m src.data.zarc`` writes to
``data/processed/`` (safra 2026/2027, plus the perennial file for cassava).
A ten-day period (decêndio) counts as inside the zoning when the ZARC lists a
risk class (20, 30 or 40) for it; 0 means no zoning. Soil class and cycle are
not known for a plot, so the periods are the union over the municipality's
rows for the crop.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.data.paths import ROOT
from src.engine.model import Crop, CropSchedule

SAFRA = "2026/2027"
ZARC_FILES = ("zarc_2026-2027_se.csv", "zarc_perene_se.csv")
PROCESSED_DIR = ROOT / "data" / "processed"
SOURCE_URL = "https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico"
DECENDIO_COLUMNS = [f"dec{i}" for i in range(1, 37)]
RISK_CLASSES = (20, 30, 40)

# ZARC crop names that stand for each engine crop (compared without accents, lower case).
_CROP_PREFIX = {Crop.MAIZE: "milho", Crop.BEANS: "feij", Crop.CASSAVA: "mandioca"}
_EXCLUDED = "consorciado"


class ZarcResult(StrEnum):
    INSIDE = "inside"
    PARTIAL = "partial"
    OUTSIDE = "outside"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ZarcCheck:
    crop: str
    result: ZarcResult
    detail: str


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def load_zarc_table(directory: Path | None = None) -> pd.DataFrame | None:
    """Read the Sergipe ZARC CSVs; None when none is there (run src.data.zarc first)."""
    folder = directory or PROCESSED_DIR
    frames = [
        pd.read_csv(path, dtype={"geocodigo": str})
        for name in ZARC_FILES
        if (path := folder / name).is_file()
    ]
    return pd.concat(frames, ignore_index=True) if frames else None


def zarc_decendios(table: pd.DataFrame, municipality_code: str, crop: Crop) -> frozenset[int]:
    """Ten-day periods (1 to 36) with a risk class for the crop in the municipality."""
    prefix = _CROP_PREFIX[crop]
    names = table["Nome_cultura"].map(_plain)
    rows = table[
        (table["geocodigo"] == municipality_code) & names.str.startswith(prefix) & ~names.str.contains(_EXCLUDED)
    ]
    found: set[int] = set()
    for number, column in enumerate(DECENDIO_COLUMNS, start=1):
        if rows[column].isin(RISK_CLASSES).any():
            found.add(number)
    return frozenset(found)


def window_decendios(start: str, end: str) -> frozenset[int]:
    """Ten-day periods touched by the window, counted from 1 January (1 to 36)."""
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    found: set[int] = set()
    day = first
    while day <= last:
        found.add((day.month - 1) * 3 + min((day.day - 1) // 10, 2) + 1)
        day += timedelta(days=1)
    return frozenset(found)


def check_window(
    table: pd.DataFrame | None,
    municipality_code: str | None,
    schedule: CropSchedule,
) -> ZarcCheck:
    """Inside, partial or outside the ZARC for one crop window; unknown when there is no reference."""
    try:
        crop = Crop(schedule.crop)
    except ValueError:
        return ZarcCheck(schedule.crop, ZarcResult.UNKNOWN, f"{schedule.crop}: not covered by the ZARC check.")
    if table is None:
        return ZarcCheck(crop.value, ZarcResult.UNKNOWN, f"{crop.value}: the ZARC table is not loaded.")
    if not municipality_code:
        return ZarcCheck(crop.value, ZarcResult.UNKNOWN, f"{crop.value}: the municipality is not known.")
    allowed = zarc_decendios(table, municipality_code, crop)
    if not allowed:
        return ZarcCheck(
            crop.value, ZarcResult.UNKNOWN, f"{crop.value}: the ZARC has no zoning for municipality {municipality_code}."
        )
    wanted = window_decendios(schedule.planting_start, schedule.planting_end)
    overlap = wanted & allowed
    span = f"{schedule.planting_start} to {schedule.planting_end}"
    if overlap == wanted:
        return ZarcCheck(crop.value, ZarcResult.INSIDE, f"{crop.value}: the window {span} is inside the ZARC.")
    if overlap:
        return ZarcCheck(
            crop.value,
            ZarcResult.PARTIAL,
            f"{crop.value}: the window {span} is only partly inside the ZARC "
            f"({len(overlap)} of {len(wanted)} ten-day periods).",
        )
    return ZarcCheck(crop.value, ZarcResult.OUTSIDE, f"{crop.value}: the window {span} is outside the ZARC.")


def validation_note(base: str, checks: Iterable[ZarcCheck]) -> str:
    """The Recommendation validation note: ``base`` plus one line per divergent or unchecked crop."""
    items = list(checks)
    if not items or all(item.result is ZarcResult.UNKNOWN for item in items):
        reasons = " ".join(dict.fromkeys(item.detail for item in items))
        return f"{base} The ZARC check could not be done. {reasons}".strip()
    divergent = [item.detail for item in items if item.result in (ZarcResult.PARTIAL, ZarcResult.OUTSIDE)]
    if divergent:
        return f"{base} ZARC divergence (MAPA, safra {SAFRA}): {' '.join(divergent)}"
    return f"{base} ZARC check (MAPA, safra {SAFRA}): every window is inside the zoning. Source: {SOURCE_URL}"
