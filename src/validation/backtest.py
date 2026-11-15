# AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
"""Historical backtest of the decision engine at the two Sergipe pilots (issue #79).

For each year, the engine sees only data available on the decision date (March 31): the
January-March diagnosis from NASA POWER, and optionally the actual next 15 days of rain as a
"perfect forecast" ceiling. Its ranking is then compared with what the season delivered
(POWER rain, dry spells, water balance in the ZARC window) and with the municipal yields that
IBGE PAM recorded for that year. Pure functions: data loading lives in scripts/backtest.py.
"""

from dataclasses import dataclass
from statistics import median

import numpy as np
import pandas as pd

from src.data.et0 import et0_series
from src.engine import (
    Crop,
    Diagnosis,
    EngineRules,
    Plot,
    Priority,
    Projection,
    Recommendation,
    SourceAttribution,
    recommend,
)
from src.validation.season import SeasonOutcome, season_outcome

POWER_VARIABLES = ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN"]
DIAGNOSIS_START = (1, 1)
DECISION_DATE = (3, 31)
FORECAST_DAYS = 15
PREVIOUS_CROP = "maize"

POWER_SOURCE = SourceAttribution(
    source="power",
    dataset="NASA POWER Agroclimatology daily (PRECTOTCORR, T2M, RH2M, WS2M, ALLSKY_SFC_SW_DWN)",
    nasa=True,
    url="https://power.larc.nasa.gov/",
)


@dataclass(frozen=True)
class Pilot:
    id: str
    name: str
    region: str
    lat: float
    lon: float
    ibge_code: str
    elevation_m: float
    slope_mean_pct: float


# Coordinates from src/data/snapshots.py; elevation and slope from the SRTM snapshot cells SE036 and SE020.
PILOTS = (
    Pilot("sergipe_agreste_itabaiana", "Itabaiana", "Agreste", -10.685, -37.425, "2802908", 182.3, 7.77),
    Pilot("sergipe_semiarido_ns_gloria", "Nossa Senhora da Glória", "Semiárido", -10.218, -37.42, "2804508", 242.2, 8.31),
)


def enso_class(djf_oni: float) -> str:
    """NOAA ONI class of the December-February before the rainy season."""
    if djf_oni >= 1.5:
        return "el_nino_strong"
    if djf_oni >= 0.5:
        return "el_nino_moderate_weak"
    if djf_oni > -0.5:
        return "neutral"
    return "la_nina"


def with_et0(daily: pd.DataFrame, pilot: Pilot) -> pd.DataFrame:
    """Adds an ET0 column (FAO-56 Penman-Monteith, mm/day) computed from POWER daily values."""
    frame = daily.copy()
    frame["ET0"] = et0_series(
        pilot.lat,
        pilot.elevation_m,
        frame.index.day_of_year.to_numpy(),
        frame["T2M_MAX"].to_numpy(dtype=float),
        frame["T2M_MIN"].to_numpy(dtype=float),
        frame["RH2M"].to_numpy(dtype=float),
        frame["WS2M"].to_numpy(dtype=float),
        frame["ALLSKY_SFC_SW_DWN"].to_numpy(dtype=float),
    )
    return frame


def diagnosis_for(daily: pd.DataFrame, year: int, pilot: Pilot) -> Diagnosis:
    """January to March 31 diagnosis: what the engine can know on the decision date."""
    start = pd.Timestamp(year, *DIAGNOSIS_START)
    end = pd.Timestamp(year, *DECISION_DATE)
    window = daily[start:end]
    rain = float(window["PRECTOTCORR"].sum())
    et0 = window["ET0"]
    return Diagnosis(
        period_start=start.date().isoformat(),
        period_end=end.date().isoformat(),
        rain_total_mm=round(rain, 2),
        rain_daily_mean_mm=round(rain / len(window), 2),
        et0_daily_mean_mm=round(float(et0.mean()), 2),
        water_balance_mm=round(rain - float(et0.sum()), 2),
        temperature_mean_c=round(float(window["T2M"].mean()), 2),
        temperature_max_c=round(float(window["T2M_MAX"].mean()), 2),
        elevation_m=pilot.elevation_m,
        slope_mean_pct=pilot.slope_mean_pct,
        sources=(POWER_SOURCE,),
    )


