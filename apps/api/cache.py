# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Pilot cache pre-warming, disk cache serialization, and 0.01° spatial rounding (AD-7, AD-9)."""

from __future__ import annotations

import copy
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
import json
import os
from pathlib import Path
from typing import Any, Literal, Sequence

from src.data.paths import CACHE_DIR, ROOT

DEFAULT_API_CACHE_DIR: Path = CACHE_DIR / "api"
API_CACHE_ENV_VAR = "API_CACHE_DIR"
DEFAULT_DATA_DIR: Path = ROOT / "apps" / "web" / "public" / "data"

PILOT_SITES: tuple[dict[str, Any], ...] = (
    {
        "id": "sergipe_agreste_itabaiana",
        "name": "Itabaiana (Agreste)",
        "zone": "Agreste",
        "state": "SE",
        "lat": -10.685,
        "lon": -37.425,
        "radius_km": 5.0,
    },
    {
        "id": "sergipe_semiarido_ns_gloria",
        "name": "Nossa Senhora da Glória (Semiárido)",
        "zone": "Semiárido",
        "state": "SE",
        "lat": -10.218,
        "lon": -37.42,
        "radius_km": 5.0,
    },
)


def round_coord(value: float) -> float:
    """Round coordinate to 2 decimal places (0.01°), normalizing -0.0 to 0.0."""
    rounded = round(float(value), 2)
    return 0.0 if rounded == 0.0 else rounded


def format_coord_001(value: float) -> str:
    """Format coordinate rounded to 2 decimal places as a 2-decimal string."""
    return f"{round_coord(value):.2f}"


def coord_cache_key(lat: float, lon: float) -> str:
    """Canonical cache key for a coordinate pair rounded to 0.01°."""
    return f"{format_coord_001(lat)},{format_coord_001(lon)}"


coord_key = coord_cache_key


def coord_cache_key_variants(lat: float, lon: float) -> tuple[str, ...]:
    """Generate coordinate key variants using standard round and Decimal ROUND_HALF_UP / ROUND_HALF_EVEN."""
    primary = coord_cache_key(lat, lon)

    def _variants_for_val(val: float) -> list[str]:
        p = format_coord_001(val)
        res = [p]
        d = Decimal(f"{float(val):.6f}")
        for mode in (ROUND_HALF_UP, ROUND_HALF_EVEN):
            q = d.quantize(Decimal("0.01"), rounding=mode)
            s = "0.00" if (q == Decimal("-0.00") or q == Decimal("0.00")) else f"{q:.2f}"
            if s not in res:
                res.append(s)
        return res

    lat_vars = _variants_for_val(lat)
    lon_vars = _variants_for_val(lon)
    keys = [primary]
    for la in lat_vars:
        for lo in lon_vars:
            k = f"{la},{lo}"
            if k not in keys:
                keys.append(k)
    return tuple(keys)


def build_cache_key(source: str, lat: float, lon: float, period: str | None = None, *extra: str) -> str:
    """Build the canonical AD-7 cache key (source, lat/lon rounded to 0.01°, period)."""
    base = f"{source}:{coord_cache_key(lat, lon)}"
    if period and period.strip():
        base = f"{base}:{period.strip()}"
    for part in extra:
        if part and str(part).strip():
            base = f"{base}:{str(part).strip()}"
    return base


def resolve_api_cache_dir(
    cache_dir: Path | str | None = None,
    data_dir: Path | str | None = None,
) -> Path:
    """Resolve API cache directory following precedence rules."""
    if cache_dir is not None:
        return Path(cache_dir)
    env_dir = os.environ.get(API_CACHE_ENV_VAR)
    if env_dir and env_dir.strip():
        return Path(env_dir.strip())
    if data_dir is not None and Path(data_dir).resolve() != DEFAULT_DATA_DIR.resolve():
        return Path(data_dir) / ".api_cache"
    return DEFAULT_API_CACHE_DIR


def _coord_file_stem(ck: str) -> str:
    return ck.replace(",", "_")


