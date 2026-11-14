# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Command line: python -m src.data <source> --bbox|--point ... --start ... --end ... --variable ... [--out ...]."""

import argparse
import sys
from pathlib import Path

import pandas as pd

from . import earthdata, planetary, power
from .dates import DateRange, parse_range
from .errors import DataToolkitError, InputError
from .paths import PROCESSED_DIR, RAW_DIR
from .regions import BBox, resolve_region

SOURCE_CHOICES = ["power", *earthdata.SOURCES, "planetary"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.data", description="Download and clip NASA data.")
    parser.add_argument("source", choices=SOURCE_CHOICES)
    place = parser.add_mutually_exclusive_group()
    place.add_argument("--bbox", help="'W,S,E,N' or a preset: sergipe (default), nordeste")
    place.add_argument("--point", help="'LAT,LON'; needs --radius-km")
    parser.add_argument("--radius-km", type=float, help="half-side of the box around --point, in km")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--variable", help="POWER: comma list (T2M,PRECTOTCORR). Others: variable or band name")
    parser.add_argument("--collection", default=planetary.DEFAULT_COLLECTION, help="planetary: STAC collection")
    parser.add_argument(
        "--max-cloud", type=float, default=planetary.DEFAULT_MAX_CLOUD, help="planetary: eo:cloud_cover < N"
    )
    parser.add_argument("--short-name", help="override the default NASA short_name of the source")
    parser.add_argument("--version", help="collection version for the CMR search")
    parser.add_argument("--out", type=Path, help=".csv/.parquet table, or a folder for GeoTIFF sources")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help="raw cache root (default data/raw)")
    parser.add_argument("--search-only", action="store_true", help="count granules and show the latest date; no login")
    parser.add_argument(
        "--download", action="store_true", help="GLDAS/IMERG: download full files instead of lazy reads"
    )
    parser.add_argument("--refresh", action="store_true", help="POWER: ignore the local cache")
    return parser


def write_table(frame: pd.DataFrame, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix == ".csv":
        frame.to_csv(out, index=False, date_format="%Y-%m-%d")
    elif out.suffix == ".parquet":
        frame.to_parquet(out, index=False)
    else:
        raise InputError(f"unsupported output '{out.suffix}': use .csv or .parquet")


def default_out(source: str, variable: str, dates: DateRange) -> Path:
    spec = earthdata.SOURCES.get(source)
    if spec and spec.kind == "file_raster":
        return PROCESSED_DIR / source
    name = variable.replace("/", "-").replace(",", "-")
    return PROCESSED_DIR / f"{source}_{name}_{dates.start}_{dates.end}.csv"


def run_power(args: argparse.Namespace, bbox: BBox, dates: DateRange) -> None:
    variables = power.parse_variables(args.variable or "")
    lat, lon = bbox.center
    frame = power.fetch_point(lat, lon, dates, variables, cache_dir=args.raw_dir / "power", refresh=args.refresh)
    out = args.out or default_out("power", args.variable, dates)
    write_table(frame.reset_index(), out)
    valid = frame.dropna(how="all")
    print(f"POWER point {lat:.4f},{lon:.4f}: {len(frame)} days, last day with data {valid.index[-1].date()} -> {out}")


def run_earthdata(args: argparse.Namespace, bbox: BBox, dates: DateRange) -> None:
    source = earthdata.SOURCES[args.source]
    short_name = args.short_name or source.short_name
    granules = earthdata.search(short_name, bbox, dates, args.version)
    print(f"{short_name}: {len(granules)} granules, latest start {earthdata.latest_granule_date(granules).date()}")
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
    written = planetary.fetch_clips(items, args.variable, bbox, out)
    print(f"wrote {len(written)} GeoTIFF files to {out}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(attach_negative_values(sys.argv[1:] if argv is None else argv))
    try:
        bbox = resolve_region(args.bbox, args.point, args.radius_km)
        dates = parse_range(args.start, args.end)
        if args.source == "power":
            if args.search_only:
                raise InputError("--search-only applies to Earthdata sources, not POWER")
            run_power(args, bbox, dates)
        elif args.source == "planetary":
            run_planetary(args, bbox, dates)
        else:
            run_earthdata(args, bbox, dates)
    except DataToolkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2 if isinstance(exc, InputError) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
