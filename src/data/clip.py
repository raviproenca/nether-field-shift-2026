# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Local clipping of downloaded data to a bounding box (lat/lon grids, curvilinear grids, rasters, HDF tiles)."""

import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import rioxarray
import xarray as xr
from rioxarray.exceptions import NoDataInBounds

from .errors import InputError
from .regions import BBox

LAT_NAMES = ("lat", "latitude")
LON_NAMES = ("lon", "longitude")
SINUSOIDAL_CRS = "+proj=sinu +R=6371007.181 +units=m +no_defs"


def _coord_name(obj: xr.Dataset | xr.DataArray, candidates: tuple[str, ...]) -> str:
    for name in (*candidates, *(f"{c}_pm" for c in candidates)):  # SMAP's PM group names them latitude_pm
        if name in obj.coords or name in getattr(obj, "data_vars", {}):
            return name
    raise InputError(f"no coordinate named {' or '.join(candidates)} in the data")


class NearestCellWarning(UserWarning):
    """The box is smaller than a grid cell, so the nearest cell to its center was used."""


def _warn_nearest(what: str) -> None:
    warnings.warn(
        f"the box is smaller than a {what} cell; using the cell nearest to the box center", NearestCellWarning
    )


def _within_extent(values: np.ndarray, low: float, high: float) -> bool:
    """True when [low, high] touches the span of the values (1-D axis or 2-D lat/lon array), plus half a cell.

    The cell size is the largest step between neighbours along each array axis, so the jump between the end of
    one row and the start of the next in a 2-D array never counts as a step.
    """
    finite = values[np.isfinite(values)]
    steps = [np.nanmax(np.abs(np.diff(values, axis=axis))) for axis in range(values.ndim) if values.shape[axis] > 1]
    margin = max(steps, default=0.0) / 2
    return low <= finite.max() + margin and high >= finite.min() - margin


def _box_reaches_axis(values: np.ndarray, low: float, high: float) -> bool:
    """True when the center of [low, high] is within half a (local) cell of the nearest axis value."""
    center = (low + high) / 2
    nearest = int(np.argmin(np.abs(values - center)))
    steps = [abs(values[j] - values[nearest]) for j in (nearest - 1, nearest + 1) if 0 <= j < values.size]
    return abs(values[nearest] - center) <= max(steps, default=0.0) / 2


def _axis_slice(values: np.ndarray, low: float, high: float) -> slice:
    return slice(low, high) if values[0] <= values[-1] else slice(high, low)


def clip_latlon(da: xr.DataArray, bbox: BBox) -> xr.DataArray:
    """Clip a grid with 1-D lat/lon coordinates (GLDAS, IMERG), ascending or descending."""
    lat_name, lon_name = _coord_name(da, LAT_NAMES), _coord_name(da, LON_NAMES)
    clipped = da.sel(
        {
            lat_name: _axis_slice(da[lat_name].values, bbox.south, bbox.north),
            lon_name: _axis_slice(da[lon_name].values, bbox.west, bbox.east),
        }
    )
    if clipped.size == 0:
        inside = _box_reaches_axis(da[lat_name].values, bbox.south, bbox.north) and _box_reaches_axis(
            da[lon_name].values, bbox.west, bbox.east
        )
        if not inside:
            raise InputError("the bounding box does not overlap the data grid")
        lat, lon = bbox.center
        clipped = da.sel({lat_name: [lat], lon_name: [lon]}, method="nearest")
        _warn_nearest("grid")
    return clipped.rename({lat_name: "lat", lon_name: "lon"})


def _valid_coordinates(values: np.ndarray, limit: float) -> np.ndarray:
    """Coordinates as float with fill values and anything outside +-limit turned into NaN.

    SMAP stores -9999 in its 2-D latitude/longitude arrays without declaring it as a fill value.
    """
    values = values.astype("float64")
    return np.where(np.abs(values) <= limit, values, np.nan)


