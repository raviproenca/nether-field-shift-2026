# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Clipping tests on small synthetic files (no network, no login)."""

import numpy as np
import pytest
import rasterio
import xarray as xr
from rasterio.transform import from_origin

from src.data import clip
from src.data.errors import InputError
from src.data.regions import BBox

BOX = BBox(-38.0, -11.0, -37.0, -10.0)


def test_clip_latlon_ascending_and_descending():
    lat, lon = np.arange(-12, -8.9, 0.5), np.arange(-39, -35.9, 0.5)
    data = np.arange(lat.size * lon.size, dtype=float).reshape(lat.size, lon.size)
    da = xr.DataArray(data, dims=("lat", "lon"), coords={"lat": lat, "lon": lon})
    asc = clip.clip_latlon(da, BOX)
    desc = clip.clip_latlon(da.isel(lat=slice(None, None, -1)), BOX)
    assert asc.lat.min() >= -11.0 and asc.lat.max() <= -10.0 and asc.shape == (3, 3)
    assert desc.shape == asc.shape


def test_clip_latlon_rejects_no_overlap_and_renames_long_names():
    da = xr.DataArray(
        np.ones((2, 2)), dims=("latitude", "longitude"), coords={"latitude": [0.0, 1.0], "longitude": [0.0, 1.0]}
    )
    with pytest.raises(InputError, match="does not overlap"):
        clip.clip_latlon(da, BOX)
    near = clip.clip_latlon(da, BBox(-0.5, -0.5, 1.5, 1.5))
    assert set(near.dims) == {"lat", "lon"}


def test_clip_curvilinear_masks_outside_cells():
    lat, lon = np.meshgrid(np.arange(-12, -8.9, 0.5), np.arange(-39, -35.9, 0.5), indexing="ij")
    ds = xr.Dataset(
        {"sm": (("r", "c"), np.ones(lat.shape))}, coords={"latitude": (("r", "c"), lat), "longitude": (("r", "c"), lon)}
    )
    da = clip.clip_curvilinear(ds, "sm", BOX)
    assert da.shape == (3, 3) and float(da.lat.min()) == -11.0
    frame = clip.to_long_frame(da.expand_dims(time=[np.datetime64("2025-01-01")]), "sm")
    assert list(frame.columns) == ["time", "lat", "lon", "sm"] and len(frame) == 9


def test_clip_curvilinear_empty():
    ds = xr.Dataset(
        {"sm": (("r", "c"), [[1.0]])}, coords={"latitude": (("r", "c"), [[50.0]]), "longitude": (("r", "c"), [[10.0]])}
    )
    with pytest.raises(InputError, match="no grid cell"):
        clip.clip_curvilinear(ds, "sm", BOX)


def test_clip_raster_utm_geotiff(tmp_path):
    path = tmp_path / "band.tif"
    transform = from_origin(669000, 8795000, 30, 30)  # UTM 24S, around Aracaju
    data = np.arange(200 * 200, dtype="int16").reshape(1, 200, 200)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=200,
        width=200,
        count=1,
        dtype="int16",
        crs="EPSG:32724",
        transform=transform,
        nodata=-9999,
    ) as dst:
        dst.write(data)
    with rasterio.open(path) as src:
        lon_w, lat_s, lon_e, lat_n = rasterio.warp.transform_bounds(src.crs, "EPSG:4326", *src.bounds)
    inner = BBox(
        lon_w + (lon_e - lon_w) * 0.25,
        lat_s + (lat_n - lat_s) * 0.25,
        lon_w + (lon_e - lon_w) * 0.5,
        lat_s + (lat_n - lat_s) * 0.5,
    )
    clipped = clip.clip_raster(path, inner)
    assert 0 < clipped.shape[1] < 200 and 0 < clipped.shape[2] < 200
    assert clipped.rio.crs.to_epsg() == 32724


def test_read_hdf4_sinusoidal_tile(tmp_path):
    from pyhdf.SD import SD, SDC

    path = tmp_path / "tile.hdf"
    meta = "UpperLeftPointMtrs=(-4450000.0,-1110000.0)\nLowerRightMtrs=(-4445000.0,-1115000.0)\nXDim=20\nYDim=20"
    sd = SD(str(path), SDC.WRITE | SDC.CREATE)
    sds = sd.create("250m 16 days NDVI", SDC.INT16, (20, 20))
    values = np.full((20, 20), 5000, dtype="int16")
    values[0, 0] = -3000
    sds[:] = values
    sds.setfillvalue(-3000)
    sds.scale_factor = 0.0001
    sds.endaccess()
    sd.attr("StructMetadata.0").set(SDC.CHAR8, meta)
    sd.end()
    da = clip.read_sinusoidal_tile(path, "NDVI")
    assert da.shape == (20, 20) and np.isnan(da.values[0, 0]) and da.values[1, 1] == pytest.approx(0.5)
    assert clip.clip_tile(path, "NDVI", BBox(-41, -11, -40, -9)).rio.crs is not None
    with pytest.raises(InputError, match="does not overlap"):
        clip.clip_tile(path, "NDVI", BOX)


def test_hdf_grid_metadata_parser():
    text = "UpperLeftPointMtrs=(-5559752.598333,-1111950.519667)\nLowerRightMtrs=(-4447802.078667,-2223901.039333)\nXDim=4800\nYDim=4800"
    ul, _lr, x_dim, y_dim = clip._parse_grid_metadata(text)
    assert ul == (-5559752.598333, -1111950.519667) and (x_dim, y_dim) == (4800, 4800)
    with pytest.raises(InputError):
        clip._parse_grid_metadata("XDim=1")


