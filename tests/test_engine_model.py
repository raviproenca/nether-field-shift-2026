# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Unit tests for src/engine/model.py serialization and JSON Schema validation."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from src.engine import (
    Action,
    BareSoilWindow,
    Crop,
    CropSchedule,
    Diagnosis,
    Plot,
    Priority,
    Projection,
    Recommendation,
    SoilInfo,
    SourceAttribution,
    Strategy,
    StrategyKind,
    serialize_recommendation,
)

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "data-format"
    / "recommendation.schema.json"
)
SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def get_validator() -> Draft202012Validator:
    """Load recommendation.schema.json and return a Draft 2020-12 validator."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def make_sample_recommendation(*, soil: SoilInfo | None = "default") -> Recommendation:  # type: ignore[assignment]
    """Build a realistic sample Recommendation for the Itabaiana (SE) pilot site."""
    if soil == "default":
        soil = SoilInfo(
            texture="sandy_loam",
            organic_carbon_g_kg=9.5,
            ph=5.8,
            water_holding_capacity_mm=85.0,
            notes="Typical Agreste tableland soil",
            source="Embrapa Solos reference",
        )

    nasa_power = SourceAttribution(
        source="power",
        dataset="NASA POWER Agroclimatology Daily v2.x",
        nasa=True,
        url="https://power.larc.nasa.gov/",
    )
    nasa_smap = SourceAttribution(
        source="smap",
        dataset="SMAP L3 Radiometer Global Daily 9 km EASE-Grid Soil Moisture v006",
        nasa=True,
        url="https://nsidc.org/data/spl3smp_e",
        doi="10.5067/4DQ54OUIJ9B0",
    )
    open_meteo = SourceAttribution(
        source="open_meteo",
        dataset="Open-Meteo 15-day Forecast API (ECMWF/GFS)",
        nasa=False,
        url="https://open-meteo.com/",
        notice="CC BY 4.0 (non-commercial demo use)",
    )

    plot = Plot(
        lat=-10.685,
        lon=-37.425,
        radius_km=5.0,
        id="SE-ITABAIANA",
        name="Itabaiana Pilot",
        region="agreste",
        municipality_code="2802908",
        elevation_m=188.0,
        slope_mean_deg=2.4,
        slope_mean_pct=4.2,
        soil=soil,
        season="wet",
        previous_crops=("maize",),
    )

    diagnosis = Diagnosis(
        period_start="2026-08-15",
        period_end="2026-11-12",
        rain_total_mm=142.5,
        rain_daily_mean_mm=1.58,
        et0_daily_mean_mm=4.62,
        water_balance_mm=-273.6,
        soil_moisture_surface_m3m3=0.14,
        soil_moisture_root_kgm2=210.0,
        temperature_mean_c=25.4,
        temperature_max_c=32.1,
        ndvi_mean=0.41,
        elevation_m=188.0,
        slope_mean_pct=4.2,
        bare_soil_windows=(
            BareSoilWindow(
                start="2026-09-01",
                end="2026-09-30",
                ndvi_mean=0.22,
                description="Low vegetative cover after harvest",
            ),
        ),
        sources=(nasa_power, nasa_smap),
    )

    projection = Projection(
        period_start="2026-11-15",
        period_end="2026-11-29",
        horizon_days=15,
        available=True,
        rain_total_mm=28.0,
        rain_daily_mean_mm=1.87,
        temperature_mean_c=26.8,
        temperature_max_c=33.5,
        et0_daily_mean_mm=5.1,
        water_balance_mm=-48.5,
        sources=(open_meteo,),
    )

    strategies = (
        Strategy(
            kind=StrategyKind.SOIL_WATER_CONSERVATION,
            rank=1,
            score=84.5,
            title="Maize + beans intercropping with crop-residue mulching",
            crops=("beans", "maize"),
            trade_offs=(
                "Requires staggered planting management",
                "Slightly lower single-crop peak yield in exchange for moisture retention",
            ),
            planting_schedule=(
                CropSchedule(
                    crop="beans",
                    planting_start="2026-04-15",
                    planting_end="2026-05-31",
                    cycle_days=75,
                    water_demand_mm=310.0,
                ),
                CropSchedule(
                    crop="maize",
                    planting_start="2026-04-20",
                    planting_end="2026-05-31",
                    cycle_days=110,
                    water_demand_mm=480.0,
                ),
            ),
            water_demand_mm=480.0,
            breaks_pest_cycle=True,
            pest_cycle_note="Introduces a legume (beans) after monocrop maize, reducing grass-specific pest carryover.",
            actions=(
                Action(
                    code="MULCH_COVER",
                    summary="Keep previous maize stover on the surface before planting beans.",
                    timing="2 weeks before planting window",
                    evidence="Diagnosis water balance is -273.6 mm with bare soil NDVI 0.22 in September.",
                ),
            ),
        ),
        Strategy(
            kind=StrategyKind.RESILIENT_INCOME_FORAGE,
            rank=2,
            score=76.0,
            title="Drought-tolerant cassava + short-cycle beans relay",
            crops=("cassava", "beans"),
            trade_offs=(
                "Longer time to main cassava harvest (12 months)",
                "Lower water sensitivity during dry spells",
            ),
            planting_schedule=(
                CropSchedule(
                    crop="cassava",
                    planting_start="2026-04-01",
                    planting_end="2026-06-30",
                    cycle_days=360,
                    water_demand_mm=600.0,
                ),
                CropSchedule(
                    crop="beans",
                    planting_start="2026-05-01",
                    planting_end="2026-06-15",
                    cycle_days=75,
                    water_demand_mm=310.0,
                ),
            ),
            water_demand_mm=600.0,
            breaks_pest_cycle=True,
            pest_cycle_note="Replaces Poaceae (maize) with Euphorbiaceae (cassava) and Fabaceae (beans).",
            actions=(
                Action(
                    code="RELAY_SPACING",
                    summary="Plant cassava in double rows to intercrop short-cycle beans between rows.",
                    timing="At onset of rainy season (April-May)",
                    evidence="SMAP surface moisture is 0.14 m3/m3; wider spacing reduces root competition.",
                ),
            ),
        ),
        Strategy(
            kind=StrategyKind.CURRENT_PRACTICE,
            rank=3,
            score=58.0,
            title="Baseline monocrop beans without soil cover",
            crops=("beans",),
            trade_offs=(
                "Simpler field operation",
                "High vulnerability to dry spells (veranicos) and bare-soil evaporation",
            ),
            planting_schedule=(
                CropSchedule(
                    crop="beans",
                    planting_start="2026-05-01",
                    planting_end="2026-06-15",
                    cycle_days=75,
                    water_demand_mm=350.0,
                ),
            ),
            water_demand_mm=350.0,
            breaks_pest_cycle=True,
            pest_cycle_note="Rotates legume after previous maize crop.",
            actions=(
                Action(
                    code="WAIT_RAIN_ONSET",
                    summary="Avoid dry sowing until cumulative 15-day rain exceeds 35 mm.",
                    timing="Next 15 days",
                    evidence="Open-Meteo 15-day forecast shows only 28.0 mm against ET0 of 5.1 mm/day.",
                ),
            ),
        ),
    )

    return Recommendation(
        plot=plot,
        crop=Crop.BEANS,
        priority=Priority.WATER,
        diagnosis=diagnosis,
        projection=projection,
        strategies=strategies,
        uncertainty_note="15-day weather forecast is indicative; seasonal transition has moderate spread.",
        validation_note="Planting windows aligned with MAPA ZARC portaria for Sergipe (municipality 2802908).",
        sources=(nasa_power, nasa_smap, open_meteo),
    )


# ---------------------------------------------------------------------------
# Test cases required by Issue #44 (Step 3)
# ---------------------------------------------------------------------------


def test_sample_recommendation_serializes_and_validates_against_schema() -> None:
    validator = get_validator()
    rec = make_sample_recommendation()

    payload = json.loads(json.dumps(rec.to_dict()))
    validator.validate(payload)

    assert payload["schema_version"] == 1
    assert payload["crop"] == "beans"
    assert payload["priority"] == "water"
    assert len(payload["strategies"]) == 3


def test_recommendation_accepts_missing_or_partial_soil_without_source() -> None:
    validator = get_validator()

    # Scenario 1: soil is completely None
    rec_no_soil = make_sample_recommendation(soil=None)
    payload_no_soil = json.loads(json.dumps(rec_no_soil.to_dict()))
    validator.validate(payload_no_soil)
    assert payload_no_soil["plot"]["soil"] is None

    # Scenario 2: partial SoilInfo with source=None
    rec_partial_soil = make_sample_recommendation(
        soil=SoilInfo(texture="sandy", source=None)
    )
    payload_partial_soil = json.loads(json.dumps(rec_partial_soil.to_dict()))
    validator.validate(payload_partial_soil)
    assert payload_partial_soil["plot"]["soil"]["texture"] == "sandy"
    assert payload_partial_soil["plot"]["soil"]["source"] is None


def _collect_all_keys(node: Any) -> list[str]:
    """Recursively collect every dictionary key in a JSON-serializable object."""
    keys: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            keys.append(k)
            keys.extend(_collect_all_keys(v))
    elif isinstance(node, list):
        for item in node:
            keys.extend(_collect_all_keys(item))
    return keys


def test_all_serialized_keys_are_snake_case() -> None:
    rec = make_sample_recommendation()
    payload = rec.to_dict()

    all_keys = _collect_all_keys(payload)
    assert all_keys, "Expected non-empty serialized dictionary keys"
    invalid_keys = [k for k in all_keys if not SNAKE_CASE_RE.match(k)]
    assert invalid_keys == [], f"Found non-snake_case keys: {invalid_keys}"


def test_schema_rejects_fewer_than_three_strategies() -> None:
    validator = get_validator()
    rec = make_sample_recommendation()

    # Keep only 2 strategies in the serialized payload
    payload = json.loads(json.dumps(rec.to_dict()))
    payload["strategies"] = payload["strategies"][:2]

    with pytest.raises(ValidationError):
        validator.validate(payload)


def test_engine_package_has_no_io_side_effects() -> None:
    rec_a = make_sample_recommendation()
    rec_b = make_sample_recommendation()

    bytes_a = json.dumps(rec_a.to_dict(), sort_keys=True)
    bytes_b = json.dumps(serialize_recommendation(rec_b), sort_keys=True)

    assert bytes_a == bytes_b

    # Also verify list -> tuple normalization in __post_init__ produces identical output
    plot_with_list = replace(rec_a.plot, previous_crops=["maize"])  # type: ignore[arg-type]
    rec_from_list = replace(rec_a, plot=plot_with_list)
    assert isinstance(rec_from_list.plot.previous_crops, tuple)
    assert json.dumps(rec_from_list.to_dict(), sort_keys=True) == bytes_a