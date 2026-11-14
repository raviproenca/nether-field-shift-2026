# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""CLI and Earthdata plumbing tests with fakes: no network, no login."""

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from src.data import cli, earthdata, power
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
        ["--point", "-10,-37"],
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
            "--raw-dir",
            str(tmp_path / "raw"),
        ]
    )
    assert code == 0
    assert (seen["lat"], seen["lon"]) == pytest.approx((-10.91, -37.07)) and seen["variables"] == ["T2M"]
    assert seen["cache_dir"] == tmp_path / "raw" / "power"
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
