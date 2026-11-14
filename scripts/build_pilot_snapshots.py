# AI-assisted: generated with Antigravity, reviewed by dudxyz
"""Build lightweight JSON demo snapshots for Sergipe pilot areas (Agreste & Semiárido).

Uses public no-login NASA POWER, NASA NASADEM/SRTM (via Planetary Computer), Open-Meteo 15-day
forecasts, and public NASA CMR granule counts. Writes versioned snapshots to data/sample/pilots/
and mirrors them to git-ignored data/cache/pilots/.
"""

import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.data import earthdata, open_meteo, power, srtm
from src.data.dates import DateRange
from src.data.paths import CACHE_DIR, ROOT
from src.data.regions import point_to_bbox

SAMPLE_PILOTS_DIR = ROOT / "data" / "sample" / "pilots"
CACHE_PILOTS_DIR = CACHE_DIR / "pilots"
POWER_VARS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M"]


@dataclass(frozen=True)
class PilotSite:
    id: str
    name: str
    zone: str
    state: str
    lat: float
    lon: float
    radius_km: float
    typical_system: str


PILOTS: tuple[PilotSite, ...] = (
    PilotSite(
        id="sergipe_agreste_itabaiana",
        name="Itabaiana — Agreste Central Sergipano",
        zone="Agreste",
        state="SE",
        lat=-10.685,
        lon=-37.425,
        radius_km=5.0,
        typical_system="Maize + Bean intercropping (consórcio milho + feijão), cassava, sweet potato",
    ),
    PilotSite(
        id="sergipe_semiarido_ns_gloria",
        name="Nossa Senhora da Glória — Alto Sertão (Semiárido)",
        zone="Semiárido",
        state="SE",
        lat=-10.218,
        lon=-37.420,
        radius_km=5.0,
        typical_system="Sorghum / drought-tolerant maize + cowpea (feijão-caupi), forage palm",
    ),
)


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
    """Compute daily FAO-56 Penman-Monteith reference evapotranspiration (mm/day)."""
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
    return max(0.0, round(num / den, 3))


def max_consecutive_dry_days(precip: pd.Series, threshold_mm: float = 1.0) -> int:
    """Longest consecutive run with precipitation < threshold_mm (ignoring leading/trailing NaNs)."""
    longest = 0
    current = 0
    for val in precip.dropna():
        if float(val) < threshold_mm:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def enrich_with_fao56(frame: pd.DataFrame, lat: float, elevation_m: float) -> pd.DataFrame:
    """Drop incomplete trailing fill-value rows and compute daily FAO-56 ET0 and P - ET0."""
    clean = frame.dropna(subset=POWER_VARS).copy()
    et0_values = [
        fao56_et0_daily(
            lat_deg=lat,
            elevation_m=elevation_m,
            day_of_year=ts.day_of_year,
            t_max_c=float(row["T2M_MAX"]),
            t_min_c=float(row["T2M_MIN"]),
            rh_mean_pct=float(row["RH2M"]),
            u2_m_s=float(row["WS2M"]),
            rs_mj_m2_day=float(row["ALLSKY_SFC_SW_DWN"]),
        )
        for ts, row in clean.iterrows()
    ]
    clean["ET0_FAO56"] = et0_values
    clean["WATER_BALANCE"] = (clean["PRECTOTCORR"] - clean["ET0_FAO56"]).round(3)
    return clean


def _window_summary(frame: pd.DataFrame, days: int) -> dict:
    sub = frame.tail(days)
    precip = round(float(sub["PRECTOTCORR"].sum()), 2)
    et0 = round(float(sub["ET0_FAO56"].sum()), 2)
    return {
        "days": len(sub),
        "precip_mm": precip,
        "et0_fao56_mm": et0,
        "water_balance_mm": round(precip - et0, 2),
        "aridity_ratio": round(precip / max(0.1, et0), 3),
        "max_dry_spell_days": max_consecutive_dry_days(sub["PRECTOTCORR"]),
        "heat_stress_days_ge_34c": int((sub["T2M_MAX"] >= 34.0).sum()),
        "t2m_mean_c": round(float(sub["T2M"].mean()), 2),
    }