def _rec_entry_key(
    crop: str,
    priority: str,
    season: str | None = None,
    previous_crops: Sequence[str] = (),
) -> str:
    return f"{crop}:{priority}:{season or ''}:{','.join(previous_crops)}"


def _atomic_write_json(file_path: Path, data: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False)
    temp_file = file_path.with_suffix(f".tmp.{os.getpid()}")
    try:
        temp_file.write_text(content, encoding="utf-8")
        temp_file.replace(file_path)
    except Exception:
        if temp_file.is_file():
            try:
                temp_file.unlink()
            except OSError:
                pass
        file_path.write_text(content, encoding="utf-8")


def write_recommendation_cache(
    cache_dir: Path,
    lat: float,
    lon: float,
    crop: str,
    priority: str,
    recommendation_dict: dict[str, Any],
    explanations: dict[str, str],
    season: str | None = None,
    previous_crops: Sequence[str] = (),
    alias_variants: bool = False,
) -> Path:
    """Store recommendation result in language-neutral format with multi-language explanations (AD-7, AD-9)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    ck = coord_cache_key(lat, lon)
    entry_key = _rec_entry_key(crop, priority, season, previous_crops)

    stem = _coord_file_stem(ck)
    primary_path = cache_dir / f"recommendation_{stem}.json"
    payload: dict[str, Any] = {}
    if primary_path.is_file():
        try:
            existing = json.loads(primary_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                payload = existing
        except (OSError, ValueError):
            payload = {}

    entries = payload.setdefault("entries", {})
    entries[entry_key] = {
        "recommendation": recommendation_dict,
        "explanations": dict(explanations),
    }

    period_str = ""
    diag = recommendation_dict.get("diagnosis", {})
    if diag.get("period_start") and diag.get("period_end"):
        period_str = f"{diag['period_start']}..{diag['period_end']}"

    payload["cache_key"] = build_cache_key("recommendation", lat, lon, period_str)
    payload["coord_key"] = ck
    payload["point"] = {"lat": round_coord(lat), "lon": round_coord(lon)}
    payload["source"] = "recommendation"
    if period_str:
        payload["period"] = period_str
    payload["entries"] = entries

    _atomic_write_json(primary_path, payload)

    if alias_variants:
        for variant_ck in coord_cache_key_variants(lat, lon):
            if variant_ck != ck:
                var_stem = _coord_file_stem(variant_ck)
                var_path = cache_dir / f"recommendation_{var_stem}.json"
                var_payload = copy.deepcopy(payload)
                var_payload["coord_key"] = variant_ck
                v_lat_str, v_lon_str = variant_ck.split(",")
                var_payload["point"] = {"lat": float(v_lat_str), "lon": float(v_lon_str)}
                var_payload["cache_key"] = f"recommendation:{variant_ck}" + (f":{period_str}" if period_str else "")
                _atomic_write_json(var_path, var_payload)

    return primary_path


def read_recommendation_cache(
    cache_dir: Path,
    lat: float,
    lon: float,
    crop: str,
    priority: str,
    lang: Literal["en", "pt-BR"] = "en",
    season: str | None = None,
    previous_crops: Sequence[str] = (),
    allow_default_fallback: bool = True,
) -> dict[str, Any] | None:
    """Read cached recommendation matching coordinates and parameters (with default entry fallback)."""
    payload: dict[str, Any] | None = None
    for variant_ck in coord_cache_key_variants(lat, lon):
        var_stem = _coord_file_stem(variant_ck)
        var_path = cache_dir / f"recommendation_{var_stem}.json"
        if var_path.is_file():
            try:
                data = json.loads(var_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "entries" in data:
                    payload = data
                    break
            except (OSError, ValueError):
                continue

    if payload is None:
        return None

    entries = payload.get("entries", {})
    exact_key = _rec_entry_key(crop, priority, season, previous_crops)
    entry = entries.get(exact_key)
    fell_back = False

    if entry is None and allow_default_fallback:
        default_key = _rec_entry_key(crop, priority, None, ())
        entry = entries.get(default_key)
        fell_back = True

    if entry is None or not isinstance(entry, dict):
        return None

    rec_dict = copy.deepcopy(entry.get("recommendation", {}))
    plot_dict = rec_dict.setdefault("plot", {})
    if fell_back:
        if season is not None:
            plot_dict["season"] = season
        if previous_crops:
            plot_dict["previous_crops"] = list(previous_crops)

    explanations = entry.get("explanations", {})
    explanation = explanations.get(lang) or explanations.get("en") or ""

    return {
        "recommendation": rec_dict,
        "explanation": explanation,
        "lang": lang,
    }


def write_diagnosis_cache(
    cache_dir: Path,
    lat: float,
    lon: float,
    response_dict: dict[str, Any],
    alias_variants: bool = False,
) -> Path:
    """Store diagnosis response on disk under 0.01° grid cache key (AD-7)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    ck = coord_cache_key(lat, lon)
    stem = _coord_file_stem(ck)
    primary_path = cache_dir / f"diagnosis_{stem}.json"

    period_str = ""
    summary = response_dict.get("summary", {})
    p_start = summary.get("period_start")
    p_end = summary.get("period_end")
    if p_start and p_end:
        period_str = f"{p_start}..{p_end}"

    payload: dict[str, Any] = {
        "cache_key": build_cache_key("diagnosis", lat, lon, period_str),
        "coord_key": ck,
        "point": {"lat": round_coord(lat), "lon": round_coord(lon)},
        "source": "diagnosis",
        "period": period_str,
        "response": response_dict,
    }

    _atomic_write_json(primary_path, payload)

    if alias_variants:
        for variant_ck in coord_cache_key_variants(lat, lon):
            if variant_ck != ck:
                var_stem = _coord_file_stem(variant_ck)
                var_path = cache_dir / f"diagnosis_{var_stem}.json"
                var_payload = copy.deepcopy(payload)
                var_payload["coord_key"] = variant_ck
                v_lat_str, v_lon_str = variant_ck.split(",")
                var_payload["point"] = {"lat": float(v_lat_str), "lon": float(v_lon_str)}
                var_payload["cache_key"] = f"diagnosis:{variant_ck}" + (f":{period_str}" if period_str else "")
                _atomic_write_json(var_path, var_payload)

    return primary_path


