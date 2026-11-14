# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Command line: python -m src.data <source> --bbox|--point ... --start ... --end ... --variable ... [--out ...]."""

import argparse
import sys
import warnings
from pathlib import Path

import pandas as pd

from . import earthdata, planetary, power
from .clip import NearestCellWarning
from .dates import DateRange, parse_range
from .errors import DataToolkitError, InputError, remote_errors
from .paths import CACHE_DIR, PROCESSED_DIR, RAW_DIR, safe_filename
from .regions import BBox, parse_point, resolve_region

TABLE_SUFFIXES = (".csv", ".parquet")
SOURCE_CHOICES = ["power", *earthdata.SOURCES, "planetary"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.data", description="Download and clip NASA data.")
    parser.add_argument("source", choices=SOURCE_CHOICES)
    place = parser.add_mutually_exclusive_group()
    place.add_argument("--bbox", help="'W,S,E,N' or a preset: sergipe (default), nordeste")
    place.add_argument("--point", help="'LAT,LON'; needs --radius-km (except for power, which uses the point itself)")
    parser.add_argument("--radius-km", type=float, help="half-side of the box around --point, in km")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--variable", help="POWER: comma list (T2M,PRECTOTCORR). Others: variable or band name")
    parser.add_argument("--collection", default=planetary.DEFAULT_COLLECTION, help="planetary: STAC collection")
    parser.add_argument(
        "--max-cloud", type=float, default=planetary.DEFAULT_MAX_CLOUD, help="planetary: eo:cloud_cover < N"
    )
    parser.add_argument(
        "--max-pixels", type=int, default=planetary.DEFAULT_MAX_PIXELS, help="planetary: max pixels per band and item"
    )
    parser.add_argument("--short-name", help="override the default NASA short_name of the source")
    parser.add_argument(
        "--version", help="collection version (default: the version of the source's default short_name)"
    )
    parser.add_argument("--out", type=Path, help=".csv/.parquet table, or a folder for GeoTIFF sources")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help="downloaded granules (default data/raw)")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR, help="API response cache (default data/cache)")
    parser.add_argument("--search-only", action="store_true", help="count granules and show the latest date; no login")
    parser.add_argument(
        "--download", action="store_true", help="GLDAS/IMERG: download full files instead of lazy reads"
    )
    parser.add_argument("--refresh", action="store_true", help="POWER: ignore the local cache")
    return parser


def write_table(frame: pd.DataFrame, out: Path) -> None:
    if out.suffix not in TABLE_SUFFIXES:
        raise InputError(f"unsupported output '{out.suffix}': use .csv or .parquet")
    with remote_errors(f"writing {out.name}"):
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix == ".csv":
            frame.to_csv(out, index=False, date_format="%Y-%m-%d")
        else:
            frame.to_parquet(out, index=False)


def default_out(source: str, variable: str, dates: DateRange) -> Path:
    spec = earthdata.SOURCES.get(source)
    if spec and spec.kind == "file_raster":
        return PROCESSED_DIR / source
    name = safe_filename(variable)
    return PROCESSED_DIR / f"{source}_{name}_{dates.start}_{dates.end}.csv"


def power_point(args: argparse.Namespace) -> tuple[float, float]:
    """POWER is a point API: --point is used as is (no radius needed); a box becomes its center."""
    if args.point is not None:
        return parse_point(args.point)
    if args.radius_km is not None:
        raise InputError("--radius-km needs --point")
    return resolve_region(args.bbox).center


def check_out_extension(args: argparse.Namespace) -> None:
    """Fail before any search or download when --out does not fit the source."""
    if args.out is None:
        return
    spec = earthdata.SOURCES.get(args.source)
    folder_output = args.source == "planetary" or (spec is not None and spec.kind == "file_raster")
    suffix = args.out.suffix.lower()
    if folder_output and suffix in (*TABLE_SUFFIXES, ".tif"):
        raise InputError(f"{args.source} writes GeoTIFF files into a folder: --out '{args.out}' should be a folder")
    if not folder_output and suffix not in TABLE_SUFFIXES:
        raise InputError(f"unsupported --out '{args.out}': use a .csv or .parquet file")


