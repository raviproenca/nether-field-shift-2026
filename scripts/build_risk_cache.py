# AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
"""Pre-compute the seasonal rain-risk view of each pilot into apps/web/public/risk/.

For every decendio (10-day period) from April to July it stores the median NASA POWER rain in
strong El Niño seasons (NOAA ONI of December-February >= 1.5) and in all other seasons, plus
the planting window of each crop from src/engine/rules/crops.yaml. It shows risk from past
seasons; it is not a forecast. Run from the repo root (needs the network once):
    python scripts/build_risk_cache.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from statistics import median

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.dates import DateRange  # noqa: E402
from src.data.paths import CACHE_DIR  # noqa: E402
from src.data.power import fetch_point  # noqa: E402
from src.data.snapshots import PILOTS  # noqa: E402
from src.engine.rules import load_rules  # noqa: E402

OUT_DIR = ROOT / "apps" / "web" / "public" / "risk"
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
FIRST_YEAR, LAST_YEAR = 1981, 2025
DECENDIOS = range(10, 22)  # April 1 to July 31
STRONG_EL_NINO = 1.5


def decendio(day) -> int:
    return (day.month - 1) * 3 + min((day.day - 1) // 10, 2) + 1


def djf_oni() -> dict[int, float]:
    path = CACHE_DIR / "oni" / "oni.ascii.txt"
    if not path.is_file():
        response = requests.get(ONI_URL, timeout=60)
        response.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(response.text)
    rows = (line.split() for line in path.read_text().splitlines()[1:])
    return {int(r[1]): float(r[3]) for r in rows if len(r) == 4 and r[0] == "DJF"}


def rain_by_decendio(lat: float, lon: float) -> dict[int, dict[int, float]]:
    """year -> decendio -> rain (mm) for complete April-July seasons."""
    daily = fetch_point(lat, lon, DateRange(date(FIRST_YEAR, 1, 1), date(LAST_YEAR, 12, 31)), ["PRECTOTCORR"],
                        cache_dir=CACHE_DIR / "power")["PRECTOTCORR"]
    seasons: dict[int, dict[int, float]] = {}
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        season = daily[f"{year}-04-01":f"{year}-07-31"]
        if len(season) != 122 or season.isna().any():
            continue
        grouped = season.groupby(season.index.map(decendio)).sum()
        seasons[year] = {int(d): round(float(v), 1) for d, v in grouped.items()}
    return seasons


def main() -> int:
    oni = djf_oni()
    rules = load_rules()
    windows = {
        crop.value: {"start": profile.planting_calendar.start_decendio, "end": profile.planting_calendar.end_decendio}
        for crop, profile in rules.crops.items()
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Shared by every point: the browser computes the risk of any address from NASA POWER with these.
    strong_years = sorted(y for y, value in oni.items() if FIRST_YEAR <= y <= LAST_YEAR and value >= STRONG_EL_NINO)
    common = {
        "first_year": FIRST_YEAR,
        "last_year": LAST_YEAR,
        "decendios": list(DECENDIOS),
        "strong_el_nino_years": strong_years,
        "windows": windows,
        "sources": [
            {"name": "NASA POWER daily rain (PRECTOTCORR)", "url": "https://power.larc.nasa.gov/", "nasa": True},
            {"name": "NOAA CPC Oceanic Niño Index", "url": ONI_URL, "nasa": False},
        ],
    }
    (OUT_DIR / "common.json").write_text(json.dumps(common, indent=2) + "\n", encoding="utf-8")
    for pilot in PILOTS:
        seasons = rain_by_decendio(pilot.lat, pilot.lon)
        strong = [y for y in seasons if oni.get(y, 0.0) >= STRONG_EL_NINO]
        others = [y for y in seasons if y not in strong]
        rows = [
            {
                "decendio": d,
                "strong_el_nino_mm": round(median(seasons[y][d] for y in strong), 1),
                "other_years_mm": round(median(seasons[y][d] for y in others), 1),
            }
            for d in DECENDIOS
        ]
        payload = {
            "pilot_id": pilot.id,
            "decendios": rows,
            "strong_el_nino_years": strong,
            "other_years_count": len(others),
            "windows": windows,
            "current_oni_note": "NOAA CPC: strong El Niño expected through January-March 2027 (12 Nov 2026 update).",
            "sources": [
                {"name": "NASA POWER daily rain (PRECTOTCORR), 1981-2025", "url": "https://power.larc.nasa.gov/", "nasa": True},
                {"name": "NOAA CPC Oceanic Niño Index", "url": ONI_URL, "nasa": False},
            ],
        }
        (OUT_DIR / f"{pilot.id}.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"{pilot.id}: strong El Niño years {strong}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
