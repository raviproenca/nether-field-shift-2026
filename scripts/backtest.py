# AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
"""Historical backtest of the decision engine at the Sergipe pilots (issue #79).

Run from the repo root:
    .venv/bin/python -m scripts.backtest
It downloads (and caches in data/cache/) NASA POWER daily data, the NOAA ONI index and IBGE PAM
yields, runs the engine for every year, and writes docs/validation/backtest-report.md plus
data/processed/backtest_years.csv.
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from statistics import median

import pandas as pd
import requests

from src.data.dates import DateRange
from src.data.errors import DataToolkitError
from src.data.paths import CACHE_DIR, PROCESSED_DIR
from src.data.power import fetch_point
from src.data.sidra import PAM_TABLE
from src.data.sidra import fetch as fetch_sidra
from src.engine import load_rules
from src.validation.backtest import (
    PILOTS,
    POWER_VARIABLES,
    YearResult,
    best_strategy_by_proxy,
    enso_class,
    rank1,
    run_year,
    with_et0,
    yield_anomalies,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "validation" / "backtest-report.md"
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
PAM_CROPS = {"40112": "beans", "40119": "cassava", "40122": "maize"}
FIRST_YEAR = 1981
STRATEGY_LABEL = {
    "current_practice": "current practice",
    "soil_water_conservation": "soil and water conservation",
    "resilient_income_forage": "resilient income",
}


def load_oni(cache_dir: Path) -> dict[int, float]:
    """DJF ONI by year of January (DJF 1998 = Dec 1997 to Feb 1998)."""
    path = cache_dir / "oni" / "oni.ascii.txt"
    if not path.is_file():
        response = requests.get(ONI_URL, timeout=60)
        response.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(response.text)
    djf = {}
    for line in path.read_text().splitlines()[1:]:
        parts = line.split()
        if len(parts) == 4 and parts[0] == "DJF":
            djf[int(parts[1])] = float(parts[3])
    return djf


def load_pam(cache_dir: Path, last_year: int) -> pd.DataFrame:
    """IBGE PAM average yield (kg/ha) of maize, beans and cassava in the pilot municipalities."""
    frame = fetch_sidra(
        PAM_TABLE, "112", f"{FIRST_YEAR}-{last_year}", classification=782,
        categories=",".join(PAM_CROPS), cache_dir=cache_dir,
    )
    codes = {pilot.ibge_code for pilot in PILOTS}
    frame = frame[frame["municipio_code"].astype(str).isin(codes)]
    return pd.DataFrame({
        "ibge_code": frame["municipio_code"].astype(str),
        "year": frame["ano"].astype(int),
        "crop": frame["produto_das_lavouras_temporarias_e_permanentes_code"].astype(str).map(PAM_CROPS),
        "yield_kg_ha": pd.to_numeric(frame["value"], errors="coerce"),
    })


def load_power(pilot, last_year: int, cache_dir: Path) -> pd.DataFrame:
    dates = DateRange(date(FIRST_YEAR, 1, 1), date(last_year, 12, 31))
    daily = fetch_point(pilot.lat, pilot.lon, dates, POWER_VARIABLES, cache_dir=cache_dir / "power")
    return with_et0(daily.dropna(how="all"), pilot)


def run(last_year: int, cache_dir: Path) -> tuple[list[YearResult], dict]:
    rules = load_rules()
    oni = load_oni(cache_dir)
    pam = load_pam(cache_dir, last_year)
    anomalies = yield_anomalies(pam)
    results = []
    for pilot in PILOTS:
        daily = load_power(pilot, last_year, cache_dir)
        for year in range(FIRST_YEAR, last_year + 1):
            if year not in oni:
                continue
            result = run_year(daily, pilot, year, enso_class(oni[year]), anomalies, rules)
            if result is not None:
                results.append(result)
    return results, anomalies


def _missing(value) -> bool:
    return value is None or pd.isna(value)


def _fmt(value) -> str:
    return "n/a" if _missing(value) else f"{value:.0f}"


def _pct(value) -> str:
    return "n/a" if _missing(value) else f"{value * 100:+.0f}%"


def year_rows(results: list[YearResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append({
            "pilot": r.pilot.name,
            "year": r.year,
            "enso": r.enso,
            "rain_mar_jul_mm": round(r.outcome.rain_mar_jul_mm, 1),
            "rain_window_mm": round(r.outcome.rain_window_mm, 1),
            "window_balance_mm": None if r.outcome.window_balance_mm is None else round(r.outcome.window_balance_mm, 1),
            "longest_dry_spell_days": r.outcome.longest_dry_spell_apr_jul_days,
            "diagnosis_balance_mm": r.diagnosis.water_balance_mm,
            "pam_maize": r.yield_anomaly["maize"],
            "pam_beans": r.yield_anomaly["beans"],
            "pam_cassava": r.yield_anomaly["cassava"],
            "rank1_maize_water": rank1(r, "maize", "water", False),
            "rank1_maize_water_perfect": rank1(r, "maize", "water", True),
            "rank1_maize_income": rank1(r, "maize", "income", False),
        })
    return pd.DataFrame(rows)


def season_class(frame: pd.DataFrame) -> pd.Series:
    """dry / normal / wet by tercile of rain in the ZARC window, per pilot."""
    def classify(group: pd.DataFrame) -> pd.Series:
        low, high = group["rain_window_mm"].quantile([1 / 3, 2 / 3])
        return group["rain_window_mm"].map(lambda v: "dry" if v <= low else "wet" if v >= high else "normal")
    return frame.groupby("pilot", group_keys=False).apply(classify)


def agreement(results: list[YearResult], anomalies: dict, crop: str, priority: str, perfect: bool) -> tuple[int, int, float]:
    """Years where the engine's rank 1 had the best PAM proxy, years scored, and the chance rate."""
    hits = scored = 0
    chance = 0.0
    for r in results:
        best = best_strategy_by_proxy(r, crop, priority, perfect, anomalies)
        if not best:
            continue
        scored += 1
        chance += len(best) / 3
        hits += rank1(r, crop, priority, perfect) in best
    return hits, scored, (chance / scored if scored else 0.0)


