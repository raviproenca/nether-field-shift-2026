# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Main entry point, application factory, routing, and CORS configuration for the API."""

from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Query, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

from .cache import prewarm_pilots
from .diagnosis import DiagnosisResponse, build_diagnosis_response
from .errors import APIError, ErrorResponse, register_exception_handlers
from .forecast import ForecastResponse, build_forecast_response
from .recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    build_recommendation_response,
)
from .sources_catalog import (
    SOURCES_BY_ID,
    SOURCES_CATALOG,
    HealthResponse,
    SourcesResponse,
)

API_VERSION = "0.1.0"
DEFAULT_CORS_ORIGIN = "http://localhost:5173"
CORS_ENV_VARS = (
    "API_CORS_ORIGINS",
    "DASHBOARD_ORIGIN",
    "CORS_ALLOWED_ORIGINS",
    "CORS_ORIGIN",
)


def _normalize_origin(origin: str) -> str:
    """Strip whitespace and trailing slash unless wildcard."""
    cleaned = origin.strip()
    if not cleaned:
        return ""
    if cleaned == "*":
        return "*"
    return cleaned.rstrip("/")


def get_cors_origins(override: Sequence[str] | None = None) -> list[str]:
    """Resolve allowed CORS origins from an override or environment variables.

    When override is provided, entries are stripped, deduplicated, and empty items are dropped.
    Otherwise, environment variables ('API_CORS_ORIGINS', 'DASHBOARD_ORIGIN',
    'CORS_ALLOWED_ORIGINS', 'CORS_ORIGIN') are inspected in priority order until one with
    at least one non-empty origin is found. If none are configured, returns DEFAULT_CORS_ORIGIN.
    """
    if override is not None:
        result: list[str] = []
        for item in override:
            normalized = _normalize_origin(item)
            if normalized and normalized not in result:
                result.append(normalized)
        return result

    for env_var in CORS_ENV_VARS:
        raw_val = os.environ.get(env_var)
        if raw_val is not None:
            parsed: list[str] = []
            for part in raw_val.split(","):
                normalized = _normalize_origin(part)
                if normalized and normalized not in parsed:
                    parsed.append(normalized)
            if parsed:
                return parsed

    return [DEFAULT_CORS_ORIGIN]


