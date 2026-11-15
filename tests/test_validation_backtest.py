# AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
"""Tests for the season metrics and the engine backtest (no network, small fixed data)."""

import numpy as np
import pandas as pd
import pytest

from src.engine import load_rules
from src.validation.backtest import (
    PILOTS,
    best_strategy_by_proxy,
    diagnosis_for,
    enso_class,
    projection_for,
    rank1,
    run_year,
    strategy_proxy,
    yield_anomalies,
)
from src.validation.season import (
    decendio,
    dry_spells,
    onset_day_of_year,
    season_outcome,
)

PILOT = PILOTS[1]


def daily_frame(year: int, rain_mm: float = 3.0) -> pd.DataFrame:
    days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    return pd.DataFrame(
        {
            "PRECTOTCORR": rain_mm,
            "T2M": 26.0,
            "T2M_MAX": 31.0,
            "T2M_MIN": 21.0,
            "RH2M": 70.0,
            "WS2M": 2.0,
            "ALLSKY_SFC_SW_DWN": 20.0,
            "ET0": 4.0,
        },
        index=days,
    )


def test_decendio_splits_each_month_in_three():
    assert decendio(pd.Timestamp(2024, 1, 1)) == 1
    assert decendio(pd.Timestamp(2024, 4, 1)) == 10
    assert decendio(pd.Timestamp(2024, 4, 20)) == 11
    assert decendio(pd.Timestamp(2024, 6, 30)) == 18


def test_dry_spells_counts_runs_below_one_mm():
    rain = pd.Series([0, 0, 5, 0.5, 0.2, 0, 2, 0])
    assert dry_spells(rain) == [2, 3, 1]


def test_onset_is_first_day_reaching_the_trailing_sum():
    days = pd.date_range("2024-03-01", periods=20, freq="D")
    rain = pd.Series([0.0] * 9 + [20.0, 20.0] + [0.0] * 9, index=days)
    assert onset_day_of_year(rain, 35.0) == pd.Timestamp("2024-03-11").day_of_year
    assert onset_day_of_year(rain * 0, 35.0) is None


def test_season_outcome_measures_the_zarc_window():
    frame = daily_frame(2024)
    outcome = season_outcome(frame["PRECTOTCORR"], 2024, frame["ET0"])
    window_days = 91  # April 1 to June 30
    assert outcome.rain_window_mm == pytest.approx(3.0 * window_days)
    assert outcome.window_balance_mm == pytest.approx(-1.0 * window_days)
    assert outcome.longest_dry_spell_apr_jul_days == 0


def test_season_outcome_is_none_when_the_season_is_incomplete():
    frame = daily_frame(2024).loc[:"2024-05-31"]
    assert season_outcome(frame["PRECTOTCORR"], 2024) is None


def test_enso_class_thresholds():
    assert enso_class(2.4) == "el_nino_strong"
    assert enso_class(0.8) == "el_nino_moderate_weak"
    assert enso_class(0.0) == "neutral"
    assert enso_class(-1.0) == "la_nina"


def test_diagnosis_uses_only_data_up_to_march_31():
    frame = daily_frame(2024)
    frame.loc["2024-04-01":, "PRECTOTCORR"] = 999.0
    diagnosis = diagnosis_for(frame, 2024, PILOT)
    assert diagnosis.period_end == "2024-03-31"
    assert diagnosis.rain_total_mm == pytest.approx(3.0 * 91)  # Jan 1 to Mar 31, leap year


def test_projection_variants():
    frame = daily_frame(2024)
    assert projection_for(frame, 2024, perfect=False).available is False
    perfect = projection_for(frame, 2024, perfect=True)
    assert perfect.available is True
    assert perfect.rain_total_mm == pytest.approx(45.0)


def test_yield_anomaly_is_relative_to_neighbouring_years():
    years = range(2000, 2011)
    pam = pd.DataFrame(
        {"ibge_code": PILOT.ibge_code, "year": list(years), "crop": "maize",
         "yield_kg_ha": [1000.0] * 5 + [500.0] + [1000.0] * 5}
    )
    anomalies = yield_anomalies(pam)
    assert anomalies[(PILOT.ibge_code, 2005, "maize")] == pytest.approx(-0.5)
    assert anomalies[(PILOT.ibge_code, 2004, "maize")] == pytest.approx(0.0)


def test_strategy_proxy_needs_every_crop():
    anomalies = {(PILOT.ibge_code, 2024, "maize"): -0.2, (PILOT.ibge_code, 2024, "beans"): 0.1}
    assert strategy_proxy(("maize", "beans"), anomalies, PILOT.ibge_code, 2024) == pytest.approx(-0.05)
    assert strategy_proxy(("maize", "cassava"), anomalies, PILOT.ibge_code, 2024) is None


def test_run_year_ranks_three_strategies_and_scores_them():
    frame = daily_frame(2024)
    anomalies = {
        (PILOT.ibge_code, 2024, "maize"): -0.3,
        (PILOT.ibge_code, 2024, "beans"): 0.1,
        (PILOT.ibge_code, 2024, "cassava"): 0.0,
    }
    result = run_year(frame, PILOT, 2024, "el_nino_strong", anomalies, load_rules())
    recommendation = result.recommendations[("maize", "water", False)]
    assert len(recommendation.strategies) == 3
    assert rank1(result, "maize", "water", False) in {s.kind.value for s in recommendation.strategies}
    best = best_strategy_by_proxy(result, "maize", "water", False, anomalies)
    assert best == ["soil_water_conservation"]  # maize + beans has the highest mean anomaly
    assert np.isfinite(result.outcome.rain_mar_jul_mm)
