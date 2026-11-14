# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Snapshot generator: python -m src.data.snapshots

Builds light JSON/GeoJSON files (a grid of points per region with short series of POWER, GLDAS, IMERG, SMAP and
NDVI) that the internal map reads as static files. No server. Format: docs/data-format.md.
A source that fails is reported in index.json and does not stop the others.
"""

import argparse
import sys
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

from . import snapshot_sources as sources
from .errors import DataToolkitError, InputError, describe_failure
from .paths import CACHE_DIR, RAW_DIR, ROOT
from .regions import PRESETS, BBox
from .sampling import Point, grid_points
from .snapshot_model import Region, SourceData, SourceInfo
from .snapshot_output import MAX_TOTAL_BYTES, build_files, check_size, write_files

DEFAULT_OUT = ROOT / "apps" / "web" / "public" / "data"
DEFAULT_REGIONS = {
    "sergipe": Region("sergipe", "Sergipe", PRESETS["sergipe"], 0.25, "SE"),
    "nordeste": Region("nordeste", "Northeast Brazil (Nordeste)", PRESETS["nordeste"], 1.0, "NE"),
}
DEFAULT_SOURCES = ["gldas", "power", "imerg", "smap", "viirs"]
LAND_MASK_SOURCE = "gldas"
DOMAIN_MARGIN = 0.1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.data.snapshots", description="Generate the static data snapshots of the internal map."
    )
    parser.add_argument("--regions", default=",".join(DEFAULT_REGIONS), help="comma list (default: all)")
    parser.add_argument(
        "--spacing", action="append", default=[], metavar="REGION=DEG", help="grid spacing, e.g. --spacing nordeste=2"
    )
    parser.add_argument(
        "--sources", default=",".join(DEFAULT_SOURCES), help="comma list of: " + ", ".join(sources.FETCHERS)
    )
    parser.add_argument("--days", type=int, default=30, help="days of daily series (POWER, IMERG, SMAP); default 30")
    parser.add_argument("--gldas-months", type=int, default=6, help="months of GLDAS monthly series; default 6")
    parser.add_argument("--ndvi-days", type=int, default=60, help="span of the NDVI composites, in days; default 60")
    parser.add_argument("--today", help="YYYY-MM-DD, the 'current' day (default: today, UTC)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output folder (default apps/web/public/data)")
    parser.add_argument("--max-mb", type=float, default=MAX_TOTAL_BYTES / 1048576, help="size limit of all files, MB")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR)
    parser.add_argument("--workers", type=int, default=4, help="parallel reads; default 4")
    return parser


def parse_spacing(items: list[str]) -> dict[str, float]:
    spacing = {}
    for item in items:
        name, _, value = item.partition("=")
        try:
            spacing[name.strip()] = float(value)
        except ValueError:
            raise InputError(f"invalid --spacing '{item}': expected REGION=DEGREES, e.g. nordeste=2") from None
    return spacing


def pick_regions(names: str, spacing: dict[str, float]) -> list[Region]:
    chosen = []
    for name in (n.strip() for n in names.split(",") if n.strip()):
        if name not in DEFAULT_REGIONS:
            raise InputError(f"unknown region '{name}'; choose from: {', '.join(DEFAULT_REGIONS)}")
        region = DEFAULT_REGIONS[name]
        chosen.append(Region(region.id, region.name, region.bbox, spacing.get(name, region.spacing), region.prefix))
    unknown = set(spacing) - {r.id for r in chosen}
    if unknown or not chosen:
        raise InputError(
            f"--spacing names a region that is not selected: {', '.join(sorted(unknown)) or '(none selected)'}"
        )
    return chosen


def domain_of(regions: list[Region]) -> BBox:
    """Box covering all regions plus the largest half-spacing (point boxes reach beyond the region edge)."""
    margin = max(r.spacing for r in regions) / 2 + DOMAIN_MARGIN
    return BBox(
        max(-180.0, min(r.bbox.west for r in regions) - margin),
        max(-90.0, min(r.bbox.south for r in regions) - margin),
        min(180.0, max(r.bbox.east for r in regions) + margin),
        min(90.0, max(r.bbox.north for r in regions) + margin),
    )


def land_points(points: list[Point], data: SourceData) -> list[Point]:
    """Points where the land-mask source has a value at some time; the rest is open water."""
    on_land = np.isfinite(data.values).any(axis=(1, 2))
    return [point for point, keep in zip(points, on_land) if keep]


def run_sources(
    names: list[str], ctx: sources.Context, fetchers: dict[str, Callable], log: Callable[[str], None]
) -> tuple[dict[str, SourceData], dict[str, str]]:
    """Fetch every source; the land mask comes first and filters the points the other sources are asked for."""
    results: dict[str, SourceData] = {}
    failures: dict[str, str] = {}
    ordered = sorted(names, key=lambda n: n != LAND_MASK_SOURCE)
    for name in ordered:
        started = time.time()
        log(f"[{name}] fetching")
        try:
            results[name] = fetchers[name](ctx)
        except Exception as exc:  # noqa: BLE001  one failing source must not stop the others
            failures[name] = str(exc) if isinstance(exc, DataToolkitError) else describe_failure(exc)
            log(f"[{name}] FAILED: {failures[name]}")
            continue
        log(f"[{name}] ok in {time.time() - started:.0f}s ({len(results[name].times)} times)")
    return results, failures


def generate(
    regions: list[Region],
    names: list[str],
    ctx_args: dict,
    out_dir: Path,
    max_bytes: int,
    fetchers: dict[str, Callable] | None = None,
    infos: dict[str, SourceInfo] | None = None,
    log: Callable[[str], None] = print,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, int]:
    """Run the whole pipeline and write the files. Returns {relative path: size in bytes}."""
    fetchers, infos = fetchers or sources.FETCHERS, infos or sources.INFOS
    all_points = [p for region in regions for p in grid_points(region.bbox, region.spacing, region.prefix)]
    ctx = sources.Context(points=all_points, domain=domain_of(regions), log=log, **ctx_args)
    for region in regions:
        log(f"{region.id}: {sum(p.id.startswith(region.prefix) for p in all_points)} grid points")
    results: dict[str, SourceData] = {}
    failures: dict[str, str] = {}
    if LAND_MASK_SOURCE in names:
        mask_results, mask_failures = run_sources([LAND_MASK_SOURCE], ctx, fetchers, log)
        results.update(mask_results)
        failures.update(mask_failures)
        if LAND_MASK_SOURCE in results:
            land = land_points(all_points, results[LAND_MASK_SOURCE])
            log(f"land mask ({LAND_MASK_SOURCE}): {len(land)} of {len(all_points)} points on land")
            on_land = set(land)
            kept_rows = [i for i, p in enumerate(all_points) if p in on_land]
            results[LAND_MASK_SOURCE].values = results[LAND_MASK_SOURCE].values[kept_rows]
            all_points, ctx.points = land, land
        else:
            log("land mask unavailable: keeping every grid point")
    rest = [n for n in names if n != LAND_MASK_SOURCE]
    more_results, more_failures = run_sources(rest, ctx, fetchers, log)
    results.update(more_results)
    failures.update(more_failures)
    region_points = {r.id: [p for p in all_points if p.id.startswith(r.prefix)] for r in regions}
    selected = {n: infos[n] for n in names}
    files = build_files(now(), regions, region_points, selected, results, all_points, failures)
    total = check_size(files, max_bytes)
    write_files(out_dir, files)
    log(f"wrote {len(files)} files, {total / 1024:.0f} KB total, to {out_dir}")
    return {name: len(content) for name, content in files.items()}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        regions = pick_regions(args.regions, parse_spacing(args.spacing))
        names = [n.strip() for n in args.sources.split(",") if n.strip()]
        for name in names:
            sources.check_source(name)
        if args.days < 1 or args.gldas_months < 1 or args.ndvi_days < 1:
            raise InputError("--days, --gldas-months and --ndvi-days must be at least 1")
        today = date.fromisoformat(args.today) if args.today else datetime.now(UTC).date()
        ctx_args = {
            "days": args.days,
            "today": today,
            "raw_dir": args.raw_dir,
            "cache_dir": args.cache_dir,
            "workers": args.workers,
            "gldas_months": args.gldas_months,
            "ndvi_days": args.ndvi_days,
        }
        sizes = generate(
            regions, names, ctx_args, args.out, int(args.max_mb * 1048576), log=lambda m: print(m, file=sys.stderr)
        )
    except (DataToolkitError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2 if isinstance(exc, ValueError) else 1
    for name, size in sorted(sizes.items()):
        print(f"{size / 1024:8.1f} KB  {name}")
    print(f"{sum(sizes.values()) / 1024:8.1f} KB  total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
