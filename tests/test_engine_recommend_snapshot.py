# AI-assisted: generated with Cursor, reviewed by Lucas Feitosa.
"""Run recommend() on the cached Sergipe POWER snapshot for the two pilots."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from src.engine import (
    Crop,
    Diagnosis,
    Plot,
    Priority,
    Projection,
    SourceAttribution,
    load_rules,
    recommend,
    serialize_recommendation,
)

ROOT = Path(__file__).resolve().parents[1]
POWER_PATH = ROOT / "apps" / "web" / "public" / "data" / "sergipe" / "power.json"
POINTS_PATH = ROOT / "apps" / "web" / "public" / "data" / "sergipe" / "points.geojson"
PILOTS_PATH = ROOT / "apps" / "web" / "public" / "data" / "sergipe" / "pilots.geojson"
SCHEMA_PATH = ROOT / "docs" / "data-format" / "recommendation.schema.json"
RULES = load_rules()


def _load() -> tuple[dict, dict[str, tuple[float, float]], list[dict]]:
    power = json.loads(POWER_PATH.read_text(encoding="utf-8"))
    points = json.loads(POINTS_PATH.read_text(encoding="utf-8"))
    pilots = json.loads(PILOTS_PATH.read_text(encoding="utf-8"))
    grid = {
        feature["properties"]["id"]: (
            feature["properties"]["lat"],
            feature["properties"]["lon"],
        )
        for feature in points["features"]
    }
    return power, grid, pilots["features"]


def _nearest(lat: float, lon: float, grid: dict[str, tuple[float, float]]) -> str:
    return min(grid, key=lambda point_id: (grid[point_id][0] - lat) ** 2 + (grid[point_id][1] - lon) ** 2)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def test_pilots_use_nearest_power_cell_and_rank_a_legume_after_maize() -> None:
    """Itabaiana and Nossa Senhora da Glória, previous crop maize, priority water."""
    power, grid, pilots = _load()
    period = power["period"]
    attribution = power["attribution"]
    source = SourceAttribution(
        source=power["source"],
        dataset=attribution["dataset"],
        nasa=True,
        url=attribution["url"],
        doi=attribution["doi"],
        notice=attribution["notice"],
    )
    projection = Projection(
        period_start=period["end"],
        period_end=period["end"],
        horizon_days=15,
        available=False,
    )

    expected = {
        "sergipe_agreste_itabaiana": ("SE036", 11.68, 28.01, -176.85),
        "sergipe_semiarido_ns_gloria": ("SE020", 9.7, 29.58, -216.41),
    }
    assert {feature["properties"]["id"] for feature in pilots} == set(expected)

    for feature in pilots:
        props = feature["properties"]
        point_id = _nearest(props["lat"], props["lon"], grid)
        expect_id, expect_rain, expect_temp, expect_balance = expected[props["id"]]
        assert point_id == expect_id
        series = power["points"][point_id]
        rain = [row["values"]["PRECTOTCORR"] for row in series if row["values"]["PRECTOTCORR"] is not None]
        temperature = [row["values"]["T2M"] for row in series if row["values"]["T2M"] is not None]
        balance = [row["values"]["WATER_BALANCE"] for row in series if row["values"]["WATER_BALANCE"] is not None]
        assert rain and temperature and balance

        diagnosis = Diagnosis(
            period_start=period["start"],
            period_end=period["end"],
            rain_total_mm=round(sum(rain), 2),
            temperature_mean_c=round(_mean(temperature), 2),
            water_balance_mm=round(sum(balance), 2),
            sources=(source,),
        )
        plot = Plot(
            id=props["id"],
            name=props["name"],
            lat=props["lat"],
            lon=props["lon"],
            radius_km=props["radius_km"],
            region=props["zone"],
            previous_crops=("maize",),
        )
        water = recommend(plot, diagnosis, projection, Crop.MAIZE, Priority.WATER, RULES)
        income = recommend(plot, diagnosis, projection, Crop.MAIZE, Priority.INCOME, RULES)

        assert [strategy.kind.value for strategy in water.strategies] == [
            "soil_water_conservation",
            "current_practice",
            "resilient_income_forage",
        ]
        assert water.strategies[0].crops == ("maize", "beans")
        assert income.strategies[0].kind.value == "resilient_income_forage"
        assert "severe deficit" in water.uncertainty_note
        recommendation = water
        assert diagnosis.rain_total_mm == expect_rain
        assert diagnosis.temperature_mean_c == expect_temp
        assert diagnosis.water_balance_mm == expect_balance
        assert recommendation.diagnosis.rain_total_mm == diagnosis.rain_total_mm
        assert recommendation.uncertainty_note.startswith("The forecast is absent.")
        payload = json.loads(json.dumps(serialize_recommendation(recommendation)))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
        assert payload["plot"]["id"] == props["id"]
        assert payload["diagnosis"]["sources"][0]["nasa"] is True
        assert payload["diagnosis"]["sources"][0]["source"] == "power"
