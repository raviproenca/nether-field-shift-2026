# AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
"""POST /recommendation: assemble engine inputs, run the engine, add template text."""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from apps.api.diagnosis import build_engine_diagnosis
from apps.api.errors import APIError
from apps.api.forecast import build_engine_projection
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
    previous_crops: list[str] = Field(default_factory=list)
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
) -> RecommendationResponse:
    """Run diagnosis, forecast and engine for one plot; the text is the fixed template."""
    plot, diagnosis = build_engine_diagnosis(
        lat=request.lat,
        lon=request.lon,
        radius_km=request.radius_km,
        data_dir=data_dir,
    )
    plot = replace(
        plot,
        season=request.season if request.season is not None else plot.season,
        previous_crops=tuple(request.previous_crops) or plot.previous_crops,
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
    return RecommendationResponse(
        recommendation=result.to_dict(),
        explanation=explain(result, request.lang),
        lang=request.lang,
    )
