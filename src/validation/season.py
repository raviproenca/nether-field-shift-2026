# AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
"""Rainy-season metrics from a daily rain series: onset, dry spells and rain per decendio.

Pure functions on pandas Series indexed by date; no file or network access.
"""

from dataclasses import dataclass

import pandas as pd

ONSET_WINDOW_DAYS = 15
DRY_DAY_MM = 1.0
LONG_DRY_SPELL_DAYS = 10
SEASON_START = (3, 1)
SEASON_END = (7, 31)
ZARC_DECENDIOS = range(10, 19)  # Apr 1 to Jun 30, the planting window in src/engine/rules/crops.yaml


def decendio(day: pd.Timestamp) -> int:
    """Decendio of the year, 1 to 36 (three per month: days 1-10, 11-20, 21-end)."""
    return (day.month - 1) * 3 + min((day.day - 1) // 10, 2) + 1


def onset_day_of_year(rain: pd.Series, threshold_mm: float) -> int | None:
    """Day of year of the first day whose trailing 15-day rain reaches threshold_mm, or None."""
    trailing = rain.rolling(ONSET_WINDOW_DAYS, min_periods=1).sum()
    hits = trailing[trailing >= threshold_mm]
    return int(hits.index[0].day_of_year) if len(hits) else None


def dry_spells(rain: pd.Series) -> list[int]:
    """Lengths of every run of consecutive days with rain below DRY_DAY_MM."""
    spells: list[int] = []
    run = 0
    for value in rain:
        if value < DRY_DAY_MM:
            run += 1
            continue
        if run:
            spells.append(run)
        run = 0
    if run:
        spells.append(run)
    return spells


@dataclass(frozen=True)
class SeasonOutcome:
    """What the rainy season actually delivered at one point in one year."""

    year: int
    rain_mar_jul_mm: float
    rain_window_mm: float
    et0_window_mm: float | None
    longest_dry_spell_apr_jul_days: int
    dry_spells_10d_apr_jul: int
    onset_doy_35mm: int | None

    @property
    def window_balance_mm(self) -> float | None:
        """Rain minus ET0 over the ZARC planting window (decendios 10 to 18)."""
        if self.et0_window_mm is None:
            return None
        return self.rain_window_mm - self.et0_window_mm


def _window(series: pd.Series) -> pd.Series:
    return series[series.index.map(decendio).isin(ZARC_DECENDIOS)]


def season_outcome(rain: pd.Series, year: int, et0: pd.Series | None = None) -> SeasonOutcome | None:
    """Season metrics for one year, or None when Mar 1 to Jul 31 is incomplete."""
    start = pd.Timestamp(year, *SEASON_START)
    end = pd.Timestamp(year, *SEASON_END)
    season = rain[start:end]
    expected_days = (end - start).days + 1
    if len(season) != expected_days or season.isna().any():
        return None
    apr_jul = season[pd.Timestamp(year, 4, 1):]
    spells = dry_spells(apr_jul)
    et0_window = None
    if et0 is not None:
        et0_season = _window(et0[start:end])
        if len(et0_season) and not et0_season.isna().any():
            et0_window = float(et0_season.sum())
    return SeasonOutcome(
        year=year,
        rain_mar_jul_mm=float(season.sum()),
        rain_window_mm=float(_window(season).sum()),
        et0_window_mm=et0_window,
        longest_dry_spell_apr_jul_days=max(spells, default=0),
        dry_spells_10d_apr_jul=sum(spell >= LONG_DRY_SPELL_DAYS for spell in spells),
        onset_doy_35mm=onset_day_of_year(season, 35.0),
    )