def render(results: list[YearResult], anomalies: dict, frame: pd.DataFrame) -> str:
    lines = [
        "<!-- AI-assisted: generated by scripts/backtest.py (Claude Code), reviewed by <pending Gabriel>. Do not edit the tables by hand; rerun the script. -->",
        "",
        "# Decision engine backtest: Sergipe pilots, 1981 onward",
        "",
        "Issue #79. Generated by `python -m scripts.backtest`. Findings and limits are in the last sections.",
        "",
        "## Setup",
        "",
        "- **Pilots:** Itabaiana (Agreste) and Nossa Senhora da Glória (Semiárido), the points in `src/data/snapshots.py`.",
        "- **Decision date: March 31.** The engine sees only January 1 to March 31 of that year: NASA POWER rain, temperature and FAO-56 ET0 (from POWER), plus SRTM elevation and slope. Previous crop: maize.",
        "- **Two forecast variants:** none (`available=False`), and the observed rain of April 1 to 15 used as a *perfect* 15-day forecast. The second is a ceiling, not something a real forecast achieves.",
        "- **What the season delivered** (NASA POWER): rain March to July, rain and rain minus ET0 in the ZARC window (decendios 10 to 18, April 1 to June 30, from `src/engine/rules/crops.yaml`), the longest dry spell in April to July.",
        "- **Reference of what happened on farms:** IBGE PAM (SIDRA table 5457, variable 112) average yield of maize, beans and cassava in each municipality and year, as the anomaly against the median of the same crop in the surrounding ±5 years (so trends such as new hybrids do not read as weather). A strategy's *PAM proxy* is the mean anomaly of its crops.",
        "- **ENSO class:** NOAA CPC ONI of the December-February before the season (strong El Niño ≥ 1.5, moderate/weak 0.5 to 1.5, neutral, La Niña ≤ −0.5).",
        "- **Season class:** dry, normal or wet by tercile of rain in the ZARC window, per pilot.",
        "",
    ]
    frame = frame.assign(season=season_class(frame))
    lines += ["## Seasons by ENSO class (median per pilot)", "",
              "| Pilot | ENSO class | Years | Rain Mar–Jul (mm) | Rain ZARC window (mm) | Rain − ET0, window (mm) | Longest dry spell (days) |",
              "|---|---|---|---|---|---|---|"]
    for (pilot, enso), group in frame.groupby(["pilot", "enso"]):
        lines.append(
            f"| {pilot} | {enso} | {len(group)} | {group['rain_mar_jul_mm'].median():.0f} | {group['rain_window_mm'].median():.0f} | "
            f"{group['window_balance_mm'].median():.0f} | {group['longest_dry_spell_days'].median():.0f} |"
        )
    key_years = frame[(frame["enso"] == "el_nino_strong") | (frame["season"] != "normal")]
    key_years = key_years[(key_years["enso"] == "el_nino_strong") | key_years["year"].isin(
        frame.sort_values("rain_window_mm").groupby("pilot").head(3)["year"].tolist()
        + frame.sort_values("rain_window_mm", ascending=False).groupby("pilot").head(3)["year"].tolist()
    )]
    lines += ["", "## Key years: strong El Niño, and the 3 driest and 3 wettest per pilot", "",
              "| Pilot | Year | ENSO | Season | Rain window (mm) | Rain − ET0 window (mm) | Longest dry spell | PAM maize | PAM beans | PAM cassava | Rank 1, maize + water | Rank 1 with perfect forecast |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in key_years.sort_values(["pilot", "year"]).itertuples():
        lines.append(
            f"| {row.pilot} | {row.year} | {row.enso} | {row.season} | {row.rain_window_mm:.0f} | {_fmt(row.window_balance_mm)} | "
            f"{row.longest_dry_spell_days} | {_pct(row.pam_maize)} | {_pct(row.pam_beans)} | {_pct(row.pam_cassava)} | "
            f"{STRATEGY_LABEL[row.rank1_maize_water]} | {STRATEGY_LABEL[row.rank1_maize_water_perfect]} |"
        )
    lines += ["", "## Crop yield anomaly by season class (median, IBGE PAM)", "",
              "| Pilot | Season | Years | Maize | Beans | Cassava |", "|---|---|---|---|---|---|"]
    for (pilot, season), group in frame.groupby(["pilot", "season"]):
        med = {c: group[f"pam_{c}"].dropna() for c in ("maize", "beans", "cassava")}
        lines.append(f"| {pilot} | {season} | {len(group)} | " + " | ".join(
            _pct(median(v)) if len(v) else "n/a" for v in med.values()) + " |")
    lines += ["", "## Did rank 1 match the strategy with the best PAM proxy?", "",
              "Crop maize. Chance is the rate a random pick would reach, given ties.", "",
              "| Priority | Forecast | Hits / years scored | Hit rate | Chance |", "|---|---|---|---|---|"]
    for priority in ("water", "soil", "erosion", "income"):
        for perfect in (False, True):
            hits, scored, chance = agreement(results, anomalies, "maize", priority, perfect)
            rate = hits / scored if scored else 0.0
            lines.append(f"| {priority} | {'perfect' if perfect else 'none'} | {hits} / {scored} | {rate:.0%} | {chance:.0%} |")
    lines += ["", "## How often the engine changes its advice", "",
              "| Pilot | Rank 1, maize + water (no forecast) | Years |", "|---|---|---|"]
    for (pilot, kind), group in frame.groupby(["pilot", "rank1_maize_water"]):
        lines.append(f"| {pilot} | {STRATEGY_LABEL[kind]} | {len(group)} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--last-year", type=int, default=2025, help="last season to include (PAM is annual)")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR)
    args = parser.parse_args(argv)
    try:
        results, anomalies = run(args.last_year, args.cache_dir)
    except (DataToolkitError, requests.RequestException) as error:
        print(f"backtest: {error}", file=sys.stderr)
        return 1
    frame = year_rows(results)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PROCESSED_DIR / "backtest_years.csv", index=False)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    generated = render(results, anomalies, frame)
    findings = REPORT.with_name("backtest-findings.md")
    REPORT.write_text(generated + ("\n" + findings.read_text() if findings.is_file() else ""))
    print(f"backtest: {len(results)} pilot-years -> {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