def _axis_vector(values: np.ndarray, axis: int, tolerance: float = 1e-3) -> np.ndarray | None:
    """1-D coordinates when a 2-D array is constant along `axis` (EASE-Grid 2.0: one latitude per row, one
    longitude per column), ignoring NaN holes. None when it is not constant or not monotonic."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN rows or columns
        high, low = np.nanmax(values, axis=axis), np.nanmin(values, axis=axis)
        spread = np.nanmax(high - low) if np.isfinite(high).any() else np.inf
    steps = np.diff(high[np.isfinite(high)])
    monotonic = steps.size > 0 and (np.all(steps > 0) or np.all(steps < 0))
    return high if spread <= tolerance and monotonic else None


def clip_curvilinear(ds: xr.Dataset, variable: str, bbox: BBox) -> xr.DataArray:
    """Clip a 2-D array that carries 2-D latitude/longitude arrays (SMAP EASE-Grid).

    Fill values in the coordinate arrays are ignored. When latitude is constant per row and longitude per
    column (EASE-Grid 2.0) the grid is clipped through those two 1-D axes; otherwise cell by cell, with cells
    outside the box set to NaN.
    """
    lat_name, lon_name = _coord_name(ds, LAT_NAMES), _coord_name(ds, LON_NAMES)
    lat = ds[lat_name].copy(data=_valid_coordinates(ds[lat_name].values, 90))
    lon = ds[lon_name].copy(data=_valid_coordinates(ds[lon_name].values, 180))
    da = ds[variable]
    row_dim, col_dim = lat.dims
    lat_axis, lon_axis = _axis_vector(lat.values, axis=1), _axis_vector(lon.values, axis=0)
    if lat_axis is not None and lon_axis is not None:
        keep_rows, keep_cols = np.isfinite(lat_axis), np.isfinite(lon_axis)
        axes = da.isel({row_dim: keep_rows, col_dim: keep_cols})
        axes = axes.assign_coords(lat=(row_dim, lat_axis[keep_rows]), lon=(col_dim, lon_axis[keep_cols]))
        return clip_latlon(axes.swap_dims({row_dim: "lat", col_dim: "lon"}), bbox)
    inside = (lat >= bbox.south) & (lat <= bbox.north) & (lon >= bbox.west) & (lon <= bbox.east)
    rows, cols = np.where(inside.values)
    if rows.size == 0:
        if not (
            _within_extent(lat.values, bbox.south, bbox.north) and _within_extent(lon.values, bbox.west, bbox.east)
        ):
            raise InputError("no grid cell falls inside the bounding box")
        center_lat, center_lon = bbox.center
        distance = (lat - center_lat) ** 2 + ((lon - center_lon) * np.cos(np.radians(center_lat))) ** 2
        rows, cols = np.unravel_index(int(np.nanargmin(distance.values)), distance.shape)
        inside = xr.zeros_like(inside)
        inside[int(rows), int(cols)] = True
        rows, cols = np.array([rows]), np.array([cols])
        _warn_nearest("grid")
    window = {inside.dims[0]: slice(rows.min(), rows.max() + 1), inside.dims[1]: slice(cols.min(), cols.max() + 1)}
    clipped = da.isel(window).where(inside.isel(window))
    return clipped.assign_coords(lat=lat.isel(window), lon=lon.isel(window))


def mask_valid_range(da: xr.DataArray) -> xr.DataArray:
    """NaN outside the variable's valid_min/valid_max (or valid_range) attributes, when it declares them.

    Skipped for variables xarray unpacked with scale_factor/add_offset: their valid range is in packed units.
    """
    if "scale_factor" in da.encoding or "add_offset" in da.encoding:
        return da
    bounds, valid_min, valid_max = (_numbers(da.attrs, n) for n in ("valid_range", "valid_min", "valid_max"))
    low = bounds[0] if bounds.size == 2 else (valid_min[0] if valid_min.size == 1 else None)
    high = bounds[1] if bounds.size == 2 else (valid_max[0] if valid_max.size == 1 else None)
    if low is not None:
        da = da.where(da >= low)
    if high is not None:
        da = da.where(da <= high)
    return da


def to_long_frame(da: xr.DataArray, value_name: str) -> pd.DataFrame:
    """Flatten a clipped array to rows: time (if any), lat, lon, value. Empty cells are dropped."""
    frame = da.rename(value_name).to_dataframe().reset_index()
    columns = [c for c in ("time", "lat", "lon") if c in frame.columns] + [value_name]
    return frame[columns].dropna(subset=[value_name]).reset_index(drop=True)


def clip_box_latlon(da: xr.DataArray, bbox: BBox, label: str) -> xr.DataArray:
    """rioxarray clip_box with a lat/lon box (reprojected to the raster CRS) and a friendly error."""
    try:
        return da.rio.clip_box(*bbox.as_tuple, crs="EPSG:4326")
    except NoDataInBounds:
        raise InputError(f"{label} does not overlap the bounding box") from None


def clip_raster(path: Path, bbox: BBox) -> xr.DataArray:
    """Clip a GeoTIFF (HLS) to a lat/lon box."""
    with rioxarray.open_rasterio(path, masked=True) as lazy:
        return clip_box_latlon(lazy, bbox, path.name).load()


def _parse_grid_metadata(text: str) -> tuple[tuple[float, float], tuple[float, float], int, int]:
    def pair(key: str) -> tuple[float, float]:
        match = re.search(rf"{key}=\(([-\d.eE+]+),([-\d.eE+]+)\)", text)
        if not match:
            raise InputError(f"HDF-EOS metadata has no {key}")
        return float(match.group(1)), float(match.group(2))

    def integer(key: str) -> int:
        match = re.search(rf"{key}=(\d+)", text)
        if not match:
            raise InputError(f"HDF-EOS metadata has no {key}")
        return int(match.group(1))

    return pair("UpperLeftPointMtrs"), pair("LowerRightMtrs"), integer("XDim"), integer("YDim")


def _numbers(attrs: dict, name: str) -> np.ndarray:
    """Attribute (case-insensitive) as a flat float array: scalars and 1- or 2-element arrays alike.

    Empty when the attribute is missing or not numeric. HDF5 attributes often come as 1-element arrays
    (scale_factor) and valid_range or even _FillValue as 2-element ones.
    """
    for key, value in attrs.items():
        if key.lower() == name.lower():
            try:
                return np.asarray(value, dtype="float64").ravel()
            except (TypeError, ValueError):
                return np.array([])
    return np.array([])


def _scalar(attrs: dict, name: str, default: float | None = None) -> float | None:
    values = _numbers(attrs, name)
    return float(values[0]) if values.size == 1 else default


def _pick_unique(variable: str, names: list[str], where: str) -> str:
    """An exact (case-insensitive) name wins; otherwise the text must match exactly one dataset."""
    exact = [name for name in names if name.split("/")[-1].lower() == variable.lower()]
    matches = exact or [name for name in names if variable.lower() in name.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise InputError(f"no dataset matching '{variable}' in {where}; found: {', '.join(names)}")
    raise InputError(f"'{variable}' matches several datasets in {where}: {', '.join(matches)}; use a longer name")


def _read_hdf4(path: Path, variable: str) -> tuple[str, np.ndarray, dict, str]:
    from pyhdf.SD import SD, SDC

    sd = SD(str(path), SDC.READ)
    try:
        name = _pick_unique(variable, list(sd.datasets()), path.name)
        sds = sd.select(name)
        return name, sds.get(), sds.attributes(), sd.attributes()["StructMetadata.0"]
    finally:
        sd.end()


def _read_hdf5(path: Path, variable: str) -> tuple[str, np.ndarray, dict, str]:
    import h5py

    with h5py.File(path, "r") as h5:
        names: list[str] = []
        h5.visititems(lambda name, obj: names.append(name) if isinstance(obj, h5py.Dataset) else None)
        name = _pick_unique(variable, names, path.name)
        dataset = h5[name]
        meta = h5["HDFEOS INFORMATION/StructMetadata.0"][()]
        return name, dataset[()], dict(dataset.attrs), meta.decode() if isinstance(meta, bytes) else str(meta)


VI_NAME = re.compile(r"\b(NDVI|EVI2?)\b", re.IGNORECASE)
VI_RANGE = (-1.0, 1.5)


def _check_vegetation_index_range(name: str, array: np.ndarray) -> None:
    """NDVI/EVI must be about -1..1 after scaling; anything else means scale_factor is missing or inverted."""
    if not VI_NAME.search(name) or not np.isfinite(array).any():
        return
    low, high = float(np.nanmin(array)), float(np.nanmax(array))
    if low < VI_RANGE[0] or high > VI_RANGE[1]:
        raise InputError(
            f"scale_factor looks inverted: '{name}' has valid values from {low:g} to {high:g}, "
            f"outside {VI_RANGE[0]:g}..{VI_RANGE[1]:g}"
        )


def unpack_values(raw: np.ndarray, attrs: dict, hdf4: bool) -> np.ndarray:
    """Physical values from raw integers: fill values and values outside valid_range first, then scaling.

    Two conventions exist and are told apart explicitly:
    - HDF5 (VIIRS) follows CF: value = raw * scale_factor + add_offset.
    - HDF4 (MODIS) with scale_factor > 1 (e.g. 10000 for MOD13 NDVI/EVI): value = (raw - add_offset) / scale_factor.
      A HDF4 scale_factor <= 1 (e.g. 0.02 for MOD11 LST) is a multiplier, as in CF.
    _FillValue may hold several numbers (VIIRS: -15000 and -13000) and valid_range is a [min, max] pair.
    """
    array = raw.astype("float64")
    fills, valid = _numbers(attrs, "_FillValue"), _numbers(attrs, "valid_range")
    array[np.isin(raw, fills)] = np.nan
    if valid.size == 2:
        array[(raw < valid[0]) | (raw > valid[1])] = np.nan
    scale, offset = _scalar(attrs, "scale_factor"), _scalar(attrs, "add_offset", 0.0)
    if scale is None:
        return array - offset if offset else array
    return array * scale + offset


def read_sinusoidal_tile(path: Path, variable: str) -> xr.DataArray:
    """Read one variable of a MODIS (HDF4) or VIIRS (HDF5) sinusoidal tile as a georeferenced array.

    Fill values and out-of-range values become NaN, then scale_factor/add_offset are applied (see unpack_values).
    """
    hdf4 = path.suffix.lower() == ".hdf"
    reader = _read_hdf4 if hdf4 else _read_hdf5
    name, values, attrs, metadata = reader(path, variable)
    (ul_x, ul_y), (lr_x, lr_y), x_dim, y_dim = _parse_grid_metadata(metadata)
    if values.shape != (y_dim, x_dim):
        raise InputError(f"'{variable}' is not a {y_dim}x{x_dim} tile grid (shape {values.shape})")
    array = unpack_values(values, attrs, hdf4)
    _check_vegetation_index_range(name, array)
    step_x, step_y = (lr_x - ul_x) / x_dim, (ul_y - lr_y) / y_dim
    da = xr.DataArray(
        array,
        dims=("y", "x"),
        coords={"y": ul_y - (np.arange(y_dim) + 0.5) * step_y, "x": ul_x + (np.arange(x_dim) + 0.5) * step_x},
        name=name.split("/")[-1],
    )
    return da.rio.write_crs(SINUSOIDAL_CRS).rio.write_nodata(np.nan)


def clip_tile(path: Path, variable: str, bbox: BBox) -> xr.DataArray:
    return clip_box_latlon(read_sinusoidal_tile(path, variable), bbox, path.name)
