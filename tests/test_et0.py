# AI-assisted: generated with Antigravity and Claude Code, reviewed by dudxyz (adapted for the snapshot generator)
# Based on work by @dudxyz in feat/dudxyz-srtm-openmeteo-pilots
"""FAO-56 ET0 tests (no network)."""

import numpy as np
import pytest

from src.data import et0


def test_fao56_et0_realistic_tropical_range():
    # Sunny warm Agreste day in Sergipe: about 4.5 to 6.5 mm/day
    value = et0.fao56_et0_daily(
        lat_deg=-10.685,
        elevation_m=180.0,
        day_of_year=318,
        t_max_c=33.0,
        t_min_c=23.0,
        rh_mean_pct=60.0,
        u2_m_s=2.5,
        rs_mj_m2_day=22.0,
    )
    assert 4.0 <= value <= 7.0


def test_fao56_et0_is_never_negative_and_grows_with_wind_and_dryness():
    calm_humid = et0.fao56_et0_daily(-10.0, 100.0, 100, 30.0, 22.0, 95.0, 0.5, 10.0)
    windy_dry = et0.fao56_et0_daily(-10.0, 100.0, 100, 30.0, 22.0, 40.0, 4.0, 10.0)
    assert calm_humid >= 0 and windy_dry > calm_humid


def test_et0_series_is_nan_where_an_input_is_missing():
    days = np.array([318, 319, 320])
    one = np.array([33.0, 33.0, np.nan])
    result = et0.et0_series(
        -10.685, 180.0, days, one, one - 10, np.array([60.0, 60.0, 60.0]), np.full(3, 2.5), np.full(3, 22.0)
    )
    assert result[0] == pytest.approx(result[1], rel=0.02) and np.isnan(result[2])
