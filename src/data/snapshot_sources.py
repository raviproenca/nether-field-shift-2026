# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Fetchers of the snapshot generator: one function per source, each returning SourceData for a list of points.

Reads are as light as the source allows: POWER one call per model cell, IMERG/GLDAS/SMAP only the box window of
each file over HTTPS (cached as small .npz files), VIIRS/MODIS one tile download per date sampled in place.
"""

import hashlib
import json
import math
import threading
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import partial
from pathlib import Path

import earthaccess
import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer

from . import clip, earthdata, et0, planetary, power, srtm
from .dates import DateRange
from .errors import DataToolkitError, InputError, RemoteDataError, describe_failure
from .regions import BBox, point_to_bbox
from .sampling import Layer, Point, sample_layer
from .snapshot_model import SourceData, SourceInfo, StaticData, Variable

SMAP_FILL = -9999.0
SMAP_VALID = (0.02, 0.5)
EARTH_RADIUS_M = 6371007.181
M_PER_DEGREE = EARTH_RADIUS_M * math.pi / 180
NDVI_STEP_DAYS = 16


@dataclass
class Context:
    """Everything a fetcher needs. `domain` is the box that covers every point plus a margin."""

    points: list[Point]
    domain: BBox
    days: int
    today: date
    raw_dir: Path
    cache_dir: Path
    workers: int = 4
    gldas_months: int = 6
    ndvi_days: int = 60
    power_lag_days: int = 4
    terrain_radius_km: float = 5.0
    elevations: dict[str, float] = field(default_factory=dict)
    log: Callable[[str], None] = print


INFOS: dict[str, SourceInfo] = {
    "power": SourceInfo(
        "power",
        "NASA POWER",
        "NASA Langley Research Center (POWER project)",
        True,
        "0.5° x 0.625° (MERRA-2), 1° (CERES solar)",
        "daily",
        "nearest_cell",
        "NASA POWER daily point API (MERRA-2 and CERES SYN1deg), community AG",
        None,
        "https://power.larc.nasa.gov/",
    ),
    "srtm": SourceInfo(
        "srtm",
        "NASADEM terrain (SRTM)",
        "NASA JPL NASADEM, served by Microsoft Planetary Computer",
        True,
        "30 m (1 arc-second)",
        "static (February 2000)",
        "window_mean",
        "NASADEM Merged DEM Global 1 arc-second V001 (NASADEM_HGT)",
        "10.5067/MEASURES/NASADEM/NASADEM_HGT.001",
        "https://planetarycomputer.microsoft.com/dataset/nasadem",
        None,
        "static",
    ),
    "gldas": SourceInfo(
        "gldas",
        "GLDAS Noah land surface model (monthly)",
        "NASA GSFC GES DISC",
        True,
        "0.25° (~25 km)",
        "monthly",
        "cell_mean",
        "GLDAS Noah Land Surface Model L4 monthly 0.25 x 0.25 degree V2.1 (GLDAS_NOAH025_M)",
        "10.5067/SXAVCZFAQLNO",
        "https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_M_2.1/summary",
    ),
    "imerg": SourceInfo(
        "imerg",
        "GPM IMERG precipitation (Late run)",
        "NASA GSFC GES DISC",
        True,
        "0.1° (~10 km)",
        "daily",
        "cell_mean",
        "GPM IMERG Late Precipitation L3 1 day 0.1 degree x 0.1 degree V07 (GPM_3IMERGDL)",
        "10.5067/GPM/IMERGDL/DAY/07",
        "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDL_07/summary",
    ),
    "smap": SourceInfo(
        "smap",
        "SMAP enhanced soil moisture (morning pass)",
        "NASA NSIDC DAAC",
        True,
        "9 km",
        "daily (gaps between orbits)",
        "cell_mean",
        "SMAP Enhanced L3 Radiometer Global and Polar Grid Daily 9 km EASE-Grid Soil Moisture V006 (SPL3SMP_E)",
        "10.5067/M20OXIZHY3RJ",
        "https://nsidc.org/data/spl3smp_e/versions/6",
    ),
    "viirs": SourceInfo(
        "viirs",
        "VIIRS vegetation index (NDVI)",
        "NASA LP DAAC",
        True,
        "500 m",
        "16-day composite, one every 16 days",
        "window_mean",
        "VIIRS/NPP Vegetation Indices 16-Day L3 Global 500m SIN Grid V002 (VNP13A1)",
        "10.5067/VIIRS/VNP13A1.002",
        "https://lpdaac.usgs.gov/products/vnp13a1v002/",
    ),
    "modis": SourceInfo(
        "modis",
        "MODIS vegetation index (NDVI)",
        "NASA LP DAAC",
        True,
        "250 m",
        "16-day composite",
        "window_mean",
        "MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1)",
        "10.5067/MODIS/MOD13Q1.061",
        "https://lpdaac.usgs.gov/products/mod13q1v061/",
    ),
}

POWER_INPUTS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M", "GWETROOT"]
POWER_VARIABLES = [
    Variable("T2M", "Air temperature at 2 m (daily mean)", "°C", 1),
    Variable("T2M_MAX", "Air temperature at 2 m (daily maximum)", "°C", 1),
    Variable("T2M_MIN", "Air temperature at 2 m (daily minimum)", "°C", 1),
    Variable("PRECTOTCORR", "Precipitation (bias-corrected)", "mm/day", 2),
    Variable("ALLSKY_SFC_SW_DWN", "All-sky surface shortwave downward irradiance", "MJ/m²/day", 1),
    Variable("GWETROOT", "Root zone soil wetness", "1 (fraction, 0-1)", 3),
]
ET0_VARIABLES = [
    Variable("ET0_FAO56", "Reference evapotranspiration, FAO-56 Penman-Monteith (derived from POWER)", "mm/day", 2),
    Variable("WATER_BALANCE", "Precipitation minus ET0 (derived from POWER)", "mm/day", 2),
]
TERRAIN_VARIABLES = [
    Variable("elevation_m", "Mean elevation inside the terrain radius", "m", 1),
    Variable("slope_mean_deg", "Mean slope inside the terrain radius", "°", 2),
    Variable("slope_mean_pct", "Mean slope inside the terrain radius", "%", 2),
]
GLDAS_VARIABLES = [
    Variable("SoilMoi0_10cm_inst", "Soil moisture, 0-10 cm layer", "kg/m² (= mm of water)", 1),
    Variable("SoilMoi10_40cm_inst", "Soil moisture, 10-40 cm layer", "kg/m² (= mm of water)", 1),
    Variable("Rainf_f_tavg", "Rainfall rate (monthly mean)", "mm/day", 2),
]
GLDAS_RAIN_TO_MM_PER_DAY = 86400.0
IMERG_VARIABLE = Variable("precipitation", "Daily precipitation (Late run)", "mm/day", 1)
SMAP_VARIABLE = Variable("soil_moisture", "Soil moisture, morning (6 a.m.) overpass", "m³/m³", 3)
NDVI_VARIABLE = Variable("NDVI", "Normalized Difference Vegetation Index", "1 (dimensionless, -1 to 1)", 3)


def _iso(day: date) -> str:
    return day.isoformat()


def _window(ctx: Context, lag: int = 0) -> DateRange:
    end = ctx.today - timedelta(days=lag)
    return DateRange(end - timedelta(days=ctx.days - 1), end)


def _one_per_day(granules: list) -> dict[date, object]:
    return {earthdata.granule_start(g).date(): g for g in sorted(granules, key=earthdata.granule_start)}


def _cached_windows(
    ctx: Context, source: str, items: dict[str, object], read: Callable[[object], tuple[np.ndarray, ...]]
) -> tuple[dict[str, tuple[np.ndarray, ...]], list[str]]:
    """Read one small window per key (in threads), caching each as .npz. Failures are returned, not raised."""
    folder = ctx.cache_dir / "snapshots" / source
    folder.mkdir(parents=True, exist_ok=True)
    tag = hashlib.sha1(repr(ctx.domain.as_tuple).encode()).hexdigest()[:8]

    def load(key: str):
        path = folder / f"{key}_{tag}.npz"
        if path.is_file():
            with np.load(path) as stored:
                return key, tuple(stored[name] for name in stored.files), None
        try:
            arrays = read(items[key])
        except Exception as exc:  # noqa: BLE001  a failed date must not stop the others
            return key, None, f"{key}: {describe_failure(exc)}"
        np.savez_compressed(path, *arrays)
        return key, arrays, None

    earthdata.require_login()  # earthaccess.open needs the session that login creates
    results, failures = {}, []
    with ThreadPoolExecutor(max_workers=ctx.workers) as pool:
        for done, (key, arrays, failure) in enumerate(pool.map(load, sorted(items)), start=1):
            if failure:
                failures.append(failure)
            else:
                results[key] = arrays
            if done % 5 == 0 or done == len(items):
                ctx.log(f"  {source}: {done}/{len(items)} dates")
    return results, failures


def _stack(
    windows: dict[str, tuple[np.ndarray, ...]], variables: int
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    """Sort windows by key and stack them: times, lat, lon, values[time, variable, lat, lon]."""
    times = sorted(windows)
    lat, lon = windows[times[0]][0], windows[times[0]][1]
    values = np.stack([np.stack(windows[t][2 : 2 + variables]) for t in times])
    return times, lat, lon, values


def _layer_values(layer_values: np.ndarray, lat: np.ndarray, lon: np.ndarray, points: list[Point], index: int):
    return sample_layer(Layer(lat, lon, layer_values[:, index]), points)


def _grid_result(ctx: Context, variables: list[Variable], windows: dict, failures: list[str], label: str) -> SourceData:
    if not windows:
        raise RemoteDataError(f"no {label} window could be read ({'; '.join(failures[:3])})")
    times, lat, lon, values = _stack(windows, len(variables))
    sampled = np.stack([_layer_values(values, lat, lon, ctx.points, i) for i in range(len(variables))], axis=-1)
    notes = [f"{label} failed on {len(failures)} date(s): {'; '.join(failures[:3])}"] if failures else []
    return SourceData(variables, times, np.transpose(sampled, (1, 0, 2)), times[-1], notes)


def _search(short_name: str, version: str, ctx: Context, dates: DateRange) -> list:
    return earthdata.search(short_name, ctx.domain, dates, version)


def _open_one(granule):
    return earthaccess.open([granule])[0]


def _power_cell(lat: float, lon: float) -> tuple[float, float]:
    """Center of the MERRA-2 cell (0.5° x 0.625°) that holds the point, which is what POWER answers with."""
    return round(round(lat / 0.5) * 0.5, 4), round(-180 + round((lon + 180) / 0.625) * 0.625, 4)


def _derived_et0(ctx: Context, frame: pd.DataFrame, point: Point) -> np.ndarray | None:
    """ET0 and water balance columns of one point, from the POWER inputs of its cell and the SRTM elevation."""
    elevation = ctx.elevations.get(point.id)
    if elevation is None:
        return None
    days = np.asarray(frame.index.dayofyear)
    inputs = [frame[name].to_numpy(dtype="float64") for name in ("T2M_MAX", "T2M_MIN", "RH2M", "WS2M")]
    et0_values = et0.et0_series(point.lat, elevation, days, *inputs, frame["ALLSKY_SFC_SW_DWN"].to_numpy("float64"))
    return np.stack([et0_values, frame["PRECTOTCORR"].to_numpy("float64") - et0_values], axis=-1)


def fetch_power(ctx: Context) -> SourceData:
    """One POWER call per MERRA-2 cell (cached in data/cache/power), shared by the points inside it.

    ET0 (FAO-56) and the water balance are derived per point from the cell's inputs and the point's elevation.
    """
    dates = _window(ctx, ctx.power_lag_days)
    cells = sorted({_power_cell(p.lat, p.lon) for p in ctx.points})
    ctx.log(f"  power: {len(cells)} cells for {len(ctx.points)} points")

    def one(cell):
        try:
            frame = power.fetch_point(cell[0], cell[1], dates, POWER_INPUTS, cache_dir=ctx.cache_dir / "power")
            return cell, frame.reindex(pd.date_range(dates.start, dates.end)), None
        except DataToolkitError as exc:
            return cell, None, f"cell {cell[0]},{cell[1]}: {exc}"

    with ThreadPoolExecutor(max_workers=min(ctx.workers, 4)) as pool:
        outcomes = list(pool.map(one, cells))
    frames = {cell: frame for cell, frame, _ in outcomes if frame is not None}
    failed = [text for _, _, text in outcomes if text]
    if not frames:
        raise RemoteDataError(f"POWER failed for every cell ({'; '.join(failed[:2])})")
    times = [_iso(d.date()) for d in pd.date_range(dates.start, dates.end)]
    published = POWER_VARIABLES + ET0_VARIABLES
    values = np.full((len(ctx.points), len(times), len(published)), np.nan)
    without_elevation = 0
    for row, point in enumerate(ctx.points):
        frame = frames.get(_power_cell(point.lat, point.lon))
        if frame is None:
            continue
        values[row, :, : len(POWER_VARIABLES)] = frame[[v.name for v in POWER_VARIABLES]].to_numpy(dtype="float64")
        derived = _derived_et0(ctx, frame, point)
        if derived is None:
            without_elevation += 1
        else:
            values[row, :, len(POWER_VARIABLES) :] = derived
    notes = [f"POWER failed for {len(failed)} cell(s): {'; '.join(failed[:2])}"] if failed else []
    if without_elevation:
        notes.append(f"ET0 and water balance are empty for {without_elevation} point(s) without SRTM elevation")
    return SourceData(published, times, values, times[-1], notes)


def _terrain_summary(bbox: BBox, client) -> list[float]:
    summary = srtm.summarize_terrain(srtm.fetch_elevation(bbox, client=client))
    return [summary["elevation_mean_m"], summary["slope_mean_deg"], summary["slope_mean_pct"]]


def fetch_srtm(ctx: Context) -> StaticData:
    """NASADEM elevation and mean slope inside `terrain_radius_km` of each point, read at 30 m (cached per point)."""
    folder = ctx.cache_dir / "snapshots" / "srtm"
    folder.mkdir(parents=True, exist_ok=True)
    local = threading.local()

    def one(point: Point):
        path = folder / f"{point.lat:.4f}_{point.lon:.4f}_{ctx.terrain_radius_km:g}.json"
        if path.is_file():
            return point.id, json.loads(path.read_text()), None
        try:
            if not hasattr(local, "client"):
                local.client = planetary.open_client()
            summary = _terrain_summary(point_to_bbox(point.lat, point.lon, ctx.terrain_radius_km), local.client)
        except Exception as exc:  # noqa: BLE001  a point without terrain must not stop the others
            return point.id, None, f"{point.id}: {describe_failure(exc)}"
        path.write_text(json.dumps(summary))
        return point.id, summary, None

    with ThreadPoolExecutor(max_workers=ctx.workers) as pool:
        outcomes = list(pool.map(one, ctx.points))
    failed = [text for _, _, text in outcomes if text]
    if len(failed) == len(outcomes):
        raise RemoteDataError(f"NASADEM failed for every point ({'; '.join(failed[:2])})")
    values = np.array([row if row else [np.nan] * 3 for _, row, _ in outcomes], dtype="float64")
    ctx.elevations = {pid: row[0] for pid, row, _ in outcomes if row}
    notes = [f"NASADEM failed for {len(failed)} point(s): {'; '.join(failed[:2])}"] if failed else []
    return StaticData(TERRAIN_VARIABLES, values, notes)


def _gldas_window(domain: BBox) -> Callable:
    def read(granule):
        with xr.open_dataset(_open_one(granule), engine="h5netcdf", phony_dims="sort") as ds:
            arrays = []
            for variable in GLDAS_VARIABLES:
                da = ds[variable.name].sel(lat=slice(domain.south, domain.north), lon=slice(domain.west, domain.east))
                da = da.squeeze(drop=True).load()
                scale = GLDAS_RAIN_TO_MM_PER_DAY if variable.unit == "mm/day" else 1.0
                arrays.append(da.transpose("lat", "lon").values.astype("float32") * scale)
            lat, lon = da["lat"].values.astype("float64"), da["lon"].values.astype("float64")
        return (lat, lon, *arrays)

    return read


def fetch_gldas(ctx: Context) -> SourceData:
    """Monthly GLDAS Noah (the 3-hourly product is never read raw): the last `gldas_months` months."""
    granules = _search("GLDAS_NOAH025_M", "2.1", ctx, DateRange(ctx.today - timedelta(days=31 * 14), ctx.today))
    months = _one_per_day(granules)
    chosen = {_iso(d): g for d, g in list(months.items())[-ctx.gldas_months :]}
    windows, failures = _cached_windows(ctx, "gldas", chosen, _gldas_window(ctx.domain))
    return _grid_result(ctx, GLDAS_VARIABLES, windows, failures, "GLDAS")


def _imerg_window(domain: BBox) -> Callable:
    def read(granule):
        with xr.open_dataset(_open_one(granule), engine="h5netcdf", phony_dims="sort") as ds:
            da = ds["precipitation"].sel(lat=slice(domain.south, domain.north), lon=slice(domain.west, domain.east))
            da = da.squeeze(drop=True).load().transpose("lat", "lon")
        return da["lat"].values.astype("float64"), da["lon"].values.astype("float64"), da.values.astype("float32")

    return read


def fetch_imerg(ctx: Context) -> SourceData:
    """Daily IMERG Late: the last `days` days available, box window read lazily once per day."""
    granules = _search("GPM_3IMERGDL", "07", ctx, DateRange(ctx.today - timedelta(days=ctx.days + 5), ctx.today))
    days = _one_per_day(granules)
    chosen = {_iso(d): g for d, g in list(days.items())[-ctx.days :]}
    windows, failures = _cached_windows(ctx, "imerg", chosen, _imerg_window(ctx.domain))
    return _grid_result(ctx, [IMERG_VARIABLE], windows, failures, "IMERG")


def ease2_axes() -> tuple[np.ndarray, np.ndarray]:
    """Row latitudes and column longitudes of the 9 km EASE-Grid 2.0 global grid (1624 x 3856), cell centers."""
    size = 9008.055210146
    cols = -17367530.4451615 + (np.arange(3856) + 0.5) * size
    rows = 7314540.83 - (np.arange(1624) + 0.5) * size
    to_geographic = Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True)
    lon, _ = to_geographic.transform(cols, np.zeros_like(cols))
    _, lat = to_geographic.transform(np.zeros_like(rows), rows)
    return lat, lon


def _smap_window(rows: slice, cols: slice) -> Callable:
    import h5py

    def read(granule):
        with h5py.File(_open_one(granule), "r") as h5:
            raw = h5["Soil_Moisture_Retrieval_Data_AM/soil_moisture"][rows, cols].astype("float32")
        raw[(raw == SMAP_FILL) | (raw < SMAP_VALID[0]) | (raw > SMAP_VALID[1])] = np.nan
        return (raw,)

    return read


def fetch_smap(ctx: Context) -> SourceData:
    """Daily SMAP soil moisture (AM pass): box window of each day read lazily; days without coverage stay empty."""
    lat, lon = ease2_axes()
    in_rows = np.flatnonzero((lat >= ctx.domain.south) & (lat <= ctx.domain.north))
    in_cols = np.flatnonzero((lon >= ctx.domain.west) & (lon <= ctx.domain.east))
    rows, cols = slice(int(in_rows.min()), int(in_rows.max()) + 1), slice(int(in_cols.min()), int(in_cols.max()) + 1)
    granules = _search("SPL3SMP_E", "006", ctx, DateRange(ctx.today - timedelta(days=ctx.days + 5), ctx.today))
    days = _one_per_day(granules)
    chosen = {_iso(d): g for d, g in list(days.items())[-ctx.days :]}
    windows, failures = _cached_windows(ctx, "smap", chosen, _smap_window(rows, cols))
    if not windows:
        raise RemoteDataError(f"no SMAP window could be read ({'; '.join(failures[:3])})")
    times = sorted(windows)
    layer = Layer(lat[rows], lon[cols], np.stack([windows[t][0] for t in times]))
    sampled = sample_layer(layer, ctx.points)
    notes = [f"SMAP failed on {len(failures)} date(s): {'; '.join(failures[:3])}"] if failures else []
    return SourceData([SMAP_VARIABLE], times, np.transpose(sampled)[:, :, None], times[-1], notes)


def tile_sums(tile: xr.DataArray, px: np.ndarray, py: np.ndarray, half_x: np.ndarray, half_y: np.ndarray):
    """Per point: sum and count of the valid pixels of a sinusoidal tile inside the box (px +- half_x, py +- half_y)."""
    x, y, values = tile["x"].values, tile["y"].values, tile.values
    sums, counts = np.zeros(px.size), np.zeros(px.size)
    for i in range(px.size):
        cols = np.flatnonzero((x >= px[i] - half_x[i]) & (x <= px[i] + half_x[i]))
        rows = np.flatnonzero((y >= py[i] - half_y[i]) & (y <= py[i] + half_y[i]))
        if cols.size == 0 or rows.size == 0:
            continue
        block = values[rows.min() : rows.max() + 1, cols.min() : cols.max() + 1]
        valid = np.isfinite(block)
        sums[i], counts[i] = np.where(valid, block, 0.0).sum(), valid.sum()
    return sums, counts


def sinusoidal_boxes(points: list[Point]):
    """Box centers (meters, MODIS sinusoidal) and half sizes of every point, as float arrays."""
    to_sinusoidal = Transformer.from_crs("EPSG:4326", clip.SINUSOIDAL_CRS, always_xy=True)
    lons, lats = np.array([p.lon for p in points]), np.array([p.lat for p in points])
    px, py = to_sinusoidal.transform(lons, lats)
    half_y = np.array([p.half for p in points]) * M_PER_DEGREE
    return np.asarray(px), np.asarray(py), half_y * np.cos(np.radians(lats)), half_y


def choose_composites(available: list[date], step: int = NDVI_STEP_DAYS, span: int = 60) -> list[date]:
    """Newest composite date first, then the newest one at least `step` days older, within `span` days of the first."""
    chosen: list[date] = []
    for day in sorted(available, reverse=True):
        if not chosen or (chosen[-1] - day).days >= step:
            if chosen and (chosen[0] - day).days > span:
                break
            chosen.append(day)
    return sorted(chosen)


def fetch_ndvi(ctx: Context, product: str) -> SourceData:
    """NDVI composites from VIIRS (default) or MODIS: one tile download per tile and date, sampled in place."""
    spec = earthdata.SOURCES[product]
    granules = earthdata.search(
        spec.short_name, ctx.domain, DateRange(ctx.today - timedelta(days=ctx.ndvi_days + 40), ctx.today), spec.version
    )
    by_date: dict[date, list] = defaultdict(list)
    for granule in granules:
        by_date[earthdata.granule_start(granule).date()].append(granule)
    dates = choose_composites(list(by_date), span=ctx.ndvi_days)
    px, py, half_x, half_y = sinusoidal_boxes(ctx.points)
    values = np.full((len(ctx.points), len(dates), 1), np.nan)
    failed: list[str] = []
    earthdata.require_login()
    suffix = earthdata.RASTER_SUFFIXES[product]
    ctx.raw_dir.joinpath(product).mkdir(parents=True, exist_ok=True)
    for column, day in enumerate(dates):
        ctx.log(f"  {product}: {_iso(day)} ({len(by_date[day])} tiles)")
        try:
            files = earthaccess.download(by_date[day], local_path=ctx.raw_dir / product, threads=ctx.workers)
            sums, counts = np.zeros(len(ctx.points)), np.zeros(len(ctx.points))
            for path in (f for f in files if Path(f).suffix.lower() in suffix):
                tile = clip.read_sinusoidal_tile(Path(path), "NDVI")
                tile_sum, tile_count = tile_sums(tile, px, py, half_x, half_y)
                sums, counts = sums + tile_sum, counts + tile_count
            with np.errstate(invalid="ignore", divide="ignore"):
                values[:, column, 0] = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
        except Exception as exc:  # noqa: BLE001  a failed date must not stop the others
            failed.append(f"{_iso(day)}: {describe_failure(exc)}")
    if len(failed) == len(dates):
        raise RemoteDataError(f"NDVI failed for every date ({'; '.join(failed[:2])})")
    notes = [f"{product} failed on {len(failed)} date(s): {'; '.join(failed[:2])}"] if failed else []
    return SourceData([NDVI_VARIABLE], [_iso(d) for d in dates], values, _iso(max(by_date)), notes)


FETCHERS: dict[str, Callable[[Context], SourceData]] = {
    "gldas": fetch_gldas,
    "srtm": fetch_srtm,
    "power": fetch_power,
    "imerg": fetch_imerg,
    "smap": fetch_smap,
    "viirs": partial(fetch_ndvi, product="viirs"),
    "modis": partial(fetch_ndvi, product="modis"),
}


def check_source(name: str) -> None:
    if name not in FETCHERS:
        raise InputError(f"unknown snapshot source '{name}'; choose from: {', '.join(FETCHERS)}")
