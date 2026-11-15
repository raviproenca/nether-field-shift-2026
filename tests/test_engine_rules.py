# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Unit tests for src/engine/rules.py agronomic profiles and thresholds (Issue #45)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.engine import (
    DEFAULT_RULES_DIR,
    Crop,
    CropProfile,
    EngineRules,
    Priority,
    RuleThresholds,
    load_crop_profiles,
    load_rules,
    load_thresholds,
    parse_crop_profiles,
    parse_rules,
    parse_thresholds,
)


def _load_default_crops_yaml() -> dict[str, Any]:
    """Helper to load default crops.yaml raw dictionary for mutation tests."""
    raw = yaml.safe_load((DEFAULT_RULES_DIR / "crops.yaml").read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def _load_default_thresholds_yaml() -> dict[str, Any]:
    """Helper to load default thresholds.yaml raw dictionary for mutation tests."""
    raw = yaml.safe_load(
        (DEFAULT_RULES_DIR / "thresholds.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(raw, dict)
    return raw


def test_load_rules_has_all_v1_crops_with_water_cycle_and_heat_sources() -> None:
    """Verify that default YAML rules load Crop.MAIZE, BEANS, CASSAVA with full citations."""
    rules = load_rules()

    assert isinstance(rules, EngineRules)
    expected_crops = {Crop.MAIZE, Crop.BEANS, Crop.CASSAVA}
    assert set(rules.crops.keys()) == expected_crops

    for crop in expected_crops:
        profile = rules.crops[crop]
        assert isinstance(profile, CropProfile)
        assert profile.crop == crop
        assert profile.name and profile.name.strip()

        # Water need rule verification
        wn = profile.water_need
        assert wn.min_mm > 0.0
        assert wn.min_mm <= wn.typical_mm <= wn.max_mm
        assert isinstance(wn.source, str) and len(wn.source.strip()) > 0
        assert wn.url is not None and wn.url.startswith("http")

        # Cycle length rule verification
        cl = profile.cycle_length
        assert cl.min_days > 0
        assert cl.min_days <= cl.typical_days <= cl.max_days
        assert isinstance(cl.source, str) and len(cl.source.strip()) > 0
        assert cl.url is not None and cl.url.startswith("http")

        # Heat limit rule verification
        hl = profile.heat_limit
        assert hl.max_optimal_c > 0.0
        assert hl.max_optimal_c <= hl.critical_c
        assert isinstance(hl.sensitive_stage, str) and len(hl.sensitive_stage.strip()) > 0
        assert isinstance(hl.source, str) and len(hl.source.strip()) > 0
        assert hl.url is not None and hl.url.startswith("http")


def test_crop_profiles_include_water_demand_kc_and_planting_calendar_parameters() -> None:
    """Verify FAO-56 Kc parameters, planting calendar pilot anchors/heuristics, botanical family, and N-fixation."""
    rules = load_rules()

    # Botanical family and nitrogen fixation assertions
    maize = rules.crops[Crop.MAIZE]
    assert maize.botanical_family == "Poaceae"
    assert maize.fixes_nitrogen is False

    beans = rules.crops[Crop.BEANS]
    assert beans.botanical_family == "Fabaceae"
    assert beans.fixes_nitrogen is True

    cassava = rules.crops[Crop.CASSAVA]
    assert cassava.botanical_family == "Euphorbiaceae"
    assert cassava.fixes_nitrogen is False

    # Check each crop's Kc and planting calendar parameters
    for crop, profile in rules.crops.items():
        assert profile.soil_cover_rating in {
            "low",
            "low_initial",
            "medium",
            "medium_high",
            "high",
        }

        # FAO-56 Kc stage curve
        kc = profile.kc
        assert kc.kc_ini >= 0.0
        assert kc.kc_mid >= 0.0
        assert kc.kc_end >= 0.0
        assert isinstance(kc.source, str) and len(kc.source.strip()) > 0
        assert kc.url is not None and kc.url.startswith("http")

        # Planting calendar (pilot calendar decendios and rainfall onset heuristic; full ZARC validation is in #48)
        cal = profile.planting_calendar
        assert cal.preferred_season in {"wet", "dry"}
        assert 1 <= cal.start_month <= 12
        assert 1 <= cal.end_month <= 12
        assert cal.start_month <= cal.end_month
        assert 1 <= cal.start_decendio <= 36
        assert 1 <= cal.end_decendio <= 36
        assert cal.start_decendio <= cal.end_decendio
        assert cal.min_15d_rain_onset_mm >= 0.0
        assert isinstance(cal.source, str) and len(cal.source.strip()) > 0
        assert cal.url is not None and cal.url.startswith("http")


def test_load_thresholds_validates_all_priorities_and_agroclimatic_limits() -> None:
    """Verify agroclimatic thresholds and priority weights summing to 1.0."""
    thresholds = load_thresholds()
    assert isinstance(thresholds, RuleThresholds)

    # Water balance deficit & SMAP surface moisture limits
    wb = thresholds.water_balance
    assert wb.severe_deficit_mm < 0.0
    assert wb.moderate_deficit_mm < 0.0
    assert wb.severe_deficit_mm <= wb.moderate_deficit_mm
    assert 0.0 <= wb.min_smap_surface_m3m3 <= 1.0
    assert wb.min_forecast_15d_rain_mm >= 0.0
    assert isinstance(wb.source, str) and len(wb.source.strip()) > 0
    assert wb.url is not None and wb.url.startswith("http")

    # Vegetation index thresholds
    veg = thresholds.vegetation_and_bare_soil
    assert (
        -1.0
        <= veg.bare_soil_ndvi_max
        <= veg.sparse_cover_ndvi_max
        <= veg.healthy_cover_ndvi_min
        <= 1.0
    )
    assert veg.bare_soil_ndvi_max == 0.20
    assert veg.sparse_cover_ndvi_max == 0.30
    assert veg.healthy_cover_ndvi_min == 0.60
    assert isinstance(veg.source, str) and len(veg.source.strip()) > 0
    assert veg.url is not None and veg.url.startswith("http")

    # Terrain and slope classes
    ter = thresholds.terrain_and_erosion
    assert (
        0.0
        <= ter.gentle_slope_max_pct
        <= ter.contour_planting_min_slope_pct
        <= ter.high_erosion_risk_slope_pct
    )
    assert isinstance(ter.source, str) and len(ter.source.strip()) > 0
    assert ter.url is not None and ter.url.startswith("http")

    # Multi-criteria priority weights
    expected_priorities = {
        Priority.WATER,
        Priority.SOIL,
        Priority.EROSION,
        Priority.INCOME,
    }
    assert set(thresholds.priority_weights.keys()) == expected_priorities

    for priority, weights in thresholds.priority_weights.items():
        assert 0.0 <= weights.water_efficiency <= 1.0
        assert 0.0 <= weights.soil_health <= 1.0
        assert 0.0 <= weights.erosion_control <= 1.0
        assert 0.0 <= weights.income_resilience <= 1.0

        total_weight = (
            weights.water_efficiency
            + weights.soil_health
            + weights.erosion_control
            + weights.income_resilience
        )
        assert pytest.approx(total_weight, abs=1e-6) == 1.0


def test_parse_crop_profiles_rejects_missing_crop_missing_source_or_inverted_bounds() -> None:
    """Verify rejection of missing crops, missing source citations, or inverted bounds."""
    base_data = _load_default_crops_yaml()

    # 1. Missing a v1 crop profile (e.g. beans)
    bad_data = copy.deepcopy(base_data)
    del bad_data["crops"]["beans"]
    with pytest.raises(ValueError, match="Missing required crop profile"):
        parse_crop_profiles(bad_data)

    # 2. Missing top-level 'crops' key
    bad_data = copy.deepcopy(base_data)
    del bad_data["crops"]
    with pytest.raises(ValueError, match="Missing required top-level mapping 'crops'"):
        parse_crop_profiles(bad_data)

    # 3. Unknown crop key
    bad_data = copy.deepcopy(base_data)
    bad_data["crops"]["coffee"] = copy.deepcopy(bad_data["crops"]["maize"])
    with pytest.raises(ValueError, match="Unknown crop profile"):
        parse_crop_profiles(bad_data)

    # 4. Missing source in water_need_mm
    bad_data = copy.deepcopy(base_data)
    del bad_data["crops"]["maize"]["water_need_mm"]["source"]
    with pytest.raises(ValueError, match="Missing required string 'crops.maize.water_need_mm.source'"):
        parse_crop_profiles(bad_data)

    # 5. Empty source in water_need_mm
    bad_data = copy.deepcopy(base_data)
    bad_data["crops"]["maize"]["water_need_mm"]["source"] = "   "
    with pytest.raises(ValueError, match="'crops.maize.water_need_mm.source' must be a non-empty string"):
        parse_crop_profiles(bad_data)

    # 6. Missing source in cycle_length_days
    bad_data = copy.deepcopy(base_data)
    del bad_data["crops"]["beans"]["cycle_length_days"]["source"]
    with pytest.raises(ValueError, match="Missing required string 'crops.beans.cycle_length_days.source'"):
        parse_crop_profiles(bad_data)

    # 7. Empty source in cycle_length_days
    bad_data = copy.deepcopy(base_data)
    bad_data["crops"]["beans"]["cycle_length_days"]["source"] = ""
    with pytest.raises(ValueError, match="'crops.beans.cycle_length_days.source' must be a non-empty string"):
        parse_crop_profiles(bad_data)

    # 8. Missing source in heat_limit_c
    bad_data = copy.deepcopy(base_data)
    del bad_data["crops"]["cassava"]["heat_limit_c"]["source"]
    with pytest.raises(ValueError, match="Missing required string 'crops.cassava.heat_limit_c.source'"):
        parse_crop_profiles(bad_data)

    # 9. Inverted water_need_mm bounds (min_mm > max_mm)
    bad_data = copy.deepcopy(base_data)
    bad_data["crops"]["maize"]["water_need_mm"]["min_mm"] = 900.0
    bad_data["crops"]["maize"]["water_need_mm"]["max_mm"] = 500.0
    bad_data["crops"]["maize"]["water_need_mm"]["typical_mm"] = 600.0
    with pytest.raises(ValueError, match="expected min <= typical <= max"):
        parse_crop_profiles(bad_data)

    # 10. Inverted cycle_length_days bounds (min_days > max_days)
    bad_data = copy.deepcopy(base_data)
    bad_data["crops"]["beans"]["cycle_length_days"]["min_days"] = 120
    bad_data["crops"]["beans"]["cycle_length_days"]["max_days"] = 90
    bad_data["crops"]["beans"]["cycle_length_days"]["typical_days"] = 100
    with pytest.raises(ValueError, match="expected min <= typical <= max"):
        parse_crop_profiles(bad_data)

    # 11. Inverted heat_limit_c bounds (max_optimal_c > critical_c)
    bad_data = copy.deepcopy(base_data)
    bad_data["crops"]["cassava"]["heat_limit_c"]["max_optimal_c"] = 40.0
    bad_data["crops"]["cassava"]["heat_limit_c"]["critical_c"] = 35.0
    with pytest.raises(ValueError, match="expected max_optimal_c <= critical_c"):
        parse_crop_profiles(bad_data)

    # 12. Inverted planting_calendar decendios
    bad_data = copy.deepcopy(base_data)
    bad_data["crops"]["maize"]["planting_calendar"]["start_decendio"] = 40
    with pytest.raises(ValueError, match="start_decendio must be in 1..36"):
        parse_crop_profiles(bad_data)


def test_parse_thresholds_rejects_missing_priority_or_bad_weight_sum() -> None:
    """Verify rejection of missing priorities, invalid weights, or improper limits."""
    base_data = _load_default_thresholds_yaml()

    # 1. Missing a priority entry (e.g. income)
    bad_data = copy.deepcopy(base_data)
    del bad_data["priority_weights"]["income"]
    with pytest.raises(ValueError, match="Missing required priority_weights entry"):
        parse_thresholds(bad_data)

    # 2. Unknown priority entry
    bad_data = copy.deepcopy(base_data)
    bad_data["priority_weights"]["biodiversity"] = copy.deepcopy(
        bad_data["priority_weights"]["water"]
    )
    with pytest.raises(ValueError, match="Unknown priority_weights entry"):
        parse_thresholds(bad_data)

    # 3. Weights do not sum to 1.0 (e.g. sum = 1.30)
    bad_data = copy.deepcopy(base_data)
    bad_data["priority_weights"]["water"]["water_efficiency"] = 0.80
    with pytest.raises(ValueError, match="weights must sum to 1.0"):
        parse_thresholds(bad_data)

    # 4. Negative weight
    bad_data = copy.deepcopy(base_data)
    bad_data["priority_weights"]["soil"]["soil_health"] = -0.10
    with pytest.raises(ValueError, match="must be in"):
        parse_thresholds(bad_data)

    # 5. Inverted water balance deficit thresholds (severe > moderate)
    bad_data = copy.deepcopy(base_data)
    bad_data["water_balance"]["severe_deficit_mm"] = -20.0
    bad_data["water_balance"]["moderate_deficit_mm"] = -100.0
    with pytest.raises(ValueError, match="expected severe_deficit_mm <= moderate_deficit_mm"):
        parse_thresholds(bad_data)

    # 6. Inverted vegetation NDVI thresholds
    bad_data = copy.deepcopy(base_data)
    bad_data["vegetation_and_bare_soil"]["bare_soil_ndvi_max"] = 0.60
    with pytest.raises(ValueError, match="expected -1.0 <= bare_soil_ndvi_max <= sparse_cover_ndvi_max"):
        parse_thresholds(bad_data)

    # 7. Inverted terrain slope thresholds
    bad_data = copy.deepcopy(base_data)
    bad_data["terrain_and_erosion"]["gentle_slope_max_pct"] = 10.0
    bad_data["terrain_and_erosion"]["contour_planting_min_slope_pct"] = 5.0
    with pytest.raises(ValueError, match="expected 0.0 <= gentle_slope_max_pct <= contour_planting_min_slope_pct"):
        parse_thresholds(bad_data)


def test_load_rules_from_custom_yaml_directory_reflects_tuned_values(tmp_path: Path) -> None:
    """Verify that custom YAML files in a separate directory load and reflect tuned values."""
    crops_data = _load_default_crops_yaml()
    thresholds_data = _load_default_thresholds_yaml()

    # Apply custom tuned parameters
    crops_data["crops"]["maize"]["water_need_mm"]["min_mm"] = 520.0
    crops_data["crops"]["maize"]["water_need_mm"]["typical_mm"] = 580.0
    crops_data["crops"]["maize"]["water_need_mm"]["max_mm"] = 820.0

    crops_data["crops"]["beans"]["cycle_length_days"]["typical_days"] = 105

    thresholds_data["water_balance"]["severe_deficit_mm"] = -175.0
    thresholds_data["water_balance"]["moderate_deficit_mm"] = -75.0
    thresholds_data["terrain_and_erosion"]["gentle_slope_max_pct"] = 4.0

    # Write tuned YAML files into tmp_path
    crops_path = tmp_path / "crops.yaml"
    thresholds_path = tmp_path / "thresholds.yaml"
    crops_path.write_text(yaml.safe_dump(crops_data), encoding="utf-8")
    thresholds_path.write_text(yaml.safe_dump(thresholds_data), encoding="utf-8")

    # Load custom rules
    rules = load_rules(tmp_path)

    assert rules.crops[Crop.MAIZE].water_need.min_mm == 520.0
    assert rules.crops[Crop.MAIZE].water_need.typical_mm == 580.0
    assert rules.crops[Crop.MAIZE].water_need.max_mm == 820.0
    assert rules.crops[Crop.BEANS].cycle_length.typical_days == 105

    assert rules.thresholds.water_balance.severe_deficit_mm == -175.0
    assert rules.thresholds.water_balance.moderate_deficit_mm == -75.0
    assert rules.thresholds.terrain_and_erosion.gentle_slope_max_pct == 4.0

    # Unmodified fields should still match their expected default values
    assert rules.crops[Crop.CASSAVA].botanical_family == "Euphorbiaceae"
    assert rules.thresholds.priority_weights[Priority.WATER].water_efficiency == 0.50


def test_load_rules_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    """Verify that missing crops.yaml or thresholds.yaml raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Rules YAML file not found"):
        load_rules(tmp_path)


def test_parse_rules_combines_crops_and_thresholds() -> None:
    """Verify that parse_rules combines valid crop and threshold mappings directly."""
    crops_data = _load_default_crops_yaml()
    thresholds_data = _load_default_thresholds_yaml()

    rules = parse_rules(crops_data, thresholds_data)
    assert isinstance(rules, EngineRules)
    assert len(rules.crops) == 3
    assert len(rules.thresholds.priority_weights) == 4