def run_power(args: argparse.Namespace, dates: DateRange) -> None:
    variables = power.parse_variables(args.variable or "")
    lat, lon = power_point(args)
    frame = power.fetch_point(lat, lon, dates, variables, cache_dir=args.cache_dir / "power", refresh=args.refresh)
    out = args.out or default_out("power", args.variable, dates)
    write_table(frame.reset_index(), out)
    valid = frame.dropna(how="all")
    print(f"POWER point {lat:.4f},{lon:.4f}: {len(frame)} days, last day with data {valid.index[-1].date()} -> {out}")


def run_earthdata(args: argparse.Namespace, bbox: BBox, dates: DateRange) -> None:
    source = earthdata.SOURCES[args.source]
    short_name, version = earthdata.collection_query(source, args.short_name, args.version)
    granules = earthdata.search(short_name, bbox, dates, version)
    with remote_errors("reading the granule dates"):
        latest = earthdata.latest_granule_date(granules).date()
    print(f"{short_name}: {len(granules)} granules, latest start {latest}")
    if args.search_only:
        return
    if not args.variable:
        raise InputError("--variable is required (variable name, or band name for HLS, e.g. B04)")
    raw_dir = args.raw_dir / args.source
    out = args.out or default_out(args.source, args.variable, dates)
    if source.kind == "file_raster":
        written = earthdata.fetch_rasters(args.source, granules, args.variable, bbox, raw_dir, out)
        print(f"wrote {len(written)} GeoTIFF files to {out}")
    else:
        frame = earthdata.fetch_grid(source, granules, args.variable, bbox, raw_dir, args.download)
        write_table(frame, out)
        print(f"wrote {len(frame)} rows to {out}")


def attach_negative_values(argv: list[str]) -> list[str]:
    """Let '--point -10.9,-37.0' work: argparse would read the value as an option, so rewrite it as --point=VALUE."""
    merged: list[str] = []
    for token in argv:
        if merged and merged[-1] in ("--bbox", "--point") and token.startswith("-"):
            merged[-1] = f"{merged[-1]}={token}"
        else:
            merged.append(token)
    return merged


def run_planetary(args: argparse.Namespace, bbox: BBox, dates: DateRange) -> None:
    client = planetary.open_client()
    latest = planetary.latest_item_datetime(client, bbox, args.collection)
    items = planetary.search(client, bbox, dates, args.collection, args.max_cloud)
    print(
        f"{args.collection}: {len(items)} items with cloud < {args.max_cloud:g}% in the period; "
        f"latest item over the box (any cloud) {latest.date()}"
    )
    if args.search_only:
        return
    if not args.variable:
        raise InputError("--variable is required (asset/band name, e.g. B04, B08, SCL)")
    out = args.out or PROCESSED_DIR / "planetary"
    written = planetary.fetch_clips(items, args.variable, bbox, out, args.max_pixels)
    print(f"wrote {len(written)} GeoTIFF files to {out}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(attach_negative_values(sys.argv[1:] if argv is None else argv))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("default", NearestCellWarning)
            warnings.showwarning = lambda message, *_: print(f"warning: {message}", file=sys.stderr)
            dates = parse_range(args.start, args.end)
            check_out_extension(args)
            if args.source == "power":
                if args.search_only:
                    raise InputError("--search-only applies to Earthdata sources, not POWER")
                run_power(args, dates)
            else:
                bbox = resolve_region(args.bbox, args.point, args.radius_km)
                if args.source == "planetary":
                    run_planetary(args, bbox, dates)
                else:
                    run_earthdata(args, bbox, dates)
    except DataToolkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2 if isinstance(exc, InputError) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