def _monthly_summary(frame: pd.DataFrame) -> list[dict]:
    grouped = frame.resample("ME")
    rows = []
    for month_end, chunk in grouped:
        if chunk.empty:
            continue
        precip = round(float(chunk["PRECTOTCORR"].sum()), 2)
        et0 = round(float(chunk["ET0_FAO56"].sum()), 2)
        rows.append(
            {
                "month": month_end.strftime("%Y-%m"),
                "days": len(chunk),
                "precip_mm": precip,
                "et0_fao56_mm": et0,
                "water_balance_mm": round(precip - et0, 2),
                "t2m_mean_c": round(float(chunk["T2M"].mean()), 2),
                "t2m_max_c": round(float(chunk["T2M_MAX"].max()), 2),
                "bare_soil_risk": precip < 0.5 * et0,
            }
        )
    return rows


def check_earthdata_availability(bbox, end_date: date) -> dict:
    """Query public NASA CMR counts & latest dates for key soil/rain/NDVI products (no login needed)."""
    window = DateRange(end_date - timedelta(days=30), end_date)
    status = {}
    for key in ("smap", "imerg", "gldas", "hls", "modis"):
        spec = earthdata.SOURCES[key]
        try:
            granules = earthdata.search(spec.short_name, bbox, window, spec.version)
            latest = earthdata.latest_granule_date(granules).strftime("%Y-%m-%d")
            status[key] = {
                "short_name": spec.short_name,
                "resolution": spec.resolution,
                "granules_last_30d": len(granules),
                "latest_granule": latest,
            }
        except Exception as exc:  # noqa: BLE001
            status[key] = {"short_name": spec.short_name, "resolution": spec.resolution, "error": str(exc)}
    return status


