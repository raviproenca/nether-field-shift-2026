# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""IBGE SIDRA API (public, no login, not NASA data): Produção Agrícola Municipal and any other SIDRA table.

Run it as: python -m src.data.sidra --table 5457 --variable 214,8331 --classification 782 \
    --categories 40112,40119,40122 --period "last 1" --out data/processed/pam.csv
Details of the API and the PAM tables: docs/research/brazil-data-sources.md.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

from .errors import DataToolkitError, InputError, RemoteDataError
from .paths import CACHE_DIR, PROCESSED_DIR

BASE_URL = "https://apisidra.ibge.gov.br/values"
MAX_VALUES = 100_000  # the API refuses larger requests
RETRY_STATUS = {429, 500, 502, 503, 504}
PAM_TABLE = 5457  # temporary and permanent crops, 1974 onward, up to municipality level
SERGIPE_UF = 28
ZERO_SYMBOLS = {"-"}  # "zero absoluto": the crop is not produced there
MISSING_SYMBOLS = {"X", "..", "..."}  # withheld, not applicable, not available
PERIOD_PATTERN = re.compile(r"^(last \d+|all|\d{4}(-\d{4})?(,\d{4}(-\d{4})?)*)$")
NUMBER_PATTERN = re.compile(r"^\d+(,\d+)*$")


def _ids(text: str, label: str) -> str:
    if not NUMBER_PATTERN.fullmatch(text.replace(" ", "")):
        raise InputError(f"invalid {label} '{text}': expected numeric codes separated by commas")
    return text.replace(" ", "")


def build_url(
    table: int,
    variables: str,
    periods: str,
    uf: int = SERGIPE_UF,
    classification: int | None = None,
    categories: str | None = None,
) -> str:
    """URL for all municipalities (level n6) of one UF: .../t/<table>/n6/in n3 <uf>/v/<vars>/p/<periods>[/c<class>/<cats>]."""
    if table <= 0:
        raise InputError(f"invalid table '{table}'")
    if not 10 <= uf <= 53:
        raise InputError(f"invalid UF code '{uf}' (IBGE codes go from 11 to 53; Sergipe is 28)")
    periods = periods.strip()
    if not PERIOD_PATTERN.fullmatch(periods):
        raise InputError(f"invalid period '{periods}': use 'last N', 'all', years like 2023, 2020-2025 or 2020,2023")
    if (classification is None) != (categories is None):
        raise InputError("--classification and --categories go together")
    path = f"t/{table}/n6/in n3 {uf}/v/{_ids(variables, 'variable')}/p/{periods}"
    if classification is not None:
        path += f"/c{classification}/{_ids(categories or '', 'categories')}"
    return f"{BASE_URL}/{quote(path, safe='/,-')}"


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")


def _to_number(symbol: str) -> float:
    if symbol in ZERO_SYMBOLS:
        return 0.0
    if symbol in MISSING_SYMBOLS:
        return float("nan")
    try:
        return float(symbol)
    except ValueError:
        return float("nan")


def parse_response(payload) -> pd.DataFrame:
    """Tidy table from a SIDRA answer: element 0 is the header, the others are values.

    Columns: <dimension>_code and <dimension> for each dimension (municipality, variable, year, product...),
    unit, value (float: "-" becomes 0, "X", ".." and "..." become NaN) and symbol (the raw text of the value).
    """
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):
        raise RemoteDataError("SIDRA returned no data for this request (check table, codes and period)")
    header, rows = payload[0], payload[1:]
    frame = pd.DataFrame(rows)
    names: dict[str, str] = {}
    for key, label in header.items():
        if key[0] == "D" and key.endswith("C"):
            names[key] = f"{_slug(label.replace('(Código)', ''))}_code"
        elif key[0] == "D" and key.endswith("N"):
            names[key] = _slug(label)
    tidy = frame[list(names)].rename(columns=names)
    tidy.insert(len(tidy.columns), "unit", frame["MN"])
    tidy["value"] = frame["V"].map(_to_number)
    tidy["symbol"] = frame["V"]
    return tidy


