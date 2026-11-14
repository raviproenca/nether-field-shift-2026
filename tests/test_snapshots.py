# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Snapshot generator tests with fakes: grid, sampling, land mask, failing source, size limit, format and writing."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from src.data import snapshot_sources as sources
from src.data import snapshots
from src.data.errors import InputError, SizeLimitError
from src.data.regions import PRESETS, BBox
from src.data.sampling import Layer, Point, grid_points, sample_layer
from src.data.snapshot_model import Region, SourceData, Variable
from src.data.snapshot_output import build_files, check_size, kept_times, write_files

SCHEMAS = Path(__file__).resolve().parents[1] / "docs" / "data-format"
NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
TWO_REGIONS = [
    Region("sergipe", "Sergipe", PRESETS["sergipe"], 0.25, "SE"),
    Region("nordeste", "Northeast", PRESETS["nordeste"], 2.0, "NE"),
]


def validator(name: str) -> Draft202012Validator:
    resources = {}
    for path in SCHEMAS.glob("*.schema.json"):
        schema = json.loads(path.read_text())
        resources[schema["$id"]] = Resource.from_contents(schema)
    registry = Registry().with_resources(resources.items())
    return Draft202012Validator(
        json.loads((SCHEMAS / f"{name}.schema.json").read_text()), registry=registry, format_checker=FormatChecker()
    )


def fake_data(points, times=("2026-11-01", "2026-11-02"), names=("A", "B"), land=None):
    """Values that depend on the point row, so a mix-up between points shows. Non-land points are all NaN."""
    values = np.zeros((len(points), len(times), len(names)))
    for row in range(len(points)):
        values[row] = row + np.arange(len(times))[:, None] * 0.1234567 + np.arange(len(names))
    if land is not None:
        values[[i for i, p in enumerate(points) if p.id not in land]] = np.nan
    return SourceData([Variable(n, f"{n} long", "u", 2) for n in names], list(times), values, times[-1])


def fake_fetcher(land=None, **kwargs):
    return lambda ctx: fake_data(ctx.points, land=land, **kwargs)


def run(tmp_path, names, fetchers, regions=TWO_REGIONS, max_bytes=5 * 1024 * 1024):
    ctx_args = {"days": 2, "today": date(2026, 11, 14), "raw_dir": tmp_path / "raw", "cache_dir": tmp_path / "cache"}
    infos = {n: sources.INFOS["power"] for n in names}
    infos = {n: sources.INFOS.get(n, sources.INFOS["power"]) for n in names}
    out = tmp_path / "out"
    sizes = snapshots.generate(
        regions, names, ctx_args, out, max_bytes, fetchers=fetchers, infos=infos, log=lambda m: None, now=lambda: NOW
    )
    return out, sizes


def test_grid_points_are_multiples_of_the_spacing_inside_the_box():
    points = grid_points(PRESETS["sergipe"], 0.25, "SE")
    assert [p.id for p in points[:2]] == ["SE001", "SE002"] and len({p.id for p in points}) == len(points)
    bbox = PRESETS["sergipe"]
    assert all(bbox.west <= p.lon <= bbox.east and bbox.south <= p.lat <= bbox.north for p in points)
    assert all(abs(p.lat / 0.25 - round(p.lat / 0.25)) < 1e-6 and p.half == 0.125 for p in points)
    assert points[0].lat > points[-1].lat and len(points) == 64  # 8 latitudes x 8 longitudes


def test_grid_points_reject_bad_spacing_and_empty_grids():
    with pytest.raises(InputError, match="positive"):
        grid_points(PRESETS["sergipe"], 0, "SE")
    with pytest.raises(InputError, match="no grid point"):
        grid_points(BBox(-37.6, -10.6, -37.4, -10.4), 1.0, "XX")


def test_sample_layer_means_the_valid_cells_in_the_box():
    lat, lon = np.array([-10.5, -10.25, -10.0]), np.array([-37.5, -37.25, -37.0])
    values = np.arange(18, dtype="float64").reshape(2, 3, 3)
    values[0, 0, 0] = np.nan
    layer = Layer(lat, lon, values)
    big = sample_layer(layer, [Point("a", -10.25, -37.25, 0.3)])
    assert big[1, 0] == pytest.approx(values[1].mean())
    assert big[0, 0] == pytest.approx(np.nanmean(values[0]))  # the NaN cell is skipped