def build_pilot_snapshot(site: PilotSite, ref_date: date | None = None) -> dict:
    """Fetch POWER, NASADEM/SRTM, Open-Meteo, and CMR metadata into a lightweight JSON snapshot."""
    today = ref_date or datetime.now(UTC).date()
    bbox = point_to_bbox(site.lat, site.lon, site.radius_km)

    terrain_da = srtm.fetch_elevation(bbox)
    terrain = srtm.summarize_terrain(terrain_da)

    power_dates = DateRange(today - timedelta(days=365), today - timedelta(days=2))
    raw_power = power.fetch_point(site.lat, site.lon, power_dates, POWER_VARS, cache_dir=CACHE_DIR / "power")
    power_df = enrich_with_fao56(raw_power, site.lat, terrain["elevation_mean_m"])

    forecast_df = open_meteo.fetch_forecast(
        site.lat,
        site.lon,
        forecast_days=15,
        model="best_match",
        cache_dir=CACHE_DIR / "open_meteo",
    )
    forecast_env = open_meteo.to_api_response(forecast_df, site.lat, site.lon, model="best_match")
    fc_precip_15d = round(float(forecast_df["precipitation_sum"].sum()), 2)
    fc_et0_15d = round(float(forecast_df["et0_fao_evapotranspiration"].sum()), 2)

    recent_series = [
        {
            "time": ts.strftime("%Y-%m-%d"),
            "values": {
                "T2M": round(float(row["T2M"]), 2),
                "T2M_MAX": round(float(row["T2M_MAX"]), 2),
                "T2M_MIN": round(float(row["T2M_MIN"]), 2),
                "PRECTOTCORR": round(float(row["PRECTOTCORR"]), 2),
                "ALLSKY_SFC_SW_DWN": round(float(row["ALLSKY_SFC_SW_DWN"]), 2),
                "RH2M": round(float(row["RH2M"]), 2),
                "WS2M": round(float(row["WS2M"]), 2),
                "ET0_FAO56": round(float(row["ET0_FAO56"]), 2),
                "WATER_BALANCE": round(float(row["WATER_BALANCE"]), 2),
            },
        }
        for ts, row in power_df.tail(90).iterrows()
    ]

    return {
        "schema_version": "0.1.0",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pilot": {
            "id": site.id,
            "name": site.name,
            "zone": site.zone,
            "state": site.state,
            "point": {"lat": site.lat, "lon": site.lon},
            "radius_km": site.radius_km,
            "bbox": [round(v, 5) for v in bbox.as_tuple],
            "typical_system": site.typical_system,
        },
        "terrain_srtm": terrain,
        "historical_power_fao56": {
            "source": "power",
            "nasa": True,
            "period": {
                "start": power_df.index.min().strftime("%Y-%m-%d"),
                "end": power_df.index.max().strftime("%Y-%m-%d"),
            },
            "summary_30d": _window_summary(power_df, 30),
            "summary_90d": _window_summary(power_df, 90),
            "summary_365d": _window_summary(power_df, len(power_df)),
            "monthly_365d": _monthly_summary(power_df),
            "daily_last_90d": recent_series,
            "attribution": "NASA POWER API (MERRA-2 + CERES SYN1deg), FAO-56 Penman-Monteith ET0",
        },
        "forecast_open_meteo": {
            **forecast_env,
            "summary_7d": {
                "precip_mm": round(float(forecast_df.head(7)["precipitation_sum"].sum()), 2),
                "et0_fao56_mm": round(float(forecast_df.head(7)["et0_fao_evapotranspiration"].sum()), 2),
                "t2m_max_c": round(float(forecast_df.head(7)["temperature_2m_max"].max()), 2),
            },
            "summary_15d": {
                "precip_mm": fc_precip_15d,
                "et0_fao56_mm": fc_et0_15d,
                "water_balance_mm": round(fc_precip_15d - fc_et0_15d, 2),
                "t2m_max_c": round(float(forecast_df["temperature_2m_max"].max()), 2),
            },
        },
        "earthdata_cmr_availability": check_earthdata_availability(bbox, today),
        "earthdata_grids_embedded": False,
        "earthdata_pending_note": (
            "Run scripts/earthdata-login.sh and query SMAP/IMERG/GLDAS via `python -m src.data` "
            "to populate live soil-moisture and 0.1 deg precipitation grid cells."
        ),
    }


def write_all_pilots(sample_dir: Path = SAMPLE_PILOTS_DIR, cache_dir: Path = CACHE_PILOTS_DIR) -> list[Path]:
    sample_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    manifest_entries: list[dict] = []
    for site in PILOTS:
        snapshot = build_pilot_snapshot(site)
        text = json.dumps(snapshot, indent=2, ensure_ascii=False)
        for folder in (sample_dir, cache_dir):
            out = folder / f"{site.id}.json"
            out.write_text(text, encoding="utf-8")
            if folder == sample_dir:
                written.append(out)
        manifest_entries.append(
            {
                "id": site.id,
                "name": site.name,
                "zone": site.zone,
                "point": snapshot["pilot"]["point"],
                "file": f"{site.id}.json",
                "elevation_mean_m": snapshot["terrain_srtm"]["elevation_mean_m"],
                "slope_mean_pct": snapshot["terrain_srtm"]["slope_mean_pct"],
                "forecast_15d_precip_mm": snapshot["forecast_open_meteo"]["summary_15d"]["precip_mm"],
                "historical_90d_water_balance_mm": snapshot["historical_power_fao56"]["summary_90d"][
                    "water_balance_mm"
                ],
            }
        )
    index_payload = {
        "schema_version": "0.1.0",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "region": "Sergipe, Brazil",
        "pilots": manifest_entries,
    }
    index_text = json.dumps(index_payload, indent=2, ensure_ascii=False)
    for folder in (sample_dir, cache_dir):
        (folder / "index.json").write_text(index_text, encoding="utf-8")
    written.append(sample_dir / "index.json")
    return written


if __name__ == "__main__":
    paths = write_all_pilots()
    for path in paths:
        print(f"wrote {path} ({path.stat().st_size / 1024:.1f} KiB)")
