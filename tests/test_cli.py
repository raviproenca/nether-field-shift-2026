# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""CLI and Earthdata plumbing tests with fakes: no network, no login."""

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from src.data import cli, earthdata, planetary, power
from src.data.regions import PRESETS


class FakeGranule(dict):
    def __init__(self, begin):
        super().__init__(umm={"TemporalExtent": {"RangeDateTime": {"BeginningDateTime": begin}}})


def test_negative_values_are_attached_to_their_flags():
    argv = ["power", "--point", "-10.9,-37.0", "--radius-km", "2", "--bbox", "-38,-11,-36,-9"]
    assert cli.attach_negative_values(argv) == [
        "power",
        "--point=-10.9,-37.0",
        "--radius-km",
        "2",
        "--bbox=-38,-11,-36,-9",
    ]


def test_point_and_bbox_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit):
        cli.main(["power", "--bbox", "sergipe", "--point", "-10,-37", "--start", "2025-01-01", "--end", "2025-01-02"])
    assert "not allowed with" in capsys.readouterr().err


@pytest.mark.parametrize(
    "extra",
    [
        ["--radius-km", "2"],
        ["--bbox", "1,2,3"],
        ["--start", "2025-02-01", "--end", "2025-01-01"],
    ],
)
def test_input_errors_exit_with_code_2(extra, capsys):
    argv = ["power", "--variable", "T2M", "--start", "2025-01-01", "--end", "2025-01-02"]
    for flag_index in range(0, len(extra), 2):
        flag = extra[flag_index]
        if flag in ("--start", "--end"):
            argv[argv.index(flag) + 1] = extra[flag_index + 1]
        else:
            argv += extra[flag_index : flag_index + 2]
    assert cli.main(argv) == 2
    assert capsys.readouterr().err.startswith("error:")