class DynamicCORSMiddleware(CORSMiddleware):
    """CORS middleware supporting dynamic origin resolution from environment variables."""

    def __init__(
        self,
        app: ASGIApp,
        explicit_origins: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.explicit_origins = explicit_origins
        if explicit_origins is None:
            kwargs.pop("allow_origins", None)
            super().__init__(app, allow_origins=(), **kwargs)
        else:
            kwargs.setdefault("allow_origins", tuple(explicit_origins))
            super().__init__(app, **kwargs)

    def is_allowed_origin(self, origin: str) -> bool:
        if not origin:
            return False
        allowed = self.explicit_origins if self.explicit_origins is not None else get_cors_origins()
        if "*" in allowed:
            return True
        normalized = origin.rstrip("/")
        return any(normalized == o.rstrip("/") for o in allowed)


def _reject_unknown_query_params(request: Request, allowed: set[str]) -> None:
    """Validate that query parameters contain only allowed keys, raising 400 otherwise."""
    unknown = set(request.query_params.keys()) - allowed
    if unknown:
        sorted_unknown = sorted(unknown)
        if len(sorted_unknown) == 1:
            message = f"Unknown query parameter '{sorted_unknown[0]}'."
        else:
            message = f"Unknown query parameters: {', '.join(sorted_unknown)}."
        raise APIError(status_code=400, code="invalid_parameter", message=message)


def create_app(
    cors_origins: Sequence[str] | None = None,
    data_dir: Path | None = None,
    forecast_cache_dir: Path | None = None,
    api_cache_dir: Path | None = None,
    prewarm: bool = True,
) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    if prewarm:
        prewarm_pilots(
            cache_dir=api_cache_dir,
            data_dir=data_dir,
            forecast_cache_dir=forecast_cache_dir,
        )

    app_instance = FastAPI(
        title="Field Shift API",
        version=API_VERSION,
        description="Product API for Team Nether's Field Shift agronomic decision engine and NASA data toolkit.",
        responses={
            400: {"model": ErrorResponse, "description": "Invalid parameter / Bad Request"},
            404: {"model": ErrorResponse, "description": "Resource not found"},
            422: {"model": ErrorResponse, "description": "No data available for requested location"},
            500: {"model": ErrorResponse, "description": "Internal server error"},
            502: {"model": ErrorResponse, "description": "Upstream error from Open-Meteo"},
            503: {"model": ErrorResponse, "description": "Snapshot data unavailable or server not configured"},
            504: {"model": ErrorResponse, "description": "Upstream timeout"},
        },
    )

    register_exception_handlers(app_instance)

    explicit = list(get_cors_origins(cors_origins)) if cors_origins is not None else None
    app_instance.add_middleware(
        DynamicCORSMiddleware,
        explicit_origins=explicit,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app_instance.get("/health", response_model=HealthResponse)
    async def get_health(request: Request) -> HealthResponse:
        _reject_unknown_query_params(request, allowed=set())
        return HealthResponse(
            status="ok",
            version=API_VERSION,
            time=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    @app_instance.get("/sources", response_model=SourcesResponse)
    async def get_sources(
        request: Request,
        nasa: bool | None = Query(default=None),
        kind: Literal["timeseries", "raster", "static"] | None = Query(default=None),
        id: str | None = Query(default=None),
    ) -> SourcesResponse:
        _reject_unknown_query_params(request, allowed={"nasa", "kind", "id"})

        filtered = list(SOURCES_CATALOG)
        if id is not None:
            raw_id = id
            id = id.strip()
            if not id or id not in SOURCES_BY_ID:
                raise APIError(
                    status_code=400,
                    code="invalid_parameter",
                    message=f"Invalid parameter 'id': unknown source '{id or raw_id}'.",
                )
            filtered = [s for s in filtered if s.id == id]

        if nasa is not None:
            filtered = [s for s in filtered if s.nasa is nasa]

        if kind is not None:
            filtered = [s for s in filtered if s.kind == kind]

        return SourcesResponse(sources=filtered)

    @app_instance.get(
        "/diagnosis",
        response_model=DiagnosisResponse,
        responses={
            400: {"model": ErrorResponse, "description": "Invalid parameter / Bad Request"},
            422: {"model": ErrorResponse, "description": "No data available for requested location"},
            503: {"model": ErrorResponse, "description": "Snapshot data unavailable or server not configured"},
        },
    )
    async def get_diagnosis(
        request: Request,
        lat: float = Query(...),
        lon: float = Query(...),
        radius_km: float = Query(default=5.0),
    ) -> DiagnosisResponse:
        _reject_unknown_query_params(request, allowed={"lat", "lon", "radius_km"})
        return build_diagnosis_response(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            data_dir=data_dir,
            cache_dir=api_cache_dir,
        )

    @app_instance.get(
        "/forecast",
        response_model=ForecastResponse,
        responses={
            400: {"model": ErrorResponse, "description": "Invalid parameter / Bad Request"},
            422: {"model": ErrorResponse, "description": "No data returned for location"},
            502: {"model": ErrorResponse, "description": "Upstream error from Open-Meteo"},
            504: {"model": ErrorResponse, "description": "Upstream timeout"},
        },
    )
    async def get_forecast(
        request: Request,
        lat: float = Query(..., description="Latitude in degrees (-89.0 to 89.0)"),
        lon: float = Query(..., description="Longitude in degrees (-180.0 to 180.0)"),
        radius_km: float = Query(default=5.0, description="Plot radius in km (default 5.0)"),
        days: int | None = Query(default=None, description="Forecast horizon in days (1 to 16)"),
        forecast_days: int | None = Query(default=None, description="Alias for days (1 to 16)"),
        model: str = Query(default="best_match", description="Weather forecast model"),
        variables: str | None = Query(default=None, description="Comma-separated daily variables"),
    ) -> ForecastResponse:
        _reject_unknown_query_params(
            request,
            allowed={"lat", "lon", "radius_km", "days", "forecast_days", "model", "variables"},
        )
        return build_forecast_response(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            days=days,
            forecast_days=forecast_days,
            model=model,
            variables=variables,
            cache_dir=forecast_cache_dir,
        )

    @app_instance.post(
        "/recommendation",
        response_model=RecommendationResponse,
        responses={
            400: {"model": ErrorResponse, "description": "Invalid request body"},
            422: {"model": ErrorResponse, "description": "No data available for requested location"},
            503: {"model": ErrorResponse, "description": "Snapshot data or engine rules unavailable"},
        },
    )
    async def post_recommendation(body: RecommendationRequest) -> RecommendationResponse:
        return build_recommendation_response(
            body,
            data_dir=data_dir,
            forecast_cache_dir=forecast_cache_dir,
            cache_dir=api_cache_dir,
        )

    return app_instance


app = create_app()