def test_read_hdf5_sinusoidal_tile(tmp_path):
    import h5py

    path = tmp_path / "tile.h5"
    meta = "UpperLeftPointMtrs=(-4450000.0,-1110000.0)\nLowerRightMtrs=(-4445000.0,-1115000.0)\nXDim=20\nYDim=20"
    with h5py.File(path, "w") as h5:
        values = np.full((20, 20), 5000, dtype="int16")
        values[0, 0] = -3000
        dataset = h5.create_dataset("HDFEOS/GRIDS/G/Data Fields/500 m 16 days NDVI", data=values)
        dataset.attrs["_FillValue"] = np.int16(-3000)
        dataset.attrs["scale_factor"] = np.float64(0.0001)
        h5.create_dataset("HDFEOS INFORMATION/StructMetadata.0", data=meta.encode())
    da = clip.read_sinusoidal_tile(path, "500 m 16 days NDVI")
    assert da.shape == (20, 20) and np.isnan(da.values[0, 0]) and da.values[1, 1] == pytest.approx(0.5)
    assert da.rio.crs is not None and da.y[0] > da.y[-1]
    with pytest.raises(InputError, match="no dataset matching 'EVI'"):
        clip.read_sinusoidal_tile(path, "EVI")


def test_box_smaller_than_a_cell_uses_the_nearest_cell_and_warns():
    lat, lon = np.arange(-12, -8.9, 0.25), np.arange(-39, -35.9, 0.25)
    data = np.arange(lat.size * lon.size, dtype=float).reshape(lat.size, lon.size)
    da = xr.DataArray(data, dims=("lat", "lon"), coords={"lat": lat, "lon": lon})
    tiny = BBox(-37.08, -10.92, -37.06, -10.90)
    with pytest.warns(clip.NearestCellWarning, match="smaller than a grid cell"):
        clipped = clip.clip_latlon(da, tiny)
    assert clipped.shape == (1, 1) and float(clipped.lat[0]) == -11.0 and float(clipped.lon[0]) == -37.0


def test_box_outside_the_grid_is_still_an_error():
    axis = [0.0, 0.25, 0.5]
    da = xr.DataArray(np.ones((3, 3)), dims=("lat", "lon"), coords={"lat": axis, "lon": axis})
    with pytest.raises(InputError, match="does not overlap"):
        clip.clip_latlon(da, BBox(-37.08, -10.92, -37.06, -10.90))


def test_curvilinear_box_smaller_than_a_cell_uses_the_nearest_cell():
    lat, lon = np.meshgrid(np.arange(-12, -8.9, 0.5), np.arange(-39, -35.9, 0.5), indexing="ij")
    values = np.arange(lat.size, dtype=float).reshape(lat.shape)
    ds = xr.Dataset(
        {"sm": (("r", "c"), values)}, coords={"latitude": (("r", "c"), lat), "longitude": (("r", "c"), lon)}
    )
    with pytest.warns(clip.NearestCellWarning):
        da = clip.clip_curvilinear(ds, "sm", BBox(-37.4, -10.4, -37.3, -10.3))
    assert da.shape == (1, 1) and float(da.lat[0]) == -10.5 and float(da.lon[0]) == -37.5
    assert not np.isnan(da.values).any()
    with pytest.raises(InputError):
        clip.clip_curvilinear(ds, "sm", BBox(10, 10, 10.1, 10.1))


def _write_h5(path, names, scale=0.0001):
    import h5py

    meta = "UpperLeftPointMtrs=(-4450000.0,-1110000.0)\nLowerRightMtrs=(-4445000.0,-1115000.0)\nXDim=20\nYDim=20"
    with h5py.File(path, "w") as h5:
        for name in names:
            data = np.full((20, 20), 5000, dtype="int16")
            h5.create_dataset(f"HDFEOS/GRIDS/G/Data Fields/{name}", data=data).attrs["scale_factor"] = np.float64(scale)
        h5.create_dataset("HDFEOS INFORMATION/StructMetadata.0", data=meta.encode())


def test_ambiguous_variable_lists_candidates(tmp_path):
    path = tmp_path / "t.h5"
    _write_h5(path, ["500 m 16 days NDVI", "500 m 16 days NDVI quality", "500 m 16 days EVI"])
    with pytest.raises(InputError, match="matches several datasets.*NDVI quality"):
        clip.read_sinusoidal_tile(path, "500 m 16 days")
    assert clip.read_sinusoidal_tile(path, "EVI").name == "500 m 16 days EVI"
    assert clip.read_sinusoidal_tile(path, "500 m 16 days NDVI").name == "500 m 16 days NDVI"


def test_inverted_scale_factor_is_reported(tmp_path):
    path = tmp_path / "t.h5"
    _write_h5(path, ["500 m 16 days NDVI"], scale=10000.0)
    with pytest.raises(InputError, match="scale_factor looks inverted"):
        clip.read_sinusoidal_tile(path, "NDVI")
    _write_h5(path, ["500 m 16 days other"], scale=10000.0)
    assert clip.read_sinusoidal_tile(path, "other").shape == (20, 20)


def test_extent_margin_ignores_the_jump_between_rows_of_a_2d_grid():
    lat, lon = np.meshgrid(np.arange(0.0, 11.0), np.arange(0.0, 11.0), indexing="ij")
    ds = xr.Dataset(
        {"v": (("r", "c"), np.ones(lat.shape))}, coords={"latitude": (("r", "c"), lat), "longitude": (("r", "c"), lon)}
    )
    for box in (BBox(12.0, 4.0, 12.1, 4.1), BBox(4.0, 12.0, 4.1, 12.1)):
        with pytest.raises(InputError, match="no grid cell|does not overlap"):
            clip.clip_curvilinear(ds, "v", box)
    assert clip._within_extent(lon, 10.4, 10.6) and not clip._within_extent(lon, 10.6, 10.7)
