# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Planetary Computer tests with fakes (no network), plus one real call marked network."""

from datetime import UTC, datetime

import numpy as np
import pytest
import rasterio
from pystac import Asset, Item
from rasterio.transform import from_origin

from src.data import cli, planetary
from src.data.dates import parse_range
from src.data.errors import InputError, RemoteDataError
from src.data.regions import PRESETS, BBox

DATES = parse_range("2025-01-01", "2025-01-31")
BOX = PRESETS["sergipe"]


def make_item(item_id, href="/nonexistent.tif", day=4):
    item = Item(
        id=item_id,
        geometry=None,
        bbox=None,
        datetime=datetime(2025, 1, day, 12, 0, tzinfo=UTC),
        properties={},
    )
    item.add_asset("B04", Asset(href=href))
    return item


class FakeSearch:
    def __init__(self, items, error=None):
        self._items, self._error = items, error

    def items(self):
        if self._error:
            raise self._error
        return iter(self._items)


class FakeClient:
    def __init__(self, items=(), error=None):
        self.items, self.error, self.calls = list(items), error, []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return FakeSearch(self.items, self.error)


def test_build_search_has_box_period_and_cloud_query():
    query = planetary.build_search(BOX, DATES, "sentinel-2-l2a", 20)
    assert query == {
        "collections": ["sentinel-2-l2a"],
        "bbox": [-38.25, -11.57, -36.39, -9.51],
        "datetime": "2025-01-01T00:00:00Z/2025-01-31T23:59:59Z",
        "query": {"eo:cloud_cover": {"lt": 20}},
    }


@pytest.mark.parametrize("cloud", [0, -5, 101])
def test_invalid_cloud_limit(cloud):
    with pytest.raises(InputError):
        planetary.build_search(BOX, DATES, "sentinel-2-l2a", cloud)


def test_search_passes_query_and_sorts_by_date():
    client = FakeClient([make_item("late", day=20), make_item("early", day=2)])
    items = planetary.search(client, BOX, DATES, "sentinel-2-l2a", 15)
    assert [i.id for i in items] == ["early", "late"]
    assert client.calls[0]["query"] == {"eo:cloud_cover": {"lt": 15}}


def test_empty_result_is_a_clear_error():
    with pytest.raises(RemoteDataError, match="no sentinel-2-l2a items.*cloud < 20%"):
        planetary.search(FakeClient([]), BOX, DATES, "sentinel-2-l2a", 20)


def test_api_failure_is_a_clear_error():
    with pytest.raises(RemoteDataError, match="search failed"):
        planetary.search(FakeClient(error=ConnectionError("down")), BOX, DATES, "sentinel-2-l2a", 20)


def test_latest_item_asks_for_newest_first():
    client = FakeClient([make_item("new", day=28)])
    assert planetary.latest_item_datetime(client, BOX, "sentinel-2-l2a").day == 28
    call = client.calls[0]
    assert call["sortby"] == [{"field": "datetime", "direction": "desc"}] and call["max_items"] == 1
    with pytest.raises(RemoteDataError):
        planetary.latest_item_datetime(FakeClient([]), BOX, "sentinel-2-l2a")


def test_missing_asset_lists_available_ones():
    with pytest.raises(InputError, match="'B99' not found.*B04"):
        planetary.asset_href(make_item("x"), "B99")
    with pytest.raises(InputError, match="not found"):
        planetary.fetch_clips([make_item("x")], "B99", BOX, "unused")


def test_fetch_clips_cuts_window_in_item_crs(tmp_path):
    source = tmp_path / "B04.tif"
    transform = from_origin(669000, 8795000, 10, 10)  # UTM 24S
    with rasterio.open(
        source,
        "w",
        driver="GTiff",
        height=400,
        width=400,
        count=1,
        dtype="uint16",
        crs="EPSG:32724",
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(np.full((1, 400, 400), 1000, dtype="uint16"))
        west, south, east, north = rasterio.warp.transform_bounds(dst.crs, "EPSG:4326", *dst.bounds)
    inner = BBox(
        west + (east - west) * 0.4,
        south + (north - south) * 0.4,
        west + (east - west) * 0.6,
        south + (north - south) * 0.6,
    )
    written = planetary.fetch_clips([make_item("scene", str(source))], "B04", inner, tmp_path / "out")
    assert [p.name for p in written] == ["scene_B04.tif"]
    with rasterio.open(written[0]) as clipped:
        assert 0 < clipped.width < 400 and clipped.crs.to_epsg() == 32724


def test_fetch_clips_without_overlap(tmp_path):
    source = tmp_path / "B04.tif"
    with rasterio.open(
        source,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="uint16",
        crs="EPSG:32724",
        transform=from_origin(669000, 8795000, 10, 10),
    ) as dst:
        dst.write(np.ones((1, 10, 10), dtype="uint16"))
    with pytest.raises(InputError, match="no item has data"):
        planetary.fetch_clips([make_item("scene", str(source))], "B04", BBox(0, 0, 1, 1), tmp_path / "out")


def test_cli_search_only(monkeypatch, capsys):
    client = FakeClient([make_item("a"), make_item("b", day=9)])
    monkeypatch.setattr(planetary, "open_client", lambda: client)
    assert cli.main(["planetary", "--search-only", "--start", "2025-01-01", "--end", "2025-01-31"]) == 0
    assert "2 items with cloud < 20%" in capsys.readouterr().out


def test_cli_needs_variable_and_reports_api_errors(monkeypatch, capsys):
    monkeypatch.setattr(planetary, "open_client", lambda: FakeClient([make_item("a")]))
    assert cli.main(["planetary", "--start", "2025-01-01", "--end", "2025-01-31"]) == 2
    assert "--variable is required" in capsys.readouterr().err
    monkeypatch.setattr(planetary, "open_client", lambda: FakeClient(error=TimeoutError("slow")))
    assert cli.main(["planetary", "--search-only", "--start", "2025-01-01", "--end", "2025-01-31"]) == 1
    assert "error:" in capsys.readouterr().err


@pytest.mark.network
def test_real_planetary_search_sergipe():
    client = planetary.open_client()
    items = planetary.search(client, BOX, DATES, "sentinel-2-l2a", 20)
    assert len(items) > 0 and "B04" in items[0].assets
    assert planetary.latest_item_datetime(client, BOX, "sentinel-2-l2a").year >= 2025
