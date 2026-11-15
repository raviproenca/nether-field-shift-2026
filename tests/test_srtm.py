# AI-assisted: generated with Antigravity and Claude Code, reviewed by dudxyz (adapted for the snapshot generator)
# Based on work by @dudxyz in feat/dudxyz-srtm-openmeteo-pilots
"""Tests for NASA NASADEM / SRTM terrain clipping and slope calculation (no network)."""

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
import rasterio
import xarray as xr
from pystac import Asset, Item
from rasterio.transform import from_origin

from src.data import srtm
from src.data.errors import InputError, RemoteDataError
from src.data.regions import BBox, point_to_bbox


def _write_dem_tif(path: Path, west: float, north: float, data: np.ndarray, step: float = 0.0002777778) -> Path:
    transform = from_origin(west, north, step, step)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data.astype("float32"), 1)
    return path


class _FakeSearch:
    def __init__(self, items, error=None):
        self._items = items
        self._error = error

    def items(self):
        if self._error:
            raise self._error
        return iter(self._items)


class _FakeClient:
    def __init__(self, items=(), error=None):
        self._items = list(items)
        self._error = error
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeSearch(self._items, self._error)


def _make_nasadem_item(item_id: str, href: str) -> Item:
    item = Item(
        id=item_id,
        geometry=None,
        bbox=None,
        datetime=datetime(2000, 2, 20, 0, 0, tzinfo=UTC),
        properties={},
    )
    item.add_asset("elevation", Asset(href=href))
    return item


def test_search_tiles_queries_nasadem_without_datetime_filter():
    box = point_to_bbox(-10.685, -37.425, 2.0)
    client = _FakeClient([_make_nasadem_item("NASADEM_HGT_s11w038", "/tmp/a.tif")])
    tiles = srtm.search_tiles(client, box)
    assert [t.id for t in tiles] == ["NASADEM_HGT_s11w038"]
    assert client.calls[0]["collections"] == ["nasadem"]
    assert "datetime" not in client.calls[0]


def test_search_tiles_raises_on_empty_or_error():
    box = point_to_bbox(-10.685, -37.425, 2.0)
    with pytest.raises(RemoteDataError, match="no nasadem tiles"):
        srtm.search_tiles(_FakeClient([]), box)
    with pytest.raises(RemoteDataError, match="ConnectionError"):
        srtm.search_tiles(_FakeClient(error=ConnectionError("down")), box)


def test_size_guard_rejects_huge_box():
    with pytest.raises(InputError, match="million pixels at 30 m"):
        srtm.check_size(BBox(-48.0, -18.0, -34.0, -1.0), max_pixels=100_000)


def test_compute_slope_of_a_known_plane():
    # Create a 5x5 grid with step ~30 m (~0.00027 deg) and linear ramp rising 3 m per pixel east (~10% slope)
    step_deg = 30.0 / (111.32 * 1000.0)
    x = np.linspace(-37.43, -37.43 + 4 * step_deg, 5)
    y = np.linspace(-10.68, -10.68 - 4 * step_deg, 5)
    elev_vals = np.repeat(np.arange(5, dtype="float32")[None, :] * 3.0 + 100.0, 5, axis=0)
    da = xr.DataArray(elev_vals, dims=("y", "x"), coords={"y": y, "x": x}).rio.write_crs("EPSG:4326")
    slope_deg, slope_pct = srtm.compute_slope(da)
    assert slope_pct.shape == (5, 5)
    assert float(slope_pct.mean()) == pytest.approx(10.18, abs=0.5)
    assert float(slope_deg.mean()) == pytest.approx(5.81, abs=0.4)
    summary = srtm.summarize_terrain(da)
    assert summary["elevation_min_m"] == pytest.approx(100.0)
    assert summary["elevation_max_m"] == pytest.approx(112.0)
    assert "erosion_risk" not in summary and "slope_class" not in summary


def test_compute_slope_handles_single_pixel_raster():
    da = xr.DataArray([[150.0]], dims=("y", "x"), coords={"y": [-10.6], "x": [-37.4]}).rio.write_crs("EPSG:4326")
    slope_deg, slope_pct = srtm.compute_slope(da)
    assert float(slope_deg.values[0, 0]) == 0.0
    assert float(slope_pct.values[0, 0]) == 0.0


def test_write_rasters_merges_tiles_and_builds_summary(tmp_path):
    west_tile = _write_dem_tif(tmp_path / "west.tif", -37.05, -10.65, np.full((60, 60), 120.0), step=0.001)
    east_tile = _write_dem_tif(tmp_path / "east.tif", -37.00, -10.65, np.full((60, 60), 135.0), step=0.001)
    client = _FakeClient(
        [
            _make_nasadem_item("NASADEM_HGT_s11w038", str(west_tile)),
            _make_nasadem_item("NASADEM_HGT_s11w037", str(east_tile)),
        ]
    )
    box = BBox(-37.02, -10.68, -36.98, -10.66)
    out_dir = tmp_path / "srtm_out"
    written, summary = srtm.write_rasters(box, out_dir, variable="all", client=client)
    assert len(written) == 3
    assert [p.name for p in written] == ["srtm_elevation.tif", "srtm_slope_deg.tif", "srtm_slope_pct.tif"]
    assert summary["elevation_min_m"] == pytest.approx(120.0)
    assert summary["elevation_max_m"] == pytest.approx(135.0)
    assert summary["nasa"] is True


def test_cli_srtm_writes_json_summary(tmp_path, monkeypatch, capsys):
    tif = _write_dem_tif(tmp_path / "dem.tif", -37.45, -10.65, np.full((40, 40), 180.0), step=0.001)
    client = _FakeClient([_make_nasadem_item("NASADEM_HGT_s11w038", str(tif))])
    monkeypatch.setattr(planetary, "open_client", lambda: client)
    out_json = tmp_path / "terrain.json"
    code = cli.main(["srtm", "--point", "-10.67,-37.43", "--radius-km", "1", "--out", str(out_json)])
    assert code == 0
    saved = json.loads(out_json.read_text(encoding="utf-8"))
    assert saved["source"] == "srtm" and saved["elevation_mean_m"] == pytest.approx(180.0)
    assert "NASADEM summary" in capsys.readouterr().out
    assert not {"slope_class", "erosion_risk", "contour_planting_recommended"} & set(summary)  # no product rules