def test_sample_layer_uses_the_nearest_cell_for_a_tiny_box_and_nan_outside_or_empty():
    lat, lon = np.array([-10.5, -10.0]), np.array([-37.5, -37.0])
    values = np.array([[[1.0, 2.0], [np.nan, np.nan]]])
    layer = Layer(lat, lon, values)
    result = sample_layer(
        layer, [Point("near", -10.45, -37.45, 0.01), Point("far", 0.0, 0.0, 0.1), Point("empty", -10.0, -37.0, 0.01)]
    )
    assert result[0, 0] == 1.0 and np.isnan(result[0, 1]) and np.isnan(result[0, 2])


def test_domain_covers_every_region_with_a_margin():
    domain = snapshots.domain_of(TWO_REGIONS)
    nordeste = PRESETS["nordeste"]
    assert domain.west < nordeste.west and domain.north > nordeste.north and domain.south < nordeste.south


def test_generate_writes_the_documented_files_and_they_match_the_schemas(tmp_path):
    out, sizes = run(tmp_path, ["gldas", "power"], {"gldas": fake_fetcher(), "power": fake_fetcher()})
    assert set(sizes) == {
        "index.json", "sergipe/points.geojson", "sergipe/gldas.json", "sergipe/power.json",
        "nordeste/points.geojson", "nordeste/gldas.json", "nordeste/power.json",
    }  # fmt: skip
    index = json.loads((out / "index.json").read_text())
    validator("index").validate(index)
    assert [r["id"] for r in index["regions"]] == ["sergipe", "nordeste"] and index[
        "generated_at"
    ] == "2026-11-14T12:00:00Z"
    for region in index["regions"]:
        validator("points").validate(json.loads((out / region["points_file"]).read_text()))
    for source in index["sources"]:
        for path in source["files"].values():
            validator("series").validate(json.loads((out / path).read_text()))


def test_series_values_follow_the_points_and_are_rounded(tmp_path):
    out, _ = run(tmp_path, ["power"], {"power": fake_fetcher()}, regions=TWO_REGIONS[:1])
    series = json.loads((out / "sergipe/power.json").read_text())["points"]
    points = json.loads((out / "sergipe/points.geojson").read_text())["features"]
    assert list(series) == [f["id"] for f in points]
    first = series["SE001"]
    assert first[0] == {"time": "2026-11-01", "values": {"A": 0.0, "B": 1.0}}
    assert first[1]["values"]["A"] == 0.12  # 0.1234567 rounded to 2 decimals
    assert series["SE003"][0]["values"]["A"] == 2.0


def test_a_source_that_fails_is_reported_and_the_rest_still_written(tmp_path):
    def broken(ctx):
        raise RuntimeError("boom")

    out, _ = run(tmp_path, ["power", "imerg"], {"power": broken, "imerg": fake_fetcher()}, regions=TWO_REGIONS[:1])
    index = json.loads((out / "index.json").read_text())
    validator("index").validate(index)
    by_id = {s["id"]: s for s in index["sources"]}
    assert by_id["power"]["status"] == "failed" and by_id["power"]["files"] == {} and by_id["power"]["period"] is None
    assert by_id["imerg"]["status"] == "ok" and (out / "sergipe/imerg.json").is_file()
    assert not (out / "sergipe/power.json").exists()
    assert [w["code"] for w in index["warnings"]] == ["source_failed"] and "boom" in index["warnings"][0]["message"]


def test_partial_failures_inside_a_source_become_warnings(tmp_path):
    def partial(ctx):
        data = fake_data(ctx.points)
        data.warnings = ["IMERG failed on 1 date(s): 2026-11-03: HTTP 503"]
        return data

    out, _ = run(tmp_path, ["imerg"], {"imerg": partial}, regions=TWO_REGIONS[:1])
    warning = json.loads((out / "index.json").read_text())["warnings"][0]
    assert warning == {
        "source": "imerg",
        "code": "partial_data",
        "message": "IMERG failed on 1 date(s): 2026-11-03: HTTP 503",
    }


