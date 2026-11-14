# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
import math

import pytest

from src.data.errors import InputError
from src.data.regions import PRESETS, parse_bbox, parse_point, point_to_bbox, resolve_region


def test_default_region_is_sergipe():
    assert resolve_region() == PRESETS["sergipe"]


def test_preset_is_case_insensitive():
    assert parse_bbox("Nordeste") == PRESETS["nordeste"]


def test_free_bbox():
    box = parse_bbox("-38.5, -11.6, -36.3, -9.5")
    assert box.as_tuple == (-38.5, -11.6, -36.3, -9.5)
    assert box.center == pytest.approx((-10.55, -37.4))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "1,2,3",
        "a,b,c,d",
        "-36,-11,-38,-9",
        "-38,-9,-36,-11",
        "-200,-11,-36,-9",
        "-38,-95,-36,-9",
        "nan,0,1,1",
        "atlantis",
    ],
)
def test_invalid_bbox(text):
    with pytest.raises(InputError):
        parse_bbox(text)


def test_parse_point():
    assert parse_point("-10.91,-37.07") == (-10.91, -37.07)


@pytest.mark.parametrize("text", ["1", "a,b", "95,10", "10,190", "90,0"])
def test_invalid_point(text):
    with pytest.raises(InputError):
        parse_point(text)


def test_point_to_bbox_at_equator():
    box = point_to_bbox(0.0, -37.0, 11.132)
    assert box.south == pytest.approx(-0.1)
    assert box.north == pytest.approx(0.1)
    assert box.west == pytest.approx(-37.1)
    assert box.east == pytest.approx(-36.9)


def test_point_to_bbox_widens_longitude_with_latitude():
    box = point_to_bbox(-10.91, -37.07, 5)
    assert box.north - box.south == pytest.approx(2 * 5 / 111.32)
    assert box.east - box.west == pytest.approx(2 * 5 / (111.32 * math.cos(math.radians(10.91))))
    assert box.center == pytest.approx((-10.91, -37.07))


@pytest.mark.parametrize("radius", [0, -1, math.inf, math.nan])
def test_point_to_bbox_invalid_radius(radius):
    with pytest.raises(InputError):
        point_to_bbox(-10.91, -37.07, radius)


def test_point_to_bbox_rejects_pole_and_out_of_range_box():
    with pytest.raises(InputError):
        point_to_bbox(89.9, 0, 1)
    with pytest.raises(InputError):
        point_to_bbox(0, 179.9, 100)


def test_resolve_region_from_point():
    box = resolve_region(point="-10.91,-37.07", radius_km=2)
    assert box.center == pytest.approx((-10.91, -37.07))


def test_resolve_region_rules():
    with pytest.raises(InputError):
        resolve_region(bbox="sergipe", point="-10,-37", radius_km=1)
    with pytest.raises(InputError):
        resolve_region(point="-10,-37")
    with pytest.raises(InputError):
        resolve_region(radius_km=3)