def test_power_command_writes_csv(tmp_path, monkeypatch, capsys):
    seen = {}

    def fake_fetch(lat, lon, dates, variables, **kwargs):
        seen.update(lat=lat, lon=lon, variables=variables, cache_dir=kwargs["cache_dir"])
        index = pd.date_range(dates.start, dates.end, name="date")
        return pd.DataFrame({"T2M": [27.0, np.nan]}, index=index)

    monkeypatch.setattr(power, "fetch_point", fake_fetch)
    out = tmp_path / "out.csv"
    code = cli.main(
        [
            "power",
            "--point",
            "-10.91,-37.07",
            "--radius-km",
            "1",
            "--start",
            "2025-01-01",
            "--end",
            "2025-01-02",
            "--variable",
            "T2M",
            "--out",
            str(out),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    )
    assert code == 0
    assert (seen["lat"], seen["lon"]) == pytest.approx((-10.91, -37.07)) and seen["variables"] == ["T2M"]
    assert seen["cache_dir"] == tmp_path / "cache" / "power"
    assert out.read_text().splitlines() == ["date,T2M", "2025-01-01,27.0", "2025-01-02,"]
    assert "last day with data 2025-01-01" in capsys.readouterr().out


def test_power_api_failure_is_a_clean_error(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise power.RemoteDataError("POWER API unavailable after 3 attempts")

    monkeypatch.setattr(power, "fetch_point", boom)
    code = cli.main(["power", "--variable", "T2M", "--start", "2025-01-01", "--end", "2025-01-02"])
    assert code == 1 and "unavailable" in capsys.readouterr().err


def test_search_only_reports_count_and_latest(monkeypatch, capsys):
    granules = [FakeGranule("2025-01-01T00:00:00.000Z"), FakeGranule("2025-01-31T21:00:00.000Z")]
    monkeypatch.setattr(earthdata, "search", lambda *args: granules)
    assert cli.main(["gldas", "--search-only", "--start", "2025-01-01", "--end", "2025-01-31"]) == 0
    assert "2 granules, latest start 2025-01-31" in capsys.readouterr().out


def test_missing_netrc_gives_login_hint(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("NETRC", raising=False)
    monkeypatch.setattr(earthdata, "search", lambda *args: [FakeGranule("2025-01-01T00:00:00Z")])
    code = cli.main(["gldas", "--variable", "SoilMoi0_10cm_inst", "--start", "2025-01-01", "--end", "2025-01-02"])
    assert code == 1 and "run scripts/earthdata-login.sh first" in capsys.readouterr().err


def test_earthdata_source_needs_variable(monkeypatch, capsys):
    monkeypatch.setattr(earthdata, "search", lambda *args: [FakeGranule("2025-01-01T00:00:00Z")])
    assert cli.main(["smap", "--start", "2025-01-01", "--end", "2025-01-02"]) == 2
    assert "--variable is required" in capsys.readouterr().err


def test_default_sources_and_region():
    assert earthdata.SOURCES["imerg"].short_name == "GPM_3IMERGDL"
    assert set(earthdata.SOURCES) == {"gldas", "imerg", "smap", "modis", "viirs", "hls"}
    assert PRESETS["sergipe"].west < PRESETS["sergipe"].east


def test_fetch_grid_clips_and_stacks_granules(tmp_path, monkeypatch):
    """GLDAS-like files: 1-D lat/lon, one time step per granule, read through a faked earthaccess.open."""
    lat, lon = np.arange(-12, -8.9, 0.25), np.arange(-39, -35.9, 0.25)
    paths, granules = [], []
    for day in (1, 2):
        ds = xr.Dataset(
            {"SoilMoi": (("time", "lat", "lon"), np.full((1, lat.size, lon.size), float(day)))},
            coords={"time": [np.datetime64(f"2025-01-0{day}")], "lat": lat, "lon": lon},
        )
        path = tmp_path / f"g{day}.nc4"
        ds.to_netcdf(path, engine="h5netcdf")
        paths.append(path)
        granules.append(FakeGranule(f"2025-01-0{day}T00:00:00Z"))
    monkeypatch.setattr(earthdata, "require_login", lambda: None)
    monkeypatch.setattr(earthdata.earthaccess, "open", lambda granules: paths)
    frame = earthdata.fetch_grid(earthdata.SOURCES["gldas"], granules, "SoilMoi", PRESETS["sergipe"], tmp_path)
    assert list(frame.columns) == ["time", "lat", "lon", "SoilMoi"]
    assert set(frame["SoilMoi"]) == {1.0, 2.0} and frame["lat"].between(-11.57, -9.51).all()
    with pytest.raises(earthdata.InputError, match="not found"):
        earthdata.fetch_grid(earthdata.SOURCES["gldas"], granules, "Missing", PRESETS["sergipe"], tmp_path)


def fake_power(monkeypatch):
    seen = {}

    def fetch(lat, lon, dates, variables, **kwargs):
        seen.update(lat=lat, lon=lon)
        return pd.DataFrame({"T2M": [1.0]}, index=pd.date_range(dates.start, dates.end, name="date"))

    monkeypatch.setattr(power, "fetch_point", fetch)
    return seen


def test_power_point_without_radius_uses_the_point(tmp_path, monkeypatch):
    seen = fake_power(monkeypatch)
    out = tmp_path / "p.csv"
    argv = ["power", "--point", "-10.91,-37.07", "--start", "2025-01-01", "--end", "2025-01-01", "--variable", "T2M"]
    assert cli.main([*argv, "--out", str(out)]) == 0
    assert (seen["lat"], seen["lon"]) == (-10.91, -37.07)


def test_power_bbox_uses_its_center_and_radius_needs_point(tmp_path, monkeypatch, capsys):
    seen = fake_power(monkeypatch)
    out = str(tmp_path / "p.csv")
    base = ["power", "--start", "2025-01-01", "--end", "2025-01-01", "--variable", "T2M", "--out", out]
    assert cli.main([*base, "--bbox", "-38,-12,-36,-10"]) == 0
    assert (seen["lat"], seen["lon"]) == (-11.0, -37.0)
    assert cli.main([*base, "--radius-km", "3"]) == 2
    assert "--radius-km needs --point" in capsys.readouterr().err


def test_grid_sources_still_need_radius_with_point(monkeypatch, capsys):
    monkeypatch.setattr(earthdata, "search", lambda *args: pytest.fail("must fail before searching"))
    assert cli.main(["gldas", "--point", "-10,-37", "--start", "2025-01-01", "--end", "2025-01-02"]) == 2
    assert "--point needs --radius-km" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("source", "out"),
    [
        ("power", "x.nc"),
        ("gldas", "x.txt"),
        ("smap", "data"),
        ("modis", "x.csv"),
        ("hls", "x.tif"),
        ("planetary", "x.parquet"),
    ],
)
def test_out_extension_is_checked_before_any_network_call(source, out, monkeypatch, capsys):
    monkeypatch.setattr(earthdata, "search", lambda *args: pytest.fail("searched"))
    monkeypatch.setattr(planetary, "open_client", lambda: pytest.fail("connected"))
    monkeypatch.setattr(power, "fetch_point", lambda *a, **k: pytest.fail("fetched"))
    argv = [source, "--variable", "T2M", "--start", "2025-01-01", "--end", "2025-01-02", "--out", out]
    assert cli.main(argv) == 2
    assert "--out" in capsys.readouterr().err


def test_default_versions_follow_the_default_short_name():
    gldas = earthdata.SOURCES["gldas"]
    assert earthdata.collection_query(gldas, None, None) == ("GLDAS_NOAH025_3H", "2.1")
    assert earthdata.collection_query(gldas, None, "2.0") == ("GLDAS_NOAH025_3H", "2.0")
    assert earthdata.collection_query(gldas, "GLDAS_NOAH025_M", None) == ("GLDAS_NOAH025_M", None)
    versions = {name: source.version for name, source in earthdata.SOURCES.items()}
    assert versions == {"gldas": "2.1", "imerg": "07", "smap": "006", "modis": "061", "viirs": "002", "hls": "2.0"}


def test_search_receives_the_default_version(monkeypatch):
    seen = []
    monkeypatch.setattr(earthdata, "search", lambda *args: seen.append(args) or [FakeGranule("2025-01-01T00:00:00Z")])
    cli.main(["smap", "--search-only", "--start", "2025-01-01", "--end", "2025-01-02"])
    cli.main(["smap", "--search-only", "--version", "009", "--start", "2025-01-01", "--end", "2025-01-02"])
    assert [(a[0], a[3]) for a in seen] == [("SPL3SMP_E", "006"), ("SPL3SMP_E", "009")]


class FakeHttpError(Exception):
    status = 403

    def __repr__(self):
        return "Auth(token=SECRET)"


def raiser(error):
    def raise_it(*args, **kwargs):
        raise error

    return raise_it


def test_remote_failures_become_short_messages(tmp_path, monkeypatch):
    monkeypatch.setattr(earthdata, "require_login", lambda: None)
    granules = [FakeGranule("2025-01-01T00:00:00Z")]
    cases = [(FakeHttpError("forbidden"), "access denied \\(HTTP 403\\)"), (OSError("disk gone"), "OSError: disk gone")]
    for error, expected in cases:
        monkeypatch.setattr(earthdata.earthaccess, "open", raiser(error))
        with pytest.raises(earthdata.RemoteDataError, match="opening the granules failed: " + expected) as caught:
            earthdata.fetch_grid(earthdata.SOURCES["gldas"], granules, "v", PRESETS["sergipe"], tmp_path)
        assert "SECRET" not in str(caught.value)


def test_download_failure_in_rasters_is_wrapped(tmp_path, monkeypatch):
    monkeypatch.setattr(earthdata, "require_login", lambda: None)
    monkeypatch.setattr(earthdata.earthaccess, "download", raiser(KeyError("links")))
    granules = [FakeGranule("2025-01-01T00:00:00Z")]
    with pytest.raises(earthdata.RemoteDataError, match="downloading the granules failed: KeyError"):
        earthdata.fetch_rasters("modis", granules, "NDVI", PRESETS["sergipe"], tmp_path, tmp_path)


def test_reading_failure_in_grid_is_wrapped(tmp_path, monkeypatch):
    monkeypatch.setattr(earthdata, "require_login", lambda: None)
    monkeypatch.setattr(earthdata.earthaccess, "open", lambda g: [tmp_path / "not-a-netcdf-file.nc4"])
    granules = [FakeGranule("2025-01-01T00:00:00Z")]
    with pytest.raises(earthdata.RemoteDataError, match="reading the granules failed"):
        earthdata.fetch_grid(earthdata.SOURCES["gldas"], granules, "v", PRESETS["sergipe"], tmp_path)


def test_point_smaller_than_a_cell_warns_on_stderr(tmp_path, monkeypatch, capsys):
    lat, lon = np.arange(-12, -8.9, 0.25), np.arange(-39, -35.9, 0.25)
    ds = xr.Dataset(
        {"v": (("time", "lat", "lon"), np.ones((1, lat.size, lon.size)))},
        coords={"time": [np.datetime64("2025-01-01")], "lat": lat, "lon": lon},
    )
    path = tmp_path / "g.nc4"
    ds.to_netcdf(path, engine="h5netcdf")
    monkeypatch.setattr(earthdata, "search", lambda *a: [FakeGranule("2025-01-01T00:00:00Z")])
    monkeypatch.setattr(earthdata, "require_login", lambda: None)
    monkeypatch.setattr(earthdata.earthaccess, "open", lambda g: [path])
    out = tmp_path / "o.csv"
    argv = ["gldas", "--variable", "v", "--point", "-10.91,-37.07", "--radius-km", "1"]
    argv += ["--start", "2025-01-01", "--end", "2025-01-01", "--out", str(out)]
    assert cli.main(argv) == 0
    assert "warning: the box is smaller than a grid cell" in capsys.readouterr().err
    assert len(pd.read_csv(out)) == 1


def test_granules_without_dates_give_a_short_error(monkeypatch, capsys):
    monkeypatch.setattr(earthdata, "search", lambda *args: [FakeGranule("x") | {"umm": {}}])
    assert cli.main(["gldas", "--search-only", "--start", "2025-01-01", "--end", "2025-01-02"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: reading the granule dates failed: KeyError") and "Traceback" not in err


def test_unwritable_output_gives_a_short_error(tmp_path, monkeypatch, capsys):
    fake_power(monkeypatch)
    (tmp_path / "out.csv").mkdir()
    argv = ["power", "--point", "-10,-37", "--start", "2025-01-01", "--end", "2025-01-01", "--variable", "T2M"]
    assert cli.main([*argv, "--out", str(tmp_path / "out.csv")]) == 1
    assert capsys.readouterr().err.startswith("error: writing out.csv failed: IsADirectoryError")


def test_parquet_write_failure_is_wrapped(tmp_path, monkeypatch, capsys):
    fake_power(monkeypatch)

    def broken(self, *args, **kwargs):
        raise ValueError("arrow says no")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", broken)
    argv = ["power", "--point", "-10,-37", "--start", "2025-01-01", "--end", "2025-01-01", "--variable", "T2M"]
    assert cli.main([*argv, "--out", str(tmp_path / "o.parquet")]) == 1
    assert "writing o.parquet failed: ValueError: arrow says no" in capsys.readouterr().err
