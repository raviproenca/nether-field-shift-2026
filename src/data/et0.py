# AI-assisted: generated with Antigravity and Claude Code, reviewed by dudxyz (adapted for the snapshot generator)
# Based on work by @dudxyz in feat/dudxyz-srtm-openmeteo-pilots
"""FAO-56 Penman-Monteith reference evapotranspiration (ET0) from daily POWER values."""

import math

import numpy as np


def fao56_et0_daily(
    lat_deg: float,
    elevation_m: float,
    day_of_year: int,
    t_max_c: float,
    t_min_c: float,
    rh_mean_pct: float,
    u2_m_s: float,
    rs_mj_m2_day: float,
) -> float:
    """Daily FAO-56 Penman-Monteith reference evapotranspiration, in mm/day (soil heat flux taken as zero)."""
    t_mean = 0.5 * (t_max_c + t_min_c)
    pressure_kpa = 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26
    gamma = 0.000665 * pressure_kpa

    e_tmax = 0.6108 * math.exp((17.27 * t_max_c) / (t_max_c + 237.3))
    e_tmin = 0.6108 * math.exp((17.27 * t_min_c) / (t_min_c + 237.3))
    es = 0.5 * (e_tmax + e_tmin)
    ea = es * max(0.05, min(1.0, rh_mean_pct / 100.0))
    delta = (4098.0 * (0.6108 * math.exp((17.27 * t_mean) / (t_mean + 237.3)))) / ((t_mean + 237.3) ** 2)

    lat_rad = math.radians(lat_deg)
    dr = 1.0 + 0.033 * math.cos((2.0 * math.pi / 365.0) * day_of_year)
    decl = 0.409 * math.sin((2.0 * math.pi / 365.0) * day_of_year - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(lat_rad) * math.tan(decl))))
    ra = (
        (24.0 * 60.0 / math.pi)
        * 0.0820
        * dr
        * (ws * math.sin(lat_rad) * math.sin(decl) + math.cos(lat_rad) * math.cos(decl) * math.sin(ws))
    )
    rso = (0.75 + 2e-5 * elevation_m) * ra
    rns = 0.77 * rs_mj_m2_day
    rs_ratio = min(1.0, max(0.25, rs_mj_m2_day / max(0.1, rso)))
    sigma = 4.903e-9
    rnl = (
        sigma
        * (((t_max_c + 273.16) ** 4 + (t_min_c + 273.16) ** 4) / 2.0)
        * (0.34 - 0.14 * math.sqrt(max(0.0, ea)))
        * (1.35 * rs_ratio - 0.35)
    )
    rn = rns - rnl

    num = 0.408 * delta * rn + gamma * (900.0 / (t_mean + 273.0)) * u2_m_s * max(0.0, es - ea)
    den = delta + gamma * (1.0 + 0.34 * u2_m_s)
    return max(0.0, num / den)


def et0_series(
    lat_deg: float,
    elevation_m: float,
    days_of_year: np.ndarray,
    t_max: np.ndarray,
    t_min: np.ndarray,
    rh: np.ndarray,
    wind: np.ndarray,
    solar: np.ndarray,
) -> np.ndarray:
    """ET0 for each day of aligned arrays (mm/day); NaN wherever one of the inputs is missing."""
    result = np.full(days_of_year.shape, np.nan)
    inputs = np.stack([t_max, t_min, rh, wind, solar])
    for i in np.flatnonzero(np.isfinite(inputs).all(axis=0)):
        result[i] = fao56_et0_daily(lat_deg, elevation_m, int(days_of_year[i]), *inputs[:, i])
    return result
