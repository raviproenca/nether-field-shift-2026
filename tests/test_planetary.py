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
from src.data.paths import safe_filename
from src.data.regions import PRESETS, BBox, point_to_bbox

DATES = parse_range("2025-01-01", "2025-01-31")
BOX = PRESETS["sergipe"]


def make_item(item_id, href="/nonexistent.tif", day=4, **asset_fields):
    item = Item(
        id=item_id,
        geometry=None,
        bbox=None,
        datetime=datetime(2025, 1, day, 12, 0, tzinfo=UTC),
        properties={},
    )
    item.add_asset("B04", Asset(href=href, extra_fields=asset_fields))
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
    with pytest.raises(
        RemoteDataError, match="Planetary Computer search for sentinel-2-l2a failed: ConnectionError: down"
    ):
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


def test_size_guard_blocks_a_state_sized_box_before_reading():
    item = make_item("big", gsd=10, **{"proj:shape": [10980, 10980]})
    assert planetary.window_pixels(item, "B04", BOX) == 10980 * 10980  # capped by the tile size
    with pytest.raises(InputError, match="million pixels per band.*--point/--radius-km.*--max-pixels"):
        planetary.fetch_clips([item], "B04", BOX, "unused")


def test_size_guard_allows_small_boxes_and_can_be_raised():
    item = make_item("ok", gsd=10)
    small = point_to_bbox(-10.91, -37.07, 2)
    assert planetary.window_pixels(item, "B04", small) < 1_000_000
    planetary.check_size([item], "B04", small, planetary.DEFAULT_MAX_PIXELS)
    with pytest.raises(InputError):
        planetary.check_size([item], "B04", small, 1000)
    planetary.check_size([item], "B04", BOX, 10**10)


def test_size_guard_is_skipped_when_resolution_is_unknown():
    assert planetary.window_pixels(make_item("x"), "B04", BOX) is None


def test_size_guard_uses_proj_transform_when_gsd_is_missing():
    coarse = make_item("t", **{"proj:transform": [20.0, 0.0, 0.0, 0.0, -20.0, 0.0]})
    fine = make_item("g", gsd=10)
    small = point_to_bbox(-10.91, -37.07, 2)
    assert planetary.window_pixels(coarse, "B04", small) < planetary.window_pixels(fine, "B04", small)


def test_unsafe_names_are_sanitized_for_files():
    assert safe_filename("../S2A/x y:B04") == ".._S2A_x_y_B04"
    assert safe_filename("250m 16 days NDVI") == "250m_16_days_NDVI"


def test_cli_max_pixels_flag_reaches_the_guard(monkeypatch, capsys):
    monkeypatch.setattr(planetary, "open_client", lambda: FakeClient([make_item("big", gsd=10)]))
    argv = ["planetary", "--variable", "B04", "--start", "2025-01-01", "--end", "2025-01-31"]
    assert cli.main(argv) == 2
    assert "million pixels per band" in capsys.readouterr().err


def make_range_item(item_id, start_day):
    return Item(
        id=item_id,
        geometry=None,
        bbox=None,
        datetime=None,
        properties={
            "start_datetime": f"2025-01-{start_day:02d}T00:00:00Z",
            "end_datetime": f"2025-01-{start_day + 1:02d}T00:00:00Z",
        },
    )


def test_items_without_datetime_sort_by_start_datetime_and_do_not_crash():
    items = [make_item("dated", day=15), make_range_item("late", 20), make_range_item("early", 3)]
    ordered = planetary.search(FakeClient(items), BOX, DATES, "sentinel-2-l2a", 20)
    assert [i.id for i in ordered] == ["early", "dated", "late"]
    newest = planetary.latest_item_datetime(FakeClient([make_range_item("only", 9)]), BOX, "sentinel-2-l2a")
    assert newest.day == 9


def test_item_time_falls_back_to_the_oldest_time():
    bare = Item(id="bare", geometry=None, bbox=None, datetime=datetime(2025, 1, 1, tzinfo=UTC), properties={})
    bare.datetime = None
    assert planetary.item_time(bare) < datetime(2000, 1, 1, tzinfo=UTC)
