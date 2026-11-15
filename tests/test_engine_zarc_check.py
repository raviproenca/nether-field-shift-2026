# AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
"""ZARC window check: synthetic rows with the real column layout, plus the real file when present."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.engine.model import Crop, CropSchedule
from src.engine.zarc_check import (
    DECENDIO_COLUMNS,
    ZarcResult,
    check_window,
    load_zarc_table,
    validation_note,
    window_decendios,
    zarc_decendios,
)

ITABAIANA = "2802908"


def _row(name: str, code: str, risky: range) -> dict:
    row = {"Nome_cultura": name, "geocodigo": code}
    row.update({column: (20 if number in risky else 0) for number, column in enumerate(DECENDIO_COLUMNS, start=1)})
    return row


@pytest.fixture
def table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _row("Milho 1ª Safra", ITABAIANA, range(10, 20)),
            _row("Milho 1ª Safra consorciado com Braquiária", ITABAIANA, range(1, 37)),
            _row("Feijão", ITABAIANA, range(9, 15)),
            _row("Feijão Caupi", ITABAIANA, range(12, 18)),
        ]
    )


def _schedule(crop: str, start: str, end: str) -> CropSchedule:
    return CropSchedule(crop, start, end, 100, 400.0)


def test_window_decendios_counts_from_january() -> None:
    assert window_decendios("2027-04-01", "2027-04-10") == {10}
    assert window_decendios("2027-04-01", "2027-06-30") == set(range(10, 19))
    assert window_decendios("2027-01-31", "2027-02-01") == {3, 4}


def test_zarc_decendios_unions_rows_and_skips_intercropping(table: pd.DataFrame) -> None:
    assert zarc_decendios(table, ITABAIANA, Crop.MAIZE) == set(range(10, 20))
    assert zarc_decendios(table, ITABAIANA, Crop.BEANS) == set(range(9, 18))
    assert zarc_decendios(table, "2800001", Crop.MAIZE) == frozenset()


def test_inside_partial_and_outside(table: pd.DataFrame) -> None:
    inside = check_window(table, ITABAIANA, _schedule("maize", "2027-04-01", "2027-06-30"))
    partial = check_window(table, ITABAIANA, _schedule("maize", "2027-06-01", "2027-08-31"))
    outside = check_window(table, ITABAIANA, _schedule("maize", "2027-11-01", "2027-12-31"))

    assert inside.result is ZarcResult.INSIDE
    assert partial.result is ZarcResult.PARTIAL
    assert outside.result is ZarcResult.OUTSIDE


def test_unknown_without_table_municipality_or_zoning(table: pd.DataFrame) -> None:
    window = _schedule("maize", "2027-04-01", "2027-06-30")

    assert check_window(None, ITABAIANA, window).result is ZarcResult.UNKNOWN
    assert check_window(table, None, window).result is ZarcResult.UNKNOWN
    assert check_window(table, "2800001", window).result is ZarcResult.UNKNOWN
    assert check_window(table, ITABAIANA, _schedule("rice", "2027-04-01", "2027-06-30")).result is ZarcResult.UNKNOWN


def test_validation_note_names_the_divergence(table: pd.DataFrame) -> None:
    checks = [
        check_window(table, ITABAIANA, _schedule("maize", "2027-04-01", "2027-06-30")),
        check_window(table, ITABAIANA, _schedule("beans", "2027-11-01", "2027-12-31")),
    ]

    note = validation_note("Base.", checks)

    assert note.startswith("Base. ZARC divergence")
    assert "beans" in note and "outside the ZARC" in note
    assert "maize" not in note


def test_validation_note_when_all_inside_and_when_unchecked(table: pd.DataFrame) -> None:
    inside = [check_window(table, ITABAIANA, _schedule("maize", "2027-04-01", "2027-06-30"))]

    assert "every window is inside the zoning" in validation_note("Base.", inside)
    assert "could not be done" in validation_note("Base.", [check_window(None, ITABAIANA, _schedule("maize", "2027-04-01", "2027-06-30"))])
    assert "could not be done" in validation_note("Base.", [])


@pytest.mark.skipif(load_zarc_table() is None, reason="no ZARC CSV in data/processed/ or data/reference/zarc/")
def test_real_itabaiana_maize_window_is_april_to_june() -> None:
    real = load_zarc_table()

    assert zarc_decendios(real, ITABAIANA, Crop.MAIZE) == set(range(10, 20))
    assert check_window(real, ITABAIANA, _schedule("maize", "2027-04-01", "2027-06-30")).result is ZarcResult.INSIDE


def test_recommend_reports_divergence_and_inside(table: pd.DataFrame) -> None:
    from dataclasses import replace

    from src.engine.model import Diagnosis, Plot, Priority, Projection
    from src.engine.recommend import recommend
    from src.engine.rules import load_rules

    plot = Plot(lat=-10.685, lon=-37.425, radius_km=5.0, municipality_code=ITABAIANA)
    diagnosis = Diagnosis(period_start="2026-10-09", period_end="2026-11-13", water_balance_mm=-50.0, ndvi_mean=0.5)
    projection = Projection(period_start="2026-11-15", period_end="2026-11-29", horizon_days=15, available=False)
    rules = load_rules()

    partial = recommend(plot, diagnosis, projection, Crop.MAIZE, Priority.WATER, rules, zarc=table)
    unchecked = recommend(replace(plot, municipality_code=None), diagnosis, projection, Crop.MAIZE, Priority.WATER, rules, zarc=table)
    diverging_table = table.assign(**{column: 0 for column in DECENDIO_COLUMNS[9:19]})
    diverging_table.loc[0, "dec30"] = 20
    diverging = recommend(plot, diagnosis, projection, Crop.MAIZE, Priority.WATER, rules, zarc=diverging_table)

    assert "ZARC divergence" in partial.validation_note
    assert "beans" in partial.validation_note and "maize" not in partial.validation_note
    assert "could not be done" in unchecked.validation_note
    assert "ZARC divergence" in diverging.validation_note


def test_fallback_reference_is_used_when_processed_is_missing(tmp_path, table: pd.DataFrame) -> None:
    reference = tmp_path / "reference"
    reference.mkdir()
    table.to_csv(reference / "zarc_2026-2027_se.csv", index=False)

    loaded = load_zarc_table(tmp_path / "missing", fallback=reference)

    assert loaded is not None and len(loaded) == len(table)
    assert load_zarc_table(tmp_path / "missing", fallback=tmp_path / "none") is None


def test_processed_download_wins_over_the_reference_copy(tmp_path, table: pd.DataFrame) -> None:
    processed, reference = tmp_path / "processed", tmp_path / "reference"
    processed.mkdir()
    reference.mkdir()
    table.head(1).to_csv(processed / "zarc_2026-2027_se.csv", index=False)
    table.to_csv(reference / "zarc_2026-2027_se.csv", index=False)

    assert len(load_zarc_table(processed, fallback=reference)) == 1


def test_committed_reference_covers_the_pilots() -> None:
    real = load_zarc_table(Path("/nonexistent"))

    assert real is not None
    assert zarc_decendios(real, "2804508", Crop.MAIZE)
