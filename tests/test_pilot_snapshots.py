# AI-assisted: generated with Antigravity, reviewed by dudxyz
"""Unit tests for FAO-56 ET0 math and pilot snapshot helpers (no network)."""

import pandas as pd
import pytest

from scripts import build_pilot_snapshots as bps


def test_fao56_et0_realistic_tropical_range():
    # Sunny warm Agreste day in Sergipe: should yield ~4.5 to 6.5 mm/day
    et0 = bps.fao56_et0_daily(
        lat_deg=-10.685,
        elevation_m=180.0,
        day_of_year=318,
        t_max_c=33.0,
        t_min_c=23.0,
        rh_mean_pct=60.0,
        u2_m_s=2.5,
        rs_mj_m2_day=22.0,
    )
    assert 4.0 <= et0 <= 7.0


def test_max_consecutive_dry_days():
    series = pd.Series([0.0, 0.2, 5.4, 0.0, 0.5, 0.9, 2.0, 0.1])
    assert bps.max_consecutive_dry_days(series, threshold_mm=1.0) == 3


def test_enrich_with_fao56_drops_trailing_nan_days():
    dates = pd.date_range("2026-11-01", periods=3, freq="D")
    frame = pd.DataFrame(
        {
            "T2M": [27.0, 28.0, float("nan")],
            "T2M_MAX": [32.0, 33.0, float("nan")],
            "T2M_MIN": [22.0, 23.0, float("nan")],
            "PRECTOTCORR": [0.0, 10.0, float("nan")],
            "ALLSKY_SFC_SW_DWN": [22.0, 18.0, float("nan")],
            "RH2M": [62.0, 70.0, float("nan")],
            "WS2M": [2.2, 1.8, float("nan")],
        },
        index=dates,
    )
    enriched = bps.enrich_with_fao56(frame, lat=-10.685, elevation_m=180.0)
    assert len(enriched) == 2
    assert (enriched["ET0_FAO56"] > 3.0).all()
    assert enriched.iloc[1]["WATER_BALANCE"] == pytest.approx(10.0 - enriched.iloc[1]["ET0_FAO56"], abs=1e-2)
