# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Local clipping of downloaded data to a bounding box (lat/lon grids, curvilinear grids, rasters, HDF tiles)."""

import re
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
    for name in candidates:
        if name in obj.coords or name in getattr(obj, "data_vars", {}):
            return name
    raise InputError(f"no coordinate named {' or '.join(candidates)} in the data")


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
        raise InputError("the bounding box does not overlap the data grid")
    return clipped.rename({lat_name: "lat", lon_name: "lon"})


def clip_curvilinear(ds: xr.Dataset, variable: str, bbox: BBox) -> xr.DataArray:
    """Clip a 2-D array that carries 2-D latitude/longitude arrays (SMAP EASE-Grid); outside cells become NaN."""
    lat, lon = ds[_coord_name(ds, LAT_NAMES)], ds[_coord_name(ds, LON_NAMES)]
    inside = (lat >= bbox.south) & (lat <= bbox.north) & (lon >= bbox.west) & (lon <= bbox.east)
    rows, cols = np.where(inside.values)
    if rows.size == 0:
        raise InputError("no grid cell falls inside the bounding box")
    window = {inside.dims[0]: slice(rows.min(), rows.max() + 1), inside.dims[1]: slice(cols.min(), cols.max() + 1)}
    da = ds[variable].isel(window).where(inside.isel(window))
    return da.assign_coords(lat=lat.isel(window), lon=lon.isel(window))


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
    return clip_box_latlon(rioxarray.open_rasterio(path, masked=True), bbox, path.name)


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


def _attr(attrs: dict, name: str):
    for key, value in attrs.items():
        if key.lower() == name.lower():
            return value.item() if hasattr(value, "item") else value
    return None


def _read_hdf4(path: Path, variable: str) -> tuple[np.ndarray, dict, str]:
    from pyhdf.SD import SD, SDC

    sd = SD(str(path), SDC.READ)
    try:
        names = [name for name in sd.datasets() if variable.lower() in name.lower()]
        if not names:
            raise InputError(f"no HDF4 dataset matching '{variable}' in {path.name}; found: {', '.join(sd.datasets())}")
        sds = sd.select(names[0])
        return sds.get(), sds.attributes(), sd.attributes()["StructMetadata.0"]
    finally:
        sd.end()


def _read_hdf5(path: Path, variable: str) -> tuple[np.ndarray, dict, str]:
    import h5py

    with h5py.File(path, "r") as h5:
        found: list[str] = []
        h5.visititems(
            lambda name, obj: (
                found.append(name)
                if isinstance(obj, h5py.Dataset) and name.split("/")[-1].lower() == variable.lower()
                else None
            )
        )
        if not found:
            raise InputError(f"no HDF5 dataset named '{variable}' in {path.name}")
        dataset = h5[found[0]]
        meta = h5["HDFEOS INFORMATION/StructMetadata.0"][()]
        return dataset[()], dict(dataset.attrs), meta.decode() if isinstance(meta, bytes) else str(meta)


def read_sinusoidal_tile(path: Path, variable: str) -> xr.DataArray:
    """Read one variable of a MODIS (HDF4) or VIIRS (HDF5) sinusoidal tile as a georeferenced array.

    Fill values become NaN and scale_factor is applied when the file declares them.
    """
    reader = _read_hdf4 if path.suffix.lower() == ".hdf" else _read_hdf5
    values, attrs, metadata = reader(path, variable)
    (ul_x, ul_y), (lr_x, lr_y), x_dim, y_dim = _parse_grid_metadata(metadata)
    if values.shape != (y_dim, x_dim):
        raise InputError(f"'{variable}' is not a {y_dim}x{x_dim} tile grid (shape {values.shape})")
    array = values.astype("float64")
    fill, scale = _attr(attrs, "_FillValue"), _attr(attrs, "scale_factor")
    if fill is not None:
        array[values == fill] = np.nan
    if scale is not None:
        array = array * float(scale)
    step_x, step_y = (lr_x - ul_x) / x_dim, (ul_y - lr_y) / y_dim
    da = xr.DataArray(
        array,
        dims=("y", "x"),
        coords={"y": ul_y - (np.arange(y_dim) + 0.5) * step_y, "x": ul_x + (np.arange(x_dim) + 0.5) * step_x},
        name=variable,
    )
    return da.rio.write_crs(SINUSOIDAL_CRS)


def clip_tile(path: Path, variable: str, bbox: BBox) -> xr.DataArray:
    return clip_box_latlon(read_sinusoidal_tile(path, variable), bbox, path.name)