def projection_for(daily: pd.DataFrame, year: int, perfect: bool) -> Projection:
    """No forecast, or the observed next 15 days of rain used as a perfect forecast (the ceiling)."""
    start = pd.Timestamp(year, *DECISION_DATE) + pd.Timedelta(days=1)
    end = start + pd.Timedelta(days=FORECAST_DAYS - 1)
    if not perfect:
        return Projection(
            period_start=start.date().isoformat(),
            period_end=end.date().isoformat(),
            horizon_days=FORECAST_DAYS,
            available=False,
        )
    rain = float(daily["PRECTOTCORR"][start:end].sum())
    return Projection(
        period_start=start.date().isoformat(),
        period_end=end.date().isoformat(),
        horizon_days=FORECAST_DAYS,
        available=True,
        rain_total_mm=round(rain, 2),
        sources=(POWER_SOURCE,),
    )


def plot_for(pilot: Pilot) -> Plot:
    return Plot(
        lat=pilot.lat,
        lon=pilot.lon,
        radius_km=5.0,
        id=pilot.id,
        name=pilot.name,
        region=pilot.region,
        municipality_code=pilot.ibge_code,
        elevation_m=pilot.elevation_m,
        slope_mean_pct=pilot.slope_mean_pct,
        season="wet",
        previous_crops=(PREVIOUS_CROP,),
    )


def yield_anomalies(pam: pd.DataFrame, half_window: int = 5) -> dict[tuple[str, int, str], float]:
    """(IBGE code, year, crop) -> yield relative to the median of the surrounding years, minus 1.

    The reference is the median of the same crop and municipality within +/- half_window years,
    excluding the year itself, so long-term trends (new hybrids, area shifts) do not read as
    weather signals.
    """
    anomalies: dict[tuple[str, int, str], float] = {}
    for (code, crop), group in pam.groupby(["ibge_code", "crop"]):
        values = group.dropna(subset=["yield_kg_ha"])
        series = values[values["yield_kg_ha"] > 0].set_index("year")["yield_kg_ha"]
        for year, value in series.items():
            neighbours = series[(abs(series.index - year) <= half_window) & (series.index != year)]
            if len(neighbours) >= 3:
                anomalies[(code, int(year), crop)] = float(value / median(neighbours) - 1.0)
    return anomalies


def strategy_proxy(crops: tuple[str, ...], anomalies: dict, code: str, year: int) -> float | None:
    """Mean PAM yield anomaly of a strategy's crops in that year; None if a crop has no record."""
    values = [anomalies.get((code, year, crop)) for crop in crops]
    if any(value is None for value in values):
        return None
    return float(np.mean(values))


@dataclass(frozen=True)
class YearResult:
    pilot: Pilot
    year: int
    enso: str
    outcome: SeasonOutcome
    diagnosis: Diagnosis
    recommendations: dict[tuple[str, str, bool], Recommendation]
    yield_anomaly: dict[str, float | None]


def run_year(
    daily: pd.DataFrame,
    pilot: Pilot,
    year: int,
    enso: str,
    anomalies: dict,
    rules: EngineRules,
) -> YearResult | None:
    """Engine runs for every crop, priority and forecast variant in one year, plus the season outcome."""
    outcome = season_outcome(daily["PRECTOTCORR"], year, daily["ET0"])
    if outcome is None:
        return None
    diagnosis = diagnosis_for(daily, year, pilot)
    plot = plot_for(pilot)
    recommendations = {}
    for perfect in (False, True):
        projection = projection_for(daily, year, perfect)
        for crop in Crop:
            for priority in Priority:
                recommendations[(crop.value, priority.value, perfect)] = recommend(
                    plot, diagnosis, projection, crop, priority, rules
                )
    return YearResult(
        pilot=pilot,
        year=year,
        enso=enso,
        outcome=outcome,
        diagnosis=diagnosis,
        recommendations=recommendations,
        yield_anomaly={crop.value: anomalies.get((pilot.ibge_code, year, crop.value)) for crop in Crop},
    )


def best_strategy_by_proxy(result: YearResult, crop: str, priority: str, perfect: bool, anomalies: dict) -> list[str]:
    """Strategy kinds whose crops had the highest mean PAM anomaly that year (ties included)."""
    recommendation = result.recommendations[(crop, priority, perfect)]
    scored = {
        strategy.kind.value: strategy_proxy(strategy.crops, anomalies, result.pilot.ibge_code, result.year)
        for strategy in recommendation.strategies
    }
    known = {kind: value for kind, value in scored.items() if value is not None}
    if len(known) < len(scored):
        return []
    top = max(known.values())
    return [kind for kind, value in known.items() if abs(value - top) < 1e-9]


def rank1(result: YearResult, crop: str, priority: str, perfect: bool) -> str:
    return result.recommendations[(crop, priority, perfect)].strategies[0].kind.value
