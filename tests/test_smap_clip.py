# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""SMAP-like files: 2-D latitude/longitude with undeclared -9999 holes (found in the first real run)."""

import warnings

import h5py
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from src.data import cli, clip, earthdata
from src.data.errors import InputError
from src.data.regions import PRESETS, BBox

SERGIPE = PRESETS["sergipe"]


class FakeGranule(dict):
    def __init__(self):
        super().__init__(umm={"TemporalExtent": {"RangeDateTime": {"BeginningDateTime": "2025-01-10T00:00:00Z"}}})


def ease_like_arrays(seed=0):
    """Latitude constant per row, longitude constant per column, with random -9999 holes in both arrays."""
    rows, cols = np.linspace(-8.0, -13.0, 51), np.linspace(-39.0, -36.0, 31)
    lat = np.repeat(rows[:, None], cols.size, axis=1).astype("float32")
    lon = np.repeat(cols[None, :], rows.size, axis=0).astype("float32")
    rng = np.random.default_rng(seed)
    lat[rng.random(lat.shape) < 0.3] = -9999
    lon[rng.random(lon.shape) < 0.3] = -9999
    lat[0, :] = -9999  # a row with no valid latitude at all
    return rows, cols, lat, lon


def write_smap_like(path, soil_moisture, lat, lon, half="AM"):
    """The PM group names its datasets with a _pm suffix (latitude_pm, soil_moisture_pm), as the real file does."""
    suffix = "_pm" if half == "PM" else ""
    with h5py.File(path, "w") as h5:
        group = h5.create_group(f"Soil_Moisture_Retrieval_Data_{half}")
        group.create_dataset(f"latitude{suffix}", data=lat)  # no _FillValue attribute, like the real product
        group.create_dataset(f"longitude{suffix}", data=lon)
        sm = group.create_dataset(f"soil_moisture{suffix}", data=soil_moisture)
        sm.attrs["_FillValue"] = np.float32(-9999)
        sm.attrs["valid_min"] = np.float32(0.02)
        sm.attrs["valid_max"] = np.float32(0.5)


def stub_download(tmp_path, monkeypatch, soil_moisture, lat, lon, half="AM"):
    path = tmp_path / "SMAP_L3_SM_P_E_20250110.h5"
    write_smap_like(path, soil_moisture, lat, lon, half)
    monkeypatch.setattr(earthdata, "require_login", lambda: None)
    monkeypatch.setattr(earthdata.earthaccess, "download", lambda granules, local_path=None: [path])


def fetch(tmp_path, monkeypatch, soil_moisture, lat, lon, bbox=SERGIPE, half="AM", **options):
    stub_download(tmp_path, monkeypatch, soil_moisture, lat, lon, half)
    suffix = "_pm" if half == "PM" else ""
    variable = f"Soil_Moisture_Retrieval_Data_{half}/soil_moisture{suffix}"
    return earthdata.fetch_grid(earthdata.SOURCES["smap"], [FakeGranule()], variable, bbox, tmp_path, **options)


def test_fill_values_in_coordinates_do_not_leak_into_the_clip(tmp_path, monkeypatch):
    rows, cols, lat, lon = ease_like_arrays()
    values = np.full(lat.shape, 0.3, dtype="float32")
    frame = fetch(tmp_path, monkeypatch, values, lat, lon)
    assert frame["lat"].between(SERGIPE.south, SERGIPE.north).all()
    assert frame["lon"].between(SERGIPE.west, SERGIPE.east).all()
    inside_rows = (rows >= SERGIPE.south) & (rows <= SERGIPE.north)
    inside_cols = (cols >= SERGIPE.west) & (cols <= SERGIPE.east)
    inside_rows[0] = False  # that row has no valid latitude
    assert len(frame) == inside_rows.sum() * inside_cols.sum() and len(frame) > 50