def test_land_mask_drops_open_water_points_from_every_source(tmp_path):
    land = {"SE001", "SE002", "NE001"}
    seen = {}

    def power(ctx):
        seen["ids"] = [p.id for p in ctx.points]
        return fake_data(ctx.points)

    out, _ = run(tmp_path, ["gldas", "power"], {"gldas": fake_fetcher(land=land), "power": power})
    assert seen["ids"] == ["SE001", "SE002", "NE001"]
    for region, expected in (("sergipe", {"SE001", "SE002"}), ("nordeste", {"NE001"})):
        features = json.loads((out / region / "points.geojson").read_text())["features"]
        assert {f["id"] for f in features} == expected
        assert set(json.loads((out / region / "gldas.json").read_text())["points"]) == expected
    index = json.loads((out / "index.json").read_text())
    assert [r["points"] for r in index["regions"]] == [2, 1]


def test_without_the_land_source_every_grid_point_is_kept(tmp_path):
    def failing(ctx):
        raise RuntimeError("no gldas today")

    out, _ = run(tmp_path, ["gldas", "power"], {"gldas": failing, "power": fake_fetcher()}, regions=TWO_REGIONS[:1])
    index = json.loads((out / "index.json").read_text())
    assert index["regions"][0]["points"] == 64 and {s["id"]: s["status"] for s in index["sources"]} == {
        "gldas": "failed", "power": "ok",
    }  # fmt: skip


def test_dates_with_no_valid_value_anywhere_are_not_published():
    points = grid_points(PRESETS["sergipe"], 0.5, "SE")
    data = fake_data(points, times=("2026-11-01", "2026-11-02", "2026-11-03"))
    data.values[:, 1, :] = np.nan
    assert kept_times(data) == [0, 2]


def test_size_limit_fails_with_a_clear_message_and_writes_nothing(tmp_path):
    with pytest.raises(SizeLimitError, match=r"above the limit of 0\.00 MB.*largest files"):
        run(tmp_path, ["power"], {"power": fake_fetcher()}, max_bytes=1000)
    assert not (tmp_path / "out").exists()


def test_check_size_returns_the_total_when_under_the_limit():
    assert check_size({"a": b"x" * 10, "b": b"y" * 5}, limit=15) == 15
    with pytest.raises(SizeLimitError):
        check_size({"a": b"x" * 16}, limit=15)


def test_write_files_replaces_generated_files_and_keeps_everything_else(tmp_path):
    (tmp_path / "sergipe").mkdir()
    (tmp_path / "sergipe" / "old.json").write_text("{}")
    (tmp_path / "index.json").write_text("{}")
    (tmp_path / "keep.txt").write_text("mine")
    write_files(tmp_path, {"index.json": b"{}", "sergipe/new.json": b"[]"})
    assert not (tmp_path / "sergipe" / "old.json").exists()
    assert (tmp_path / "sergipe" / "new.json").read_bytes() == b"[]" and (tmp_path / "keep.txt").read_text() == "mine"


def test_build_files_keeps_unicode_units_readable():
    points = grid_points(PRESETS["sergipe"], 1.0, "SE")
    data = fake_data(points)
    data.variables = [Variable("T2M", "Air temperature", "°C", 1), Variable("B", "b", "m³/m³", 3)]
    files = build_files(
        NOW, TWO_REGIONS[:1], {"sergipe": points}, {"power": sources.INFOS["power"]}, {"power": data}, points, {}
    )
    assert "°C".encode() in files["sergipe/power.json"] and b"\\u00b0" not in files["sergipe/power.json"]


def test_cli_rejects_unknown_region_source_and_spacing(capsys):
    assert snapshots.main(["--regions", "mars"]) == 2
    assert snapshots.main(["--sources", "nope"]) == 2
    assert snapshots.main(["--spacing", "sergipe=abc"]) == 2
    assert snapshots.main(["--regions", "sergipe", "--spacing", "nordeste=2"]) == 2
    assert "unknown region" in capsys.readouterr().err


