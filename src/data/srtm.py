# AI-assisted: generated with Antigravity, reviewed by dudxyz
"""NASA NASADEM / SRTM 30 m terrain elevation and slope clipping (public via Planetary Computer STAC)."""

import math
from pathlib import Path

import numpy as np
import pystac_client
import rioxarray
import rioxarray.merge
import xarray as xr
from pystac import Item

from . import clip, planetary
from .errors import InputError, RemoteDataError, remote_errors
from .regions import KM_PER_DEGREE_LAT, BBox

COLLECTION = "nasadem"
ASSET = "elevation"
DEFAULT_RESOLUTION_M = 30.0
DEFAULT_MAX_PIXELS = planetary.DEFAULT_MAX_PIXELS
SRTM_VARIABLES = ("elevation", "slope_deg", "slope_pct", "all")
ATTRIBUTION = (
    "NASA JPL NASADEM Merged DEM Global 1 arc-second v001 "
    "(DOI: 10.5067/MEASURES/NASADEM/NASADEM_HGT.001), served by Microsoft Planetary Computer"
)


def estimate_pixels(bbox: BBox, resolution_m: float = DEFAULT_RESOLUTION_M) -> int:
    """Rough pixel count of a box at 30 m spacing, used as a size guard before network I/O."""
    width_m = (bbox.east - bbox.west) * KM_PER_DEGREE_LAT * 1000.0 * math.cos(math.radians(bbox.center[0]))
    height_m = (bbox.north - bbox.south) * KM_PER_DEGREE_LAT * 1000.0
    return max(1, math.ceil(width_m / resolution_m)) * max(1, math.ceil(height_m / resolution_m))


def check_size(bbox: BBox, max_pixels: int = DEFAULT_MAX_PIXELS) -> None:
    """Refuse huge DEM requests before touching the network."""
    pixels = estimate_pixels(bbox)
    if pixels > max_pixels:
        raise InputError(
            f"the box is about {pixels / 1e6:.1f} million pixels at 30 m, above the limit of "
            f"{max_pixels / 1e6:.0f} million: use a smaller --point/--radius-km (or --bbox), "
            "or raise the limit with --max-pixels"
        )


def search_tiles(client: pystac_client.Client, bbox: BBox) -> list[Item]:
    """Find NASADEM tiles intersecting the bounding box (static 2000-02 epoch; no date filter)."""
    with remote_errors("Planetary Computer search for nasadem"):
        items = list(client.search(collections=[COLLECTION], bbox=list(bbox.as_tuple)).items())
    if not items:
        raise RemoteDataError("no nasadem tiles found for this bounding box")
    return sorted(items, key=lambda item: item.id)