def test_cells_with_fill_or_outside_the_valid_range_are_dropped(tmp_path, monkeypatch):
    _rows, _cols, lat, lon = ease_like_arrays()
    values = np.full(lat.shape, 0.3, dtype="float32")
    values[::2, :] = -9999
    values[1::4, ::3] = 0.9  # above valid_max
    with pytest.warns(clip.OutOfRangeWarning):
        frame = fetch(tmp_path, monkeypatch, values, lat, lon)
    assert len(frame) > 0 and frame["soil_moisture"].between(0.02, 0.5).all()


def test_no_valid_values_in_the_box_is_a_clear_error(tmp_path, monkeypatch):
    _, _, lat, lon = ease_like_arrays()
    with pytest.raises(InputError, match="no valid '.*soil_moisture' values.*SMAP revisits every 2-3 days.*PM group"):
        fetch(tmp_path, monkeypatch, np.full(lat.shape, -9999, dtype="float32"), lat, lon)


def test_tiny_box_picks_the_nearest_real_cell_not_a_fill_cell(tmp_path, monkeypatch, recwarn):
    rows, cols, lat, lon = ease_like_arrays(seed=3)
    lat[:] = np.repeat(rows[:, None], cols.size, axis=1)  # full coordinates this time
    lon[:] = np.repeat(cols[None, :], rows.size, axis=0)
    tiny = BBox(-37.46, -10.56, -37.44, -10.54)  # between two rows and two columns
    frame = fetch(tmp_path, monkeypatch, np.full(lat.shape, 0.3, dtype="float32"), lat, lon, tiny)
    assert (
        len(frame) == 1 and abs(frame["lat"].iloc[0] + 10.55) <= 0.0501 and abs(frame["lon"].iloc[0] + 37.45) <= 0.0501
    )
    assert any(issubclass(w.category, clip.NearestCellWarning) for w in recwarn.list)


def test_skewed_grid_falls_back_to_cell_by_cell_clipping():
    """Coordinates that are not constant per row/column cannot be reduced to two axes."""
    r, c = np.meshgrid(np.arange(40.0), np.arange(40.0), indexing="ij")
    lat = -8.0 - 0.1 * r - 0.03 * c
    lon = -39.0 + 0.1 * c + 0.03 * r
    lat[3, 3] = lon[5, 5] = -9999
    ds = xr.Dataset(
        {"v": (("r", "c"), np.ones(lat.shape))},
        coords={"latitude": (("r", "c"), lat), "longitude": (("r", "c"), lon)},
    )
    da = clip.clip_curvilinear(ds, "v", SERGIPE)
    assert da.dims == ("r", "c") and np.isfinite(da.values).sum() > 50
    valid = np.isfinite(da.values)
    assert (da.lat.values[valid] >= SERGIPE.south).all() and (da.lat.values[valid] <= SERGIPE.north).all()
    assert (da.lon.values[valid] >= SERGIPE.west).all() and (da.lon.values[valid] <= SERGIPE.east).all()


def test_box_between_cells_of_a_nonuniform_axis_uses_the_local_cell_size():
    axis = np.array([0.0, 0.07, 0.14, 0.84, 1.54])  # EASE-Grid rows are not evenly spaced
    da = xr.DataArray(np.ones((5, 5)), dims=("lat", "lon"), coords={"lat": axis, "lon": axis})
    with pytest.warns(clip.NearestCellWarning):
        assert clip.clip_latlon(da, BBox(0.060, 0.060, 0.065, 0.065)).shape == (1, 1)
    with pytest.raises(Exception, match="does not overlap"):
        clip.clip_latlon(da, BBox(3.0, 3.0, 3.1, 3.1))


def values_with_some_above_valid_max():
    _, _, lat, lon = ease_like_arrays()
    values = np.full(lat.shape, 0.3, dtype="float32")
    values[1::4, :] = 0.6  # above valid_max (0.5)
    values[2::7, ::5] = -9999  # fill
    return values, lat, lon