def test_power_cell_is_the_merra2_cell_center():
    assert sources._power_cell(-10.91, -37.07) == (-11.0, -36.875)
    assert sources._power_cell(-10.6, -37.2) == sources._power_cell(-10.4, -37.4) == (-10.5, -37.5)


def test_fetch_power_shares_one_call_between_points_of_the_same_cell(tmp_path, monkeypatch):
    calls = []

    def fake_fetch_point(lat, lon, dates, variables, cache_dir=None, **_):
        calls.append((lat, lon))
        days = pd.date_range(dates.start, dates.end)
        frame = pd.DataFrame({v: np.arange(len(days), dtype=float) + lat for v in variables}, index=days)
        frame.iloc[-1] = np.nan
        return frame

    monkeypatch.setattr(sources.power, "fetch_point", fake_fetch_point)
    points = grid_points(PRESETS["sergipe"], 0.25, "SE")
    ctx = sources.Context(
        points, snapshots.domain_of(TWO_REGIONS[:1]), 3, date(2026, 11, 14), tmp_path, tmp_path, log=print
    )
    data = sources.fetch_power(ctx)
    assert len(calls) == len(set(calls)) < len(points) and data.values.shape == (len(points), 3, 4)
    assert data.times == ["2026-11-08", "2026-11-09", "2026-11-10"] and np.isnan(data.values[:, -1]).all()


def test_fetch_power_fails_cleanly_when_every_cell_fails(tmp_path, monkeypatch):
    from src.data.errors import RemoteDataError

    def always_down(*args, **kwargs):
        raise RemoteDataError("POWER API unavailable")

    monkeypatch.setattr(sources.power, "fetch_point", always_down)
    ctx = sources.Context(
        grid_points(PRESETS["sergipe"], 1.0, "SE"), PRESETS["sergipe"], 3, date(2026, 11, 14), tmp_path, tmp_path
    )
    with pytest.raises(RemoteDataError, match="failed for every cell"):
        sources.fetch_power(ctx)


def test_ease_grid_axes_match_the_known_smap_geometry():
    lat, lon = sources.ease2_axes()
    assert lat.shape == (1624,) and lon.shape == (3856,) and lat[0] > lat[-1] and lon[0] < lon[-1]
    assert lat[0] == pytest.approx(84.66, abs=0.05) and lon[0] == pytest.approx(-179.96, abs=0.02)
    assert (lat >= -7.0).sum() > 0 and abs(lat[np.abs(lat + 10.9).argmin()] + 10.9) < 0.05


def test_choose_composites_takes_one_per_16_days_within_the_span():
    days = [date(2026, 10, 24) - pd.Timedelta(days=8 * k) for k in range(10)]
    chosen = sources.choose_composites([d for d in days], span=60)
    assert chosen == [date(2026, 9, 6), date(2026, 9, 22), date(2026, 10, 8), date(2026, 10, 24)]


def test_tile_sums_average_the_pixels_inside_each_box():
    x, y = np.arange(0.0, 10000.0, 500.0) + 250, np.arange(9750.0, -250.0, -500.0)
    values = np.tile(np.arange(20, dtype=float), (20, 1))  # value = column index
    values[0:2, 0:2] = np.nan
    tile = xr.DataArray(values, dims=("y", "x"), coords={"y": y, "x": x})
    px, py = np.array([2250.0, 5000000.0]), np.array([5250.0, 5000000.0])
    sums, counts = sources.tile_sums(tile, px, py, np.array([900.0, 900.0]), np.array([900.0, 900.0]))
    assert counts[0] == 9 and sums[0] / counts[0] == pytest.approx(4.0)  # columns 3..5 around x=2250
    assert counts[1] == 0 and sums[1] == 0  # a point that is not in this tile


def test_sinusoidal_boxes_scale_the_half_width_with_the_latitude():
    points = [Point("a", -10.0, -37.0, 0.5), Point("b", -60.0, -37.0, 0.5)]
    px, py, half_x, half_y = sources.sinusoidal_boxes(points)
    assert half_y[0] == pytest.approx(half_y[1]) and half_x[1] == pytest.approx(half_y[1] * 0.5, rel=1e-3)
    assert py[0] == pytest.approx(-10.0 * 111194.93, rel=1e-3) and px[0] < 0
