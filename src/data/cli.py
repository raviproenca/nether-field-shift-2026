# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Command line: python -m src.data <source> --bbox|--point ... --start ... --end ... --variable ... [--out ...]."""

import argparse
import json
import sys
import warnings
from pathlib import Path

import pandas as pd

from . import earthdata, open_meteo, planetary, power, srtm
from .clip import NearestCellWarning, OutOfRangeWarning
from .dates import DateRange, parse_range
from .errors import DataToolkitError, InputError, remote_errors
from .paths import CACHE_DIR, PROCESSED_DIR, RAW_DIR, safe_filename
from .regions import BBox, parse_point, resolve_region

TABLE_SUFFIXES = (".csv", ".parquet")
FORECAST_SUFFIXES = (*TABLE_SUFFIXES, ".json")
SOURCE_CHOICES = ["power", *earthdata.SOURCES, "planetary", "srtm", "open-meteo"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.data", description="Download and clip NASA data.")
    parser.add_argument("source", choices=SOURCE_CHOICES)
    place = parser.add_mutually_exclusive_group()
    place.add_argument("--bbox", help="'W,S,E,N' or a preset: sergipe (default), nordeste")
    place.add_argument(
        "--point", help="'LAT,LON'; needs --radius-km (except for power and open-meteo, which use the point itself)"
    )
    parser.add_argument("--radius-km", type=float, help="half-side of the box around --point, in km")
    parser.add_argument("--start", help="YYYY-MM-DD (required for historical sources)")
    parser.add_argument("--end", help="YYYY-MM-DD (required for historical sources)")
    parser.add_argument(
        "--variable",
        help="POWER/Open-Meteo: comma list. SRTM: elevation|slope_deg|slope_pct|all. Others: variable or band name",
    )
    parser.add_argument("--collection", default=planetary.DEFAULT_COLLECTION, help="planetary: STAC collection")
    parser.add_argument(
        "--max-cloud", type=float, default=planetary.DEFAULT_MAX_CLOUD, help="planetary: eo:cloud_cover < N"
    )
    parser.add_argument(
        "--max-pixels", type=int, default=planetary.DEFAULT_MAX_PIXELS, help="planetary/srtm: max pixels per item"
    )
    parser.add_argument(
        "--forecast-days",
        type=int,
        default=open_meteo.DEFAULT_FORECAST_DAYS,
        help="open-meteo: forecast horizon in days (1..16)",
    )
    parser.add_argument(
        "--model",
        default=open_meteo.DEFAULT_MODEL,
        help=f"open-meteo: {', '.join(open_meteo.SUPPORTED_MODELS)}",
    )
    parser.add_argument("--short-name", help="override the default NASA short_name of the source")
    parser.add_argument(
        "--version", help="collection version (default: the version of the source's default short_name)"
    )
    parser.add_argument("--out", type=Path, help=".csv/.parquet/.json table, or a folder for GeoTIFF sources")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help="downloaded granules (default data/raw)")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR, help="API response cache (default data/cache)")
    parser.add_argument("--search-only", action="store_true", help="count granules/tiles without downloading data")
    parser.add_argument(
        "--download", action="store_true", help="GLDAS/IMERG: download full files instead of lazy reads"
    )
    parser.add_argument(
        "--keep-out-of-range",
        action="store_true",
        help="GLDAS/IMERG/SMAP: keep values outside the variable's valid_min/valid_max (fill values are still dropped)",
    )
    parser.add_argument("--refresh", action="store_true", help="POWER/Open-Meteo: ignore the local cache")
    return parser


def csv_date_format(frame: pd.DataFrame) -> str:
    """Daily data keeps plain dates; sub-daily data (e.g. GLDAS 3-hourly) keeps the hour."""
    for column in frame.columns:
        values = frame[column]
        if pd.api.types.is_datetime64_any_dtype(values) and (values.dropna() != values.dropna().dt.normalize()).any():
            return "%Y-%m-%d %H:%M"
    return "%Y-%m-%d"


def write_table(frame: pd.DataFrame, out: Path) -> None:
    if out.suffix not in TABLE_SUFFIXES:
        raise InputError(f"unsupported output '{out.suffix}': use .csv or .parquet")
    with remote_errors(f"writing {out.name}"):
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix == ".csv":
            frame.to_csv(out, index=False, date_format=csv_date_format(frame))
        else:
            frame.to_parquet(out, index=False)