def test_values_above_valid_max_are_dropped_with_a_count_by_default(tmp_path, monkeypatch):
    values, lat, lon = values_with_some_above_valid_max()
    with pytest.warns(
        clip.OutOfRangeWarning, match=r"dropped (\d+) values outside valid_min/valid_max \(0.02-0.5\)"
    ) as record:
        frame = fetch(tmp_path, monkeypatch, values, lat, lon)
    assert frame[["Soil_Moisture_Retrieval_Data_AM", "soil_moisture"][1]].max() <= 0.5
    kept = fetch_all(tmp_path, monkeypatch, values, lat, lon)
    dropped = int(str(record[0].message).split()[1])
    assert dropped == (kept["soil_moisture"] > 0.5).sum() > 0 and len(frame) == len(kept) - dropped


def fetch_all(tmp_path, monkeypatch, values, lat, lon):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        return fetch(tmp_path, monkeypatch, values, lat, lon, keep_out_of_range=True)


def test_keep_out_of_range_keeps_them_silently_but_fills_stay_masked(tmp_path, monkeypatch):
    values, lat, lon = values_with_some_above_valid_max()
    frame = fetch_all(tmp_path, monkeypatch, values, lat, lon)
    assert (frame["soil_moisture"] > 0.5).any() and (frame["soil_moisture"] > -1).all()


def test_cli_prints_the_warning_and_accepts_the_flag(tmp_path, monkeypatch, capsys):
    values, lat, lon = values_with_some_above_valid_max()
    stub_download(tmp_path, monkeypatch, values, lat, lon)
    monkeypatch.setattr(earthdata, "search", lambda *args: [FakeGranule()])
    variable = "Soil_Moisture_Retrieval_Data_AM/soil_moisture"
    argv = ["smap", "--variable", variable, "--start", "2025-01-10", "--end", "2025-01-10", "--raw-dir", str(tmp_path)]
    assert cli.main([*argv, "--out", str(tmp_path / "a.csv")]) == 0
    assert "warning: dropped " in capsys.readouterr().err
    assert cli.main([*argv, "--keep-out-of-range", "--out", str(tmp_path / "b.csv")]) == 0
    assert capsys.readouterr().err == ""
    default, kept = (pd.read_csv(tmp_path / name) for name in ("a.csv", "b.csv"))
    assert len(kept) > len(default) and default["soil_moisture"].max() <= 0.5 < kept["soil_moisture"].max()


def test_a_variable_without_valid_range_warns_about_nothing(tmp_path, monkeypatch):
    _, _, lat, lon = ease_like_arrays()
    stub_download(tmp_path, monkeypatch, np.full(lat.shape, 0.9, dtype="float32"), lat, lon)
    with h5py.File(tmp_path / "SMAP_L3_SM_P_E_20250110.h5", "a") as h5:
        for key in ("valid_min", "valid_max"):
            del h5["Soil_Moisture_Retrieval_Data_AM/soil_moisture"].attrs[key]
    variable = "Soil_Moisture_Retrieval_Data_AM/soil_moisture"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        frame = earthdata.fetch_grid(earthdata.SOURCES["smap"], [FakeGranule()], variable, SERGIPE, tmp_path)
    assert np.allclose(frame["soil_moisture"], 0.9)


def test_pm_group_with_suffixed_names(tmp_path, monkeypatch):
    _rows, _cols, lat, lon = ease_like_arrays(seed=5)
    values = np.full(lat.shape, 0.25, dtype="float32")
    values[::3, :] = -9999
    frame = fetch(tmp_path, monkeypatch, values, lat, lon, half="PM")
    assert len(frame) > 20 and list(frame.columns) == ["time", "lat", "lon", "soil_moisture_pm"]
    assert frame["lat"].between(SERGIPE.south, SERGIPE.north).all()
    assert frame["lon"].between(SERGIPE.west, SERGIPE.east).all()
    assert np.allclose(frame["soil_moisture_pm"], 0.25)