def fetch_elevation(
    bbox: BBox,
    client: pystac_client.Client | None = None,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> xr.DataArray:
    """Clip 30 m NASADEM elevation (meters) to the bounding box, merging adjacent tiles if needed."""
    check_size(bbox, max_pixels)
    stac = client or planetary.open_client()
    items = search_tiles(stac, bbox)
    pieces: list[xr.DataArray] = []
    for item in items:
        href = planetary.asset_href(item, ASSET)
        with remote_errors(f"reading elevation of {item.id}"):
            try:
                with rioxarray.open_rasterio(href, masked=True) as lazy:
                    clipped = clip.clip_box_latlon(lazy, bbox, item.id).load()
            except InputError:
                continue
        if "band" in clipped.dims and clipped.sizes["band"] == 1:
            clipped = clipped.squeeze("band", drop=True)
        pieces.append(clipped.astype("float32"))
    if not pieces:
        raise InputError("no nasadem tile has data inside the bounding box")
    merged = pieces[0] if len(pieces) == 1 else rioxarray.merge.merge_arrays(pieces, nodata=np.nan)
    merged = merged.astype("float32")
    merged.name = "elevation"
    if merged.rio.crs is None:
        merged = merged.rio.write_crs("EPSG:4326")
    return merged.rio.write_nodata(np.nan)


def compute_slope(elevation: xr.DataArray) -> tuple[xr.DataArray, xr.DataArray]:
    """Return (slope_deg, slope_pct) from an elevation grid in EPSG:4326 (meters)."""
    elev = elevation.squeeze("band", drop=True) if "band" in elevation.dims else elevation
    values = elev.values.astype("float64")
    if values.ndim != 2:
        raise InputError(f"expected 2-D elevation array, got shape {values.shape}")
    if elev.sizes["y"] < 2 or elev.sizes["x"] < 2:
        zeros = np.where(np.isfinite(values), 0.0, np.nan).astype("float32")
        deg = elev.copy(data=zeros).rename("slope_deg")
        pct = elev.copy(data=zeros.copy()).rename("slope_pct")
        return deg.rio.write_nodata(np.nan), pct.rio.write_nodata(np.nan)

    dlat_deg = abs(float(np.median(np.diff(elev["y"].values)))) or (1.0 / 3600.0)
    dlon_deg = abs(float(np.median(np.diff(elev["x"].values)))) or (1.0 / 3600.0)
    lat_center = float(np.nanmean(elev["y"].values))
    dy_m = dlat_deg * KM_PER_DEGREE_LAT * 1000.0
    dx_m = dlon_deg * KM_PER_DEGREE_LAT * 1000.0 * max(1e-6, math.cos(math.radians(lat_center)))

    dz_dy, dz_dx = np.gradient(values, dy_m, dx_m)
    grad = np.hypot(dz_dy, dz_dx)
    slope_deg = np.degrees(np.arctan(grad)).astype("float32")
    slope_pct = (grad * 100.0).astype("float32")

    deg_da = elev.copy(data=slope_deg).rename("slope_deg").rio.write_nodata(np.nan)
    pct_da = elev.copy(data=slope_pct).rename("slope_pct").rio.write_nodata(np.nan)
    if elev.rio.crs is not None:
        deg_da = deg_da.rio.write_crs(elev.rio.crs)
        pct_da = pct_da.rio.write_crs(elev.rio.crs)
    return deg_da, pct_da


def summarize_terrain(elevation: xr.DataArray) -> dict:
    """Compute elevation & slope summary statistics for the clipped bounding box."""
    elev_values = elevation.values.astype("float64")
    finite_elev = elev_values[np.isfinite(elev_values)]
    if finite_elev.size == 0:
        raise InputError("elevation raster has no valid pixels inside the bounding box")
    slope_deg, slope_pct = compute_slope(elevation)
    finite_deg = slope_deg.values[np.isfinite(slope_deg.values)]
    finite_pct = slope_pct.values[np.isfinite(slope_pct.values)]
    mean_pct = float(np.mean(finite_pct)) if finite_pct.size else 0.0
    return {
        "source": "srtm",
        "collection": COLLECTION,
        "resolution": "30 m (1 arc-second)",
        "valid_pixels": int(finite_elev.size),
        "elevation_min_m": round(float(np.min(finite_elev)), 2),
        "elevation_mean_m": round(float(np.mean(finite_elev)), 2),
        "elevation_max_m": round(float(np.max(finite_elev)), 2),
        "elevation_range_m": round(float(np.max(finite_elev) - np.min(finite_elev)), 2),
        "slope_mean_deg": round(float(np.mean(finite_deg)), 2) if finite_deg.size else 0.0,
        "slope_max_deg": round(float(np.max(finite_deg)), 2) if finite_deg.size else 0.0,
        "slope_mean_pct": round(mean_pct, 2),
        "slope_max_pct": round(float(np.max(finite_pct)), 2) if finite_pct.size else 0.0,
        "nasa": True,
        "attribution": ATTRIBUTION,
    }


def write_rasters(
    bbox: BBox,
    out_dir: Path,
    variable: str = "elevation",
    client: pystac_client.Client | None = None,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> tuple[list[Path], dict]:
    """Fetch NASADEM elevation, compute slope when asked, write GeoTIFF(s) to out_dir and return summary."""
    key = (variable or "elevation").strip().lower()
    if key not in SRTM_VARIABLES:
        raise InputError(f"unsupported srtm variable '{variable}': choose from {', '.join(SRTM_VARIABLES)}")
    elevation = fetch_elevation(bbox, client=client, max_pixels=max_pixels)
    summary = summarize_terrain(elevation)
    rasters: dict[str, xr.DataArray] = {"elevation": elevation}
    if key in ("slope_deg", "slope_pct", "all"):
        slope_deg, slope_pct = compute_slope(elevation)
        rasters["slope_deg"] = slope_deg
        rasters["slope_pct"] = slope_pct
    targets = ("elevation", "slope_deg", "slope_pct") if key == "all" else (key,)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in targets:
        target = out_dir / f"srtm_{name}.tif"
        rasters[name].rio.to_raster(target)
        written.append(target)
    return written, summary