def read_diagnosis_cache(cache_dir: Path, lat: float, lon: float) -> dict[str, Any] | None:
    """Read cached diagnosis response matching coordinates across key variants."""
    for variant_ck in coord_cache_key_variants(lat, lon):
        var_stem = _coord_file_stem(variant_ck)
        var_path = cache_dir / f"diagnosis_{var_stem}.json"
        if var_path.is_file():
            try:
                data = json.loads(var_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "response" in data:
                    return copy.deepcopy(data["response"])
            except (OSError, ValueError):
                continue
    return None


def load_pilot_sites(data_dir: Path | None = None) -> tuple[dict[str, Any], ...]:
    """Load pilot sites GeoJSON or fallback to constant PILOT_SITES."""
    resolved_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    pilots_geojson = resolved_dir / "sergipe" / "pilots.geojson"
    if pilots_geojson.is_file():
        try:
            data = json.loads(pilots_geojson.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                features = data.get("features", [])
                loaded: list[dict[str, Any]] = []
                for feat in features:
                    props = feat.get("properties") or {}
                    coords = feat.get("geometry", {}).get("coordinates") or []
                    p_lat = props.get("lat") if props.get("lat") is not None else (coords[1] if len(coords) >= 2 else None)
                    p_lon = props.get("lon") if props.get("lon") is not None else (coords[0] if len(coords) >= 2 else None)
                    p_id = feat.get("id") or props.get("id")
                    if p_id and p_lat is not None and p_lon is not None:
                        loaded.append({
                            "id": str(p_id),
                            "name": props.get("name") or str(p_id),
                            "zone": props.get("zone", ""),
                            "state": props.get("state", "SE"),
                            "lat": float(p_lat),
                            "lon": float(p_lon),
                            "radius_km": float(props.get("radius_km", 5.0)),
                        })
                if loaded:
                    return tuple(loaded)
        except Exception:
            pass
    return PILOT_SITES


def _cached_projection_if_available(
    lat: float,
    lon: float,
    forecast_cache_dir: Path | str | None,
    fallback_date: str,
) -> Any:
    """Build Projection domain model from existing Open-Meteo cache without making network calls."""
    from apps.api.forecast import (
        OPEN_METEO_DATASET,
        OPEN_METEO_NOTICE,
        OPEN_METEO_SOURCE_ID,
        OPEN_METEO_URL,
        PeriodSchema,
        SourceAttributionResponse,
        _build_projection_summary,
        _derive_daily_records,
        resolve_forecast_cache_dir,
    )
    from src.data import open_meteo
    from src.engine.model import Projection, SourceAttribution

    source_attr = SourceAttribution(
        source=OPEN_METEO_SOURCE_ID,
        dataset=OPEN_METEO_DATASET,
        nasa=False,
        url=OPEN_METEO_URL,
        doi=None,
        notice=OPEN_METEO_NOTICE,
    )

    resolved_fdir = resolve_forecast_cache_dir(forecast_cache_dir)
    params = open_meteo.build_params(
        lat=lat,
        lon=lon,
        variables=list(open_meteo.DEFAULT_VARIABLES),
        forecast_days=15,
        model="best_match",
    )
    c_path = open_meteo.cache_path(resolved_fdir, params)
    s_path = open_meteo.stale_cache_path(resolved_fdir, params)

    payload: dict[str, Any] | None = None
    if c_path.is_file():
        payload = open_meteo._read_cache_file(c_path)
    if payload is None and s_path.is_file():
        payload = open_meteo._read_cache_file(s_path)

    if payload is not None:
        try:
            frame = open_meteo.parse_response(payload)
            daily_records, _ = _derive_daily_records(frame)
            period_schema = PeriodSchema(
                start=frame.index.min().strftime("%Y-%m-%d"),
                end=frame.index.max().strftime("%Y-%m-%d"),
            )
            source_attr_resp = SourceAttributionResponse(
                source=OPEN_METEO_SOURCE_ID,
                dataset=OPEN_METEO_DATASET,
                nasa=False,
                url=OPEN_METEO_URL,
                doi=None,
                notice=OPEN_METEO_NOTICE,
            )
            summary = _build_projection_summary(daily_records, period_schema, source_attr_resp)
            return Projection(
                period_start=summary.period_start,
                period_end=summary.period_end,
                horizon_days=summary.horizon_days,
                available=True,
                rain_total_mm=summary.rain_total_mm,
                rain_daily_mean_mm=summary.rain_daily_mean_mm,
                temperature_mean_c=summary.temperature_mean_c,
                temperature_max_c=summary.temperature_max_c,
                et0_daily_mean_mm=summary.et0_daily_mean_mm,
                water_balance_mm=summary.water_balance_mm,
                sources=(source_attr,),
            )
        except Exception:
            pass

    return Projection(
        period_start=fallback_date,
        period_end=fallback_date,
        horizon_days=15,
        available=False,
        sources=(source_attr,),
    )


def prewarm_pilots(
    cache_dir: Path | str | None = None,
    data_dir: Path | str | None = None,
    forecast_cache_dir: Path | str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Pre-warm API cache for Sergipe pilot sites across all 3 crops and 4 priorities (AD-7)."""
    target_cache_dir = resolve_api_cache_dir(cache_dir, data_dir=data_dir)
    resolved_data_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    sergipe_dir = resolved_data_dir / "sergipe"

    if not sergipe_dir.is_dir():
        return {
            "cache_dir": str(target_cache_dir),
            "prewarmed": False,
            "pilots": [],
            "coord_keys": [],
        }

    from apps.api.diagnosis import build_diagnosis_response, build_engine_diagnosis
    from apps.api.recommendation import _zarc_table
    from src.engine.model import Crop, Priority
    from src.engine.recommend import recommend
    from src.engine.rules import load_rules
    from src.explain.template import explain

    try:
        rules = load_rules()
    except Exception:
        return {
            "cache_dir": str(target_cache_dir),
            "prewarmed": False,
            "pilots": [],
            "coord_keys": [],
        }

    zarc = _zarc_table()
    pilot_sites = load_pilot_sites(resolved_data_dir)
    prewarmed_pilots: list[dict[str, Any]] = []
    coord_keys: list[str] = []

    try:
        target_cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return {}

    for pilot in pilot_sites:
        p_lat = float(pilot["lat"])
        p_lon = float(pilot["lon"])
        p_radius = float(pilot.get("radius_km", 5.0))
        ck = coord_cache_key(p_lat, p_lon)
        stem = _coord_file_stem(ck)
        if ck not in coord_keys:
            coord_keys.append(ck)

        diag_path = target_cache_dir / f"diagnosis_{stem}.json"
        rec_path = target_cache_dir / f"recommendation_{stem}.json"

        # Check if already cached
        if not force and diag_path.is_file() and rec_path.is_file():
            try:
                rec_data = json.loads(rec_path.read_text(encoding="utf-8"))
                entries = rec_data.get("entries", {})
                all_combinations_present = True
                for c in Crop:
                    for p in Priority:
                        k = _rec_entry_key(c.value, p.value, None, ())
                        if k not in entries:
                            all_combinations_present = False
                            break
                    if not all_combinations_present:
                        break
                if all_combinations_present:
                    prewarmed_pilots.append({**pilot, "status": "cached", "coord_key": ck})
                    continue
            except (OSError, ValueError):
                pass

        try:
            diag_resp = build_diagnosis_response(
                lat=p_lat,
                lon=p_lon,
                radius_km=p_radius,
                data_dir=resolved_data_dir,
                cache_dir=target_cache_dir,
            )
            write_diagnosis_cache(target_cache_dir, p_lat, p_lon, diag_resp.model_dump(), alias_variants=True)

            engine_plot, engine_diagnosis = build_engine_diagnosis(
                lat=p_lat,
                lon=p_lon,
                radius_km=p_radius,
                data_dir=resolved_data_dir,
                cache_dir=target_cache_dir,
            )

            projection = _cached_projection_if_available(
                lat=p_lat,
                lon=p_lon,
                forecast_cache_dir=forecast_cache_dir,
                fallback_date=engine_diagnosis.period_end,
            )

            for c in Crop:
                for p in Priority:
                    rec_result = recommend(
                        plot=engine_plot,
                        diagnosis=engine_diagnosis,
                        projection=projection,
                        crop=c,
                        priority=p,
                        rules=rules,
                        zarc=zarc,
                    )
                    explanations = {
                        "en": explain(rec_result, "en"),
                        "pt-BR": explain(rec_result, "pt-BR"),
                    }
                    write_recommendation_cache(
                        cache_dir=target_cache_dir,
                        lat=p_lat,
                        lon=p_lon,
                        crop=c.value,
                        priority=p.value,
                        recommendation_dict=rec_result.to_dict(),
                        explanations=explanations,
                        alias_variants=True,
                    )

            prewarmed_pilots.append({**pilot, "status": "computed", "coord_key": ck})
        except Exception as exc:
            prewarmed_pilots.append({**pilot, "status": "error", "error": str(exc), "coord_key": ck})

    return {
        "cache_dir": str(target_cache_dir),
        "prewarmed": True,
        "pilots": prewarmed_pilots,
        "coord_keys": coord_keys,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pre-warm Field Shift API cache for pilot sites.")
    parser.add_argument("--cache-dir", type=Path, default=None, help="Directory to store API cache files.")
    parser.add_argument("--force", action="store_true", help="Force recomputation of pilot cache entries.")
    args = parser.parse_args()

    summary = prewarm_pilots(cache_dir=args.cache_dir, force=args.force)
    print(json.dumps(summary, indent=2))
