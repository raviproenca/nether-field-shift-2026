# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""ZARC Tábua de Risco (MAPA open data, CC BY, not NASA data): list the files and keep only one UF and some crops.

The MAPA catalog (CKAN) publishes one whole-country CSV per harvest year (220 to 550 MB) and no row filter, so the
file is streamed and only the wanted rows are kept in memory.

Run it as: python -m src.data.zarc --safra 2026/2027 --uf SE --crop feij --crop milho --out data/processed/zarc.csv
Details of the files and columns: docs/research/brazil-data-sources.md.
"""

import argparse
import csv
import hashlib
import sys
import unicodedata
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import requests

from .errors import DataToolkitError, InputError, RemoteDataError
from .paths import CACHE_DIR, PROCESSED_DIR

CATALOG_URL = "https://dados.agricultura.gov.br/api/3/action/package_show"
DATASET_ID = "tabua-de-risco-zoneamento-agricola-de-risco-climatico"
PERENNIAL = "perene"
UFS = frozenset(
    [
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    ]
)
DECENDIO_COLUMNS = [f"dec{i}" for i in range(1, 37)]
TIMEOUT = 120.0


def _plain(text: str) -> str:
    """Lower case without accents, so 'feij' matches 'Feijão'."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def list_resources(session: requests.Session | None = None) -> list[dict]:
    """The CSV files of the dataset: name, url. Raises RemoteDataError when the catalog does not answer."""
    try:
        response = (session or requests.Session()).get(CATALOG_URL, params={"id": DATASET_ID}, timeout=TIMEOUT)
        payload = response.json()
        resources = payload["result"]["resources"]
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        raise RemoteDataError(f"could not read the MAPA catalog ({exc.__class__.__name__}); try again later") from None
    return [{"name": r["name"], "url": r["url"]} for r in resources if str(r.get("format", "")).upper() == "CSV"]


def pick_resource(resources: list[dict], safra: str) -> dict:
    """'2026/2027' selects 'Tábua de risco - Safra 2026/2027'; 'perene' selects the perennial/vegetable/no-season file."""
    wanted = "perene," if safra.lower() == PERENNIAL else f"safra {safra}"
    matches = [r for r in resources if wanted in _plain(r["name"])]
    if len(matches) != 1:
        names = ", ".join(r["name"] for r in resources)
        raise InputError(f"no single file for --safra '{safra}'; available: {names}")
    return matches[0]


def _lines(response: requests.Response) -> Iterator[str]:
    for number, raw in enumerate(response.iter_lines()):
        if raw:
            yield raw.decode("utf-8-sig" if number == 0 else "utf-8")


def stream_rows(
    url: str, uf: str, crops: list[str] | None = None, session: requests.Session | None = None
) -> pd.DataFrame:
    """Rows of one UF (and crops whose name contains one of the texts) from a whole-country CSV, streamed."""
    wanted = [_plain(c) for c in crops or []]
    try:
        with (session or requests.Session()).get(url, stream=True, timeout=TIMEOUT) as response:
            if response.status_code != 200:
                raise RemoteDataError(f"MAPA file answered HTTP {response.status_code}")
            reader = csv.reader(_lines(response), delimiter=";")
            header = next(reader, None)
            if not header or "UF" not in header or "Nome_cultura" not in header:
                raise RemoteDataError("the ZARC file has an unexpected format (no UF/Nome_cultura columns)")
            uf_at, crop_at = header.index("UF"), header.index("Nome_cultura")
            kept = [
                row
                for row in reader
                if len(row) == len(header)
                and row[uf_at] == uf
                and (not wanted or any(text in _plain(row[crop_at]) for text in wanted))
            ]
    except requests.RequestException as exc:
        raise RemoteDataError(f"download from MAPA failed ({exc.__class__.__name__}); try again later") from None
    frame = pd.DataFrame(kept, columns=header)
    for column in [c for c in DECENDIO_COLUMNS if c in frame.columns]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
    return frame


def fetch(
    safra: str,
    uf: str = "SE",
    crops: list[str] | None = None,
    cache_dir: Path | None = None,
    refresh: bool = False,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """ZARC rows for one UF from the file of one harvest year; the filtered result is cached as CSV."""
    uf = uf.upper()
    if uf not in UFS:
        raise InputError(f"unknown UF '{uf}' (use the two-letter code, e.g. SE)")
    resource = pick_resource(list_resources(session), safra)
    key = hashlib.sha1(f"{resource['url']}|{uf}|{sorted(crops or [])}".encode()).hexdigest()[:10]
    cached = cache_dir / f"zarc_{key}.csv" if cache_dir else None
    if cached and cached.is_file() and not refresh:
        return pd.read_csv(cached, sep=";", dtype={"geocodigo": str})
    frame = stream_rows(resource["url"], uf, crops, session)
    if frame.empty:
        raise InputError(f"no ZARC rows for UF {uf} and crops {crops or 'all'} in '{resource['name']}'")
    if cached:
        cached.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(cached, sep=";", index=False)
    return frame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.data.zarc", description="Download ZARC rows for one UF.")
    parser.add_argument("--safra", help="harvest year such as 2026/2027, or 'perene' (perennial, vegetable, no season)")
    parser.add_argument("--uf", default="SE", help="two-letter UF code (default SE, Sergipe)")
    parser.add_argument("--crop", action="append", help="keep crops whose name contains this text (repeat for several)")
    parser.add_argument("--list", action="store_true", help="list the available files and stop")
    parser.add_argument("--out", type=Path, help=".csv or .parquet (default data/processed/zarc_<safra>_<uf>.csv)")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR, help="cache of the filtered rows (data/cache)")
    parser.add_argument("--refresh", action="store_true", help="ignore the local cache")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.list:
            for resource in list_resources():
                print(f"{resource['name']}\t{resource['url']}")
            return 0
        if not args.safra:
            raise InputError("--safra is required (or use --list)")
        label = args.safra.replace("/", "-")
        out = args.out or PROCESSED_DIR / f"zarc_{label}_{args.uf.lower()}.csv"
        if out.suffix not in (".csv", ".parquet"):
            raise InputError(f"unsupported --out '{out}': use a .csv or .parquet file")
        frame = fetch(args.safra, args.uf, args.crop, args.cache_dir / "zarc", args.refresh)
        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out, index=False) if out.suffix == ".csv" else frame.to_parquet(out, index=False)
    except DataToolkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2 if isinstance(exc, InputError) else 1
    print(f"ZARC {args.safra}, UF {args.uf.upper()}: {len(frame)} rows -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