def _describe_error(response: requests.Response) -> str:
    text = " ".join(str(response.text or "").split())[:200]
    return f"SIDRA API answered HTTP {response.status_code}: {text}"


def _request(session: requests.Session, url: str, timeout: float, retries: int, sleep: Callable[[float], None]) -> list:
    reason = ""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=timeout)
        except requests.RequestException as exc:
            reason = f"network error: {exc.__class__.__name__}"
        else:
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    raise RemoteDataError("SIDRA API returned a response that is not valid JSON") from None
            if "excedeu o limite" in (response.text or ""):
                raise InputError(
                    f"too many values for one SIDRA call ({MAX_VALUES} at most): narrow the years, variables or products"
                )
            if response.status_code not in RETRY_STATUS:
                raise RemoteDataError(_describe_error(response))
            reason = f"HTTP {response.status_code}"
        if attempt < retries:
            sleep(2.0 * attempt)
    raise RemoteDataError(f"SIDRA API unavailable after {retries} attempts ({reason}). Try again later.")


def fetch(
    table: int,
    variables: str,
    periods: str,
    uf: int = SERGIPE_UF,
    classification: int | None = None,
    categories: str | None = None,
    cache_dir: Path | None = None,
    refresh: bool = False,
    session: requests.Session | None = None,
    timeout: float = 60.0,
    retries: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> pd.DataFrame:
    """Municipal values of one SIDRA table for one UF. The raw JSON is cached in cache_dir (refresh=True ignores it)."""
    url = build_url(table, variables, periods, uf, classification, categories)
    cached = cache_dir / f"sidra_{table}_{hashlib.sha1(url.encode()).hexdigest()[:10]}.json" if cache_dir else None
    payload = None
    if cached and cached.is_file() and not refresh:
        try:
            payload = json.loads(cached.read_text())
        except (OSError, ValueError):
            cached.unlink(missing_ok=True)
    if payload is None:
        payload = _request(session or requests.Session(), url, timeout, retries, sleep)
        if cached:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps(payload))
    return parse_response(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.data.sidra", description="Download an IBGE SIDRA table.")
    parser.add_argument("--table", type=int, default=PAM_TABLE, help=f"SIDRA table (default {PAM_TABLE}, PAM)")
    parser.add_argument("--variable", required=True, help="variable codes, e.g. 214,8331 (see the table metadata)")
    parser.add_argument("--period", required=True, help="'last N', 'all', 2023, 2020-2025 or 2020,2023")
    parser.add_argument("--uf", type=int, default=SERGIPE_UF, help="IBGE UF code (default 28, Sergipe)")
    parser.add_argument("--classification", type=int, help="classification code, e.g. 782 (PAM products)")
    parser.add_argument("--categories", help="category codes of the classification, e.g. 40112,40119,40122")
    parser.add_argument("--out", type=Path, help=".csv or .parquet (default data/processed/sidra_<table>.csv)")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR, help="API response cache (default data/cache)")
    parser.add_argument("--refresh", action="store_true", help="ignore the local cache")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = args.out or PROCESSED_DIR / f"sidra_{args.table}.csv"
    try:
        if out.suffix not in (".csv", ".parquet"):
            raise InputError(f"unsupported --out '{out}': use a .csv or .parquet file")
        frame = fetch(
            args.table,
            args.variable,
            args.period,
            args.uf,
            args.classification,
            args.categories,
            cache_dir=args.cache_dir / "sidra",
            refresh=args.refresh,
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out, index=False) if out.suffix == ".csv" else frame.to_parquet(out, index=False)
    except DataToolkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2 if isinstance(exc, InputError) else 1
    print(f"SIDRA table {args.table}: {len(frame)} values -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