def default_out(source: str, variable: str, dates: DateRange) -> Path:
    spec = earthdata.SOURCES.get(source)
    if spec and spec.kind == "file_raster":
        return PROCESSED_DIR / source
    name = safe_filename(variable)
    return PROCESSED_DIR / f"{source}_{name}_{dates.start}_{dates.end}.csv"


def power_point(args: argparse.Namespace) -> tuple[float, float]:
    """Point APIs (POWER, Open-Meteo): --point is used as is (no radius needed); a box becomes its center."""
    if args.point is not None:
        return parse_point(args.point)
    if args.radius_km is not None:
        raise InputError("--radius-km needs --point")
    return resolve_region(args.bbox).center


def check_out_extension(args: argparse.Namespace) -> None:
    """Fail before any search or download when --out does not fit the source."""
    if args.out is None:
        return
    suffix = args.out.suffix.lower()
    if args.source == "srtm":
        if suffix in (*TABLE_SUFFIXES, ".tif"):
            raise InputError(f"srtm writes GeoTIFF files into a folder or a .json summary: invalid --out '{args.out}'")
        return
    if args.source == "open-meteo":
        if suffix not in FORECAST_SUFFIXES:
            raise InputError(f"unsupported --out '{args.out}': use a .csv, .parquet or .json file")
        return
    spec = earthdata.SOURCES.get(args.source)
    folder_output = args.source == "planetary" or (spec is not None and spec.kind == "file_raster")
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


def run_open_meteo(args: argparse.Namespace) -> None:
    variables = open_meteo.parse_variables(args.variable)
    lat, lon = power_point(args)
    frame = open_meteo.fetch_forecast(
        lat,
        lon,
        variables=variables,
        forecast_days=args.forecast_days,
        model=args.model,
        cache_dir=args.cache_dir / "open_meteo",
        refresh=args.refresh,
    )
    start_str = frame.index.min().strftime("%Y-%m-%d")
    end_str = frame.index.max().strftime("%Y-%m-%d")
    out = args.out or (PROCESSED_DIR / f"open_meteo_{args.model}_{start_str}_{end_str}.json")
    if out.suffix.lower() == ".json":
        with remote_errors(f"writing {out.name}"):
            out.parent.mkdir(parents=True, exist_ok=True)
            payload = open_meteo.to_api_response(frame, lat, lon, model=args.model)
            out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        write_table(frame.reset_index(), out)
    print(f"Open-Meteo ({args.model}) {lat:.4f},{lon:.4f}: {len(frame)} forecast days ({start_str}..{end_str}) -> {out}")


def run_srtm(args: argparse.Namespace, bbox: BBox) -> None:
    client = planetary.open_client()
    items = srtm.search_tiles(client, bbox)
    print(f"nasadem: {len(items)} tile(s): {', '.join(item.id for item in items)}")
    if args.search_only:
        return
    if args.out is not None and args.out.suffix.lower() == ".json":
        elevation = srtm.fetch_elevation(bbox, client=client, max_pixels=args.max_pixels)
        summary = srtm.summarize_terrain(elevation)
        with remote_errors(f"writing {args.out.name}"):
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(
            f"NASADEM summary: elev {summary['elevation_min_m']}..{summary['elevation_max_m']} m, "
            f"mean slope {summary['slope_mean_pct']}% ({summary['slope_class']}) -> {args.out}"
        )
        return
    out = args.out or PROCESSED_DIR / "srtm"
    written, summary = srtm.write_rasters(
        bbox, out, variable=args.variable or "elevation", client=client, max_pixels=args.max_pixels
    )
    summary_path = out / "srtm_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(
        f"wrote {len(written)} GeoTIFF file(s) and summary (mean slope {summary['slope_mean_pct']}%, "
        f"{summary['slope_class']}) to {out}"
    )


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
        frame = earthdata.fetch_grid(
            source, granules, args.variable, bbox, raw_dir, args.download, args.keep_out_of_range
        )
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
            warnings.simplefilter("default", OutOfRangeWarning)
            warnings.showwarning = lambda message, *_: print(f"warning: {message}", file=sys.stderr)
            check_out_extension(args)
            if args.source == "open-meteo":
                if args.search_only:
                    raise InputError("--search-only applies to satellite granule sources, not open-meteo")
                run_open_meteo(args)
                return 0
            if args.source == "srtm":
                bbox = resolve_region(args.bbox, args.point, args.radius_km)
                run_srtm(args, bbox)
                return 0
            if not args.start or not args.end:
                raise InputError(f"--start and --end are required for {args.source}")
            dates = parse_range(args.start, args.end)
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
