# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""MODIS (HDF4) and VIIRS (HDF5) scaling and masking, with attributes shaped like the real files."""

import h5py
import numpy as np
import pytest
from pyhdf.SD import SD, SDC

from src.data import clip
from src.data.errors import InputError

META = "UpperLeftPointMtrs=(-4450000.0,-1110000.0)\nLowerRightMtrs=(-4445000.0,-1115000.0)\nXDim=20\nYDim=20"


def raw_ndvi(fill=-3000):
    raw = np.full((20, 20), 5000, dtype="int16")
    raw[0, 0] = fill
    raw[0, 1] = 12000  # beyond valid_range
    raw[0, 2] = -2500  # below valid_range
    return raw


def write_hdf4(path, name, raw, **attributes):
    sd = SD(str(path), SDC.WRITE | SDC.CREATE)
    sds = sd.create(name, SDC.INT16, raw.shape)
    sds[:] = raw
    for key, value in attributes.items():
        setattr(sds, key, value)
    sds.endaccess()
    sd.attr("StructMetadata.0").set(SDC.CHAR8, META)
    sd.end()


def write_hdf5(path, name, raw, **attributes):
    with h5py.File(path, "w") as h5:
        dataset = h5.create_dataset(f"HDFEOS/GRIDS/G/Data Fields/{name}", data=raw)
        for key, value in attributes.items():
            dataset.attrs[key] = value
        h5.create_dataset("HDFEOS INFORMATION/StructMetadata.0", data=META.encode())


def test_modis_hdf4_ndvi_divides_by_scale_factor(tmp_path):
    """MOD13Q1: scale_factor=10000, valid_range [-2000, 10000], fill -3000 (real attributes)."""
    path = tmp_path / "MOD13Q1.hdf"
    write_hdf4(
        path,
        "250m 16 days NDVI",
        raw_ndvi(),
        _FillValue=-3000,
        scale_factor=10000.0,
        add_offset=0.0,
        valid_range=[-2000, 10000],
    )
    da = clip.read_sinusoidal_tile(path, "NDVI")
    assert da.values[5, 5] == pytest.approx(0.5)
    assert np.isnan(da.values[0, :3]).all()  # fill, above and below valid_range
    assert np.nanmin(da.values) >= -0.2 and np.nanmax(da.values) <= 1.0


def test_modis_hdf4_with_a_small_scale_factor_multiplies(tmp_path):
    """MOD11 LST style: scale_factor 0.02 is a multiplier even in HDF4."""
    path = tmp_path / "MOD11.hdf"
    raw = np.full((20, 20), 15000, dtype="int16")
    write_hdf4(path, "LST_Day_1km", raw, _FillValue=0, scale_factor=0.02, add_offset=0.0)
    assert clip.read_sinusoidal_tile(path, "LST_Day").values[3, 3] == pytest.approx(300.0)


def test_hdf4_offset_is_subtracted_before_dividing():
    attrs = {"scale_factor": 100.0, "add_offset": 50.0}
    assert clip.unpack_values(np.array([250], dtype="int16"), attrs, hdf4=True)[0] == pytest.approx(2.0)


def test_viirs_hdf5_attributes_as_arrays(tmp_path):
    """VNP13A1: two fill values, 2-element valid_range, 1-element scale_factor and add_offset arrays."""
    path = tmp_path / "VNP13A1.h5"
    raw = raw_ndvi(fill=-15000)
    raw[1, 0] = -13000
    raw[1, 1] = 10001
    write_hdf5(
        path,
        "500 m 16 days NDVI",
        raw,
        _FillValue=np.array([-15000, -13000], dtype="int16"),
        valid_range=np.array([-10000, 10000], dtype="int16"),
        scale_factor=np.array([0.0001]),
        add_offset=np.array([0.0]),
    )
    da = clip.read_sinusoidal_tile(path, "NDVI")
    assert da.values[5, 5] == pytest.approx(0.5)
    assert np.isnan(da.values[0, 0]) and np.isnan(da.values[1, 0]) and np.isnan(da.values[1, 1])
    assert np.isnan(da.values[0, 1])  # 12000 is above this valid_range too
    assert da.rio.crs is not None


def test_numbers_normalizes_scalars_arrays_and_junk():
    attrs = {"a": np.array([2.5]), "b": [1, 2], "c": np.float32(3), "d": b"text", "E": np.array([-1, -2])}
    assert clip._numbers(attrs, "a").tolist() == [2.5]
    assert clip._numbers(attrs, "B").tolist() == [1.0, 2.0]
    assert clip._numbers(attrs, "c").tolist() == [3.0]
    assert clip._numbers(attrs, "d").size == 0 and clip._numbers(attrs, "missing").size == 0
    assert clip._numbers(attrs, "e").tolist() == [-1.0, -2.0]
    assert clip._scalar(attrs, "b") is None and clip._scalar(attrs, "a") == 2.5


def test_a_wrong_scale_is_still_reported(tmp_path):
    path = tmp_path / "bad.hdf"
    write_hdf4(path, "250m 16 days NDVI", raw_ndvi(), _FillValue=-3000, scale_factor=0.5)
    with pytest.raises(InputError, match="scale_factor looks inverted"):
        clip.read_sinusoidal_tile(path, "NDVI")


def test_offset_without_scale_factor_follows_each_format_convention():
    raw = np.array([100], dtype="int16")
    assert clip.unpack_values(raw, {"add_offset": 10.0}, hdf4=False)[0] == pytest.approx(110.0)  # CF adds
    assert clip.unpack_values(raw, {"add_offset": 10.0}, hdf4=True)[0] == pytest.approx(90.0)  # HDF4 subtracts
    assert clip.unpack_values(raw, {}, hdf4=True)[0] == 100.0


def test_hdf5_file_with_offset_only(tmp_path):
    path = tmp_path / "offset.h5"
    write_hdf5(path, "temperature", np.full((20, 20), 100, dtype="int16"), add_offset=np.array([10.0]))
    assert clip.read_sinusoidal_tile(path, "temperature").values[2, 2] == pytest.approx(110.0)
