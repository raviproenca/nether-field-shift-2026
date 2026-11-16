# AI-assisted: generated with Claude Code & Antigravity, reviewed by Periélio & Lucas Feitosa
"""POST /recommendation: assemble engine inputs, run the engine, add template text."""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict

from apps.api.cache import (
    read_recommendation_cache,
    resolve_api_cache_dir,
    write_recommendation_cache,
)
from apps.api.diagnosis import _validate_diagnosis_params, build_engine_diagnosis
from apps.api.errors import APIError
from apps.api.forecast import build_engine_projection
from src.data.errors import RemoteDataError
from src.engine.model import Crop, Priority
from src.engine.recommend import recommend
from src.engine.rules import load_rules
from src.engine.zarc_check import load_zarc_table
from src.explain.template import explain

FORECAST_DAYS = 15


class RecommendationRequest(BaseModel):
    """Plot location and farmer inputs defined by the engine (#44)."""

    model_config = ConfigDict(extra="forbid")

    lat: float
    lon: float
    radius_km: float = 5.0
    crop: Crop
    priority: Priority
    season: str | None = None
    previous_crops: list[str] | None = None
    lang: Literal["en", "pt-BR"] = "en"


class RecommendationResponse(BaseModel):
    """Structured Recommendation (recommendation.schema.json) plus template text."""

    model_config = ConfigDict(extra="forbid")

    recommendation: dict[str, Any]
    explanation: str
    lang: Literal["en", "pt-BR"]


@lru_cache(maxsize=1)
def _zarc_table() -> pd.DataFrame | None:
    """ZARC rows for Sergipe from data/processed/, read once; None when not downloaded."""
    return load_zarc_table()


def build_recommendation_response(
    request: RecommendationRequest,
    data_dir: Path | None = None,
    forecast_cache_dir: Path | None = None,
    cache_dir: Path | None = None,
) -> RecommendationResponse:
    """Run diagnosis, forecast and engine for one plot; the text is the fixed template."""
    _validate_diagnosis_params(request.lat, request.lon, request.radius_km)
    resolved_cache_dir = resolve_api_cache_dir(cache_dir, data_dir=data_dir)

    try:
        plot = None
        plot, diagnosis = build_engine_diagnosis(
            lat=request.lat,
            lon=request.lon,
            radius_km=request.radius_km,
            data_dir=data_dir,
            cache_dir=resolved_cache_dir,
        )
        plot = replace(
            plot,
            season=request.season if request.season is not None else plot.season,
            previous_crops=(
                tuple(request.previous_crops)
                if request.previous_crops is not None
                else plot.previous_crops
            ),
        )
        projection = build_engine_projection(
            lat=request.lat,
            lon=request.lon,
            forecast_days=FORECAST_DAYS,
            cache_dir=forecast_cache_dir,
        )
        try:
            rules = load_rules()
        except Exception as err:
            raise APIError(
                status_code=503,
                code="server_not_configured",
                message=f"Engine rules unavailable: {err}",
            ) from None
        result = recommend(
            plot=plot,
            diagnosis=diagnosis,
            projection=projection,
            crop=request.crop,
            priority=request.priority,
            rules=rules,
            zarc=_zarc_table(),
        )
        rec_dict = result.to_dict()
        explanations = {
            "en": explain(result, "en"),
            "pt-BR": explain(result, "pt-BR"),
        }
        try:
            write_recommendation_cache(
                cache_dir=resolved_cache_dir,
                lat=request.lat,
                lon=request.lon,
                crop=request.crop.value,
                priority=request.priority.value,
                recommendation_dict=rec_dict,
                explanations=explanations,
                season=request.season,
                previous_crops=plot.previous_crops,
            )
        except OSError:
            pass
        return RecommendationResponse(
            recommendation=rec_dict,
            explanation=explanations[request.lang],
            lang=request.lang,
        )
    except (APIError, RemoteDataError, OSError) as err:
        if isinstance(err, APIError) and err.status_code < 500:
            raise
        effective_previous_crops = request.previous_crops
        if effective_previous_crops is None and plot is not None:
            effective_previous_crops = plot.previous_crops
        cached = read_recommendation_cache(
            cache_dir=resolved_cache_dir,
            lat=request.lat,
            lon=request.lon,
            crop=request.crop.value,
            priority=request.priority.value,
            lang=request.lang,
            season=request.season,
            previous_crops=effective_previous_crops or (),
            allow_default_fallback=True,
        )
        if cached is not None:
            return RecommendationResponse(**cached)
        if isinstance(err, APIError):
            raise
        if isinstance(err, RemoteDataError):
            raise APIError(
                status_code=502,
                code="upstream_error",
                message=f"Upstream forecast unavailable: {err}",
            ) from err
        raise APIError(
            status_code=503,
            code="server_not_configured",
            message=f"Snapshot data unavailable: {err}",
        ) from err
