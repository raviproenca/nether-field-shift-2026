# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""NASA Earthdata sources via earthaccess: GLDAS, IMERG (GES DISC), SMAP (NSIDC), MODIS, VIIRS, HLS (LP DAAC).

Searching granules needs no login. Opening or downloading them does: run scripts/earthdata-login.sh once.
The download paths of this module have not been exercised against the real services (no credentials in CI).
"""

import os
from dataclasses import dataclass
from pathlib import Path

import earthaccess
import pandas as pd
import xarray as xr

from . import clip
from .dates import DateRange
from .errors import AuthRequiredError, InputError, RemoteDataError
from .regions import BBox

LOGIN_HINT = "run scripts/earthdata-login.sh first"


@dataclass(frozen=True)
class Source:
    """How one NASA source is fetched. kind: 'remote_grid', 'file_grid' or 'file_raster'."""

    short_name: str
    kind: str
    resolution: str
    note: str


SOURCES: dict[str, Source] = {
    "gldas": Source("GLDAS_NOAH025_3H", "remote_grid", "0.25 deg, 3-hourly", "GES DISC, v2.1"),
    "imerg": Source(
        "GPM_3IMERGDL", "remote_grid", "0.1 deg, daily", "GES DISC, Late run (Final run GPM_3IMERGDF ends 2025-09-30)"
    ),
    "smap": Source("SPL3SMP_E", "file_grid", "9 km, daily", "NSIDC, enhanced L3 soil moisture"),
    "modis": Source("MOD13Q1", "file_raster", "250 m, 16-day", "LP DAAC, Terra vegetation indices"),
    "viirs": Source("VNP13A1", "file_raster", "500 m, 16-day", "LP DAAC, VIIRS vegetation indices (MODIS continuity)"),
    "hls": Source(
        "HLSL30", "file_raster", "30 m, 2-3 days", "LP DAAC, Landsat; use --short-name HLSS30 for Sentinel-2"
    ),
}
RASTER_SUFFIXES = {"modis": (".hdf",), "viirs": (".h5",), "hls": (".tif",)}


def require_login() -> None:
    netrc = Path(os.environ.get("NETRC") or Path.home() / ".netrc")
    if not netrc.is_file():
        raise AuthRequiredError(f"no Earthdata Login credentials ({netrc} not found): {LOGIN_HINT}")
    try:
        earthaccess.login(strategy="netrc")
    except Exception as exc:  # earthaccess raises several unrelated types
        raise AuthRequiredError(f"Earthdata Login failed ({exc}): {LOGIN_HINT}") from exc


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
    except Exception as exc:
        raise RemoteDataError(f"CMR search failed for {short_name}: {exc}") from exc
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


def _clip_grid(granule, handle, variable: str, bbox: BBox, kind: str) -> pd.DataFrame:
    ds, name = _open_dataset(handle, variable)
    if name not in ds:
        raise InputError(f"variable '{name}' not found; available: {', '.join(ds.data_vars)}")
    da = clip.clip_latlon(ds[name], bbox) if kind == "remote_grid" else clip.clip_curvilinear(ds, name, bbox)
    if "time" not in da.dims and "time" not in da.coords:
        da = da.expand_dims(time=[granule_start(granule)])
    return clip.to_long_frame(da, name)


def fetch_grid(
    source: Source, granules: list, variable: str, bbox: BBox, raw_dir: Path, download_full: bool = False
) -> pd.DataFrame:
    """Long table (time, lat, lon, value) for GLDAS, IMERG and SMAP.

    GLDAS/IMERG are read lazily over HTTPS (earthaccess.open) so only the bytes of the box are transferred,
    unless download_full is set. SMAP files are always downloaded to raw_dir and clipped locally.
    """
    require_login()
    if source.kind == "file_grid" or download_full:
        handles = _local_files(granules, raw_dir)
    else:
        handles = earthaccess.open(granules)
    frames = [_clip_grid(g, h, variable, bbox, source.kind) for g, h in zip(granules, handles)]
    return pd.concat(frames, ignore_index=True)


def _band_links(granule, band: str) -> list[str]:
    return [url for url in granule.data_links() if url.endswith(f".{band}.tif")]


def fetch_rasters(name: str, granules: list, variable: str, bbox: BBox, raw_dir: Path, out_dir: Path) -> list[Path]:
    """Download tiles to raw_dir, clip each to the box and write one GeoTIFF per granule to out_dir."""
    require_login()
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
    for path in files:
        clipped = clip.clip_raster(path, bbox) if name == "hls" else clip.clip_tile(path, variable, bbox)
        target = out_dir / f"{path.stem}_{variable.replace(' ', '_')}.tif"
        clipped.rio.to_raster(target)
        written.append(target)
    return written
