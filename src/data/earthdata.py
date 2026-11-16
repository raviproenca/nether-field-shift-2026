# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""NASA Earthdata sources via earthaccess: GLDAS, IMERG (GES DISC), SMAP (NSIDC), MODIS, VIIRS, HLS (LP DAAC).

Searching granules needs no login. Opening or downloading them does: run scripts/earthdata-login.sh once.
The download paths of this module have not been exercised against the real services (no credentials in CI).
"""

import os
import warnings
from dataclasses import dataclass
from pathlib import Path

import earthaccess
import pandas as pd
import xarray as xr

from . import clip
from .dates import DateRange
from .errors import AuthRequiredError, InputError, RemoteDataError, describe_failure, remote_errors
from .paths import safe_filename
from .regions import BBox

LOGIN_HINT = "run scripts/earthdata-login.sh first"


@dataclass(frozen=True)
class Source:
    """How one NASA source is fetched. kind: 'remote_grid', 'file_grid' or 'file_raster'."""

    short_name: str
    version: str
    kind: str
    resolution: str
    note: str


SOURCES: dict[str, Source] = {
    "gldas": Source("GLDAS_NOAH025_3H", "2.1", "remote_grid", "0.25 deg, 3-hourly", "GES DISC"),
    "imerg": Source(
        "GPM_3IMERGDL",
        "07",
        "remote_grid",
        "0.1 deg, daily",
        "GES DISC, Late run (Final run GPM_3IMERGDF ends 2025-09-30)",
    ),
    "smap": Source("SPL3SMP_E", "006", "file_grid", "9 km, daily", "NSIDC, enhanced L3 soil moisture"),
    "modis": Source("MOD13Q1", "061", "file_raster", "250 m, 16-day", "LP DAAC, Terra vegetation indices"),
    "viirs": Source(
        "VNP13A1", "002", "file_raster", "500 m, 16-day", "LP DAAC, VIIRS vegetation indices (MODIS continuity)"
    ),
    "hls": Source(
        "HLSL30", "2.0", "file_raster", "30 m, 2-3 days", "LP DAAC, Landsat; use --short-name HLSS30 for Sentinel-2"
    ),
}


def collection_query(source: Source, short_name: str | None, version: str | None) -> tuple[str, str | None]:
    """short_name and version to search. The default version only goes with the default short_name."""
    if short_name and short_name != source.short_name:
        return short_name, version
    return source.short_name, version or source.version


RASTER_SUFFIXES = {"modis": (".hdf",), "viirs": (".h5",), "hls": (".tif",)}


def require_login() -> None:
    netrc = Path(os.environ.get("NETRC") or Path.home() / ".netrc")
    if not netrc.is_file():
        raise AuthRequiredError(f"no Earthdata Login credentials ({netrc} not found): {LOGIN_HINT}")
    try:
        earthaccess.login(strategy="netrc")
    except Exception as exc:  # noqa: BLE001  earthaccess raises several unrelated types
        raise AuthRequiredError(f"Earthdata Login failed ({type(exc).__name__}): {LOGIN_HINT}") from None


def search(short_name: str, bbox: BBox, dates: DateRange, version: str | None = None) -> list:
    """Granules intersecting the box in the period. Public CMR search, no login needed."""
    query = {
        "short_name": short_name,
        "bounding_box": bbox.as_tuple,
        "temporal": (f"{dates.start.isoformat()}T00:00:00", f"{dates.end.isoformat()}T23:59:59"),
    }
    if version:
        query["version"] = version
    try:
        granules = earthaccess.search_data(count=-1, **query)
    except Exception as exc:  # noqa: BLE001  CMR errors vary
        raise RemoteDataError(f"CMR search failed for {short_name}: {describe_failure(exc)}") from None
    if not granules:
        raise RemoteDataError(f"no {short_name} granules for this box and period (try another --short-name or dates)")
    return granules


def granule_start(granule) -> pd.Timestamp:
    return pd.Timestamp(granule["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]).tz_localize(None)


def latest_granule_date(granules: list) -> pd.Timestamp:
    return max(granule_start(g) for g in granules)


def _local_files(granules: list, raw_dir: Path) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    return earthaccess.download(granules, local_path=raw_dir)


def _open_dataset(handle, variable: str) -> tuple[xr.Dataset, str]:
    group, _, name = variable.rpartition("/")
    return xr.open_dataset(handle, engine="h5netcdf", group=group or None, phony_dims="sort"), name


def _clip_grid(
    granule, handle, variable: str, bbox: BBox, kind: str, keep_out_of_range: bool = False
) -> tuple[pd.DataFrame, int, tuple[float | None, float | None]]:
    """Clipped long table, how many values the valid range dropped, and the range that was applied."""
    ds, name = _open_dataset(handle, variable)
    with ds:
        if name not in ds:
            raise InputError(f"variable '{name}' not found; available: {', '.join(ds.data_vars)}")
        da = clip.clip_latlon(ds[name], bbox) if kind == "remote_grid" else clip.clip_curvilinear(ds, name, bbox)
        dropped, bounds = 0, (None, None)
        if not keep_out_of_range:
            da, dropped, bounds = clip.mask_valid_range(da)
        da = da.load()
    if "time" not in da.dims and "time" not in da.coords:
        da = da.expand_dims(time=[granule_start(granule)])
    return clip.to_long_frame(da, name), dropped, bounds


def fetch_grid(
    source: Source,
    granules: list,
    variable: str,
    bbox: BBox,
    raw_dir: Path,
    download_full: bool = False,
    keep_out_of_range: bool = False,
) -> pd.DataFrame:
    """Long table (time, lat, lon, value) for GLDAS, IMERG and SMAP.

    GLDAS/IMERG are read lazily over HTTPS (earthaccess.open) so only the bytes of the box are transferred,
    unless download_full is set. SMAP files are always downloaded to raw_dir and clipped locally.

    Fill values are always dropped. Values outside the variable's declared valid_min/valid_max are dropped too,
    with one warning that gives the count, unless keep_out_of_range is set.
    """
    require_login()
    with remote_errors("opening the granules"):
        if source.kind == "file_grid" or download_full:
            handles = _local_files(granules, raw_dir)
        else:
            handles = earthaccess.open(granules)
    with remote_errors("reading the granules"):
        results = [_clip_grid(g, h, variable, bbox, source.kind, keep_out_of_range) for g, h in zip(granules, handles)]
    dropped = sum(count for _, count, _ in results)
    if dropped:
        low, high = next(bounds for _, count, bounds in results if count)
        warnings.warn(
            f"dropped {dropped} values outside valid_min/valid_max ({clip.describe_range(low, high)}); "
            "pass --keep-out-of-range to keep them",
            clip.OutOfRangeWarning,
        )
    table = pd.concat([frame for frame, _, _ in results], ignore_index=True)
    if table.empty:
        hint = "try other dates (SMAP revisits every 2-3 days), a bigger box, or the PM group"
        if source.kind != "file_grid":
            hint = "try other dates or a bigger box"
        raise InputError(f"no valid '{variable}' values inside the box for these dates: {hint}")
    return table


def _band_links(granule, band: str) -> list[str]:
    return [url for url in granule.data_links() if url.endswith(f".{band}.tif")]


def fetch_rasters(name: str, granules: list, variable: str, bbox: BBox, raw_dir: Path, out_dir: Path) -> list[Path]:
    """Download tiles to raw_dir, clip each to the box and write one GeoTIFF per granule to out_dir."""
    require_login()
    with remote_errors("downloading the granules"):
        if name == "hls":
            links = [link for g in granules for link in _band_links(g, variable)]
            if not links:
                raise InputError(f"no HLS band '{variable}' found (use names like B04, B8A, Fmask)")
            raw_dir.mkdir(parents=True, exist_ok=True)
            files = earthaccess.download(links, local_path=raw_dir)
        else:
            files = [f for f in _local_files(granules, raw_dir) if f.suffix.lower() in RASTER_SUFFIXES[name]]
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with remote_errors("reading the tiles"):
        for path in files:
            clipped = clip.clip_raster(path, bbox) if name == "hls" else clip.clip_tile(path, variable, bbox)
            target = out_dir / f"{safe_filename(path.stem)}_{safe_filename(variable)}.tif"
            clipped.rio.to_raster(target)
            written.append(target)
    return written
