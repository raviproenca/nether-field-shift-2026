# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Standard error schemas, exceptions, and handlers for the product API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

HTTP_STATUS_TO_ERROR_CODE: dict[int, str] = {
    400: "invalid_parameter",
    404: "not_found",
    422: "no_data",
    502: "upstream_error",
    503: "server_not_configured",
    504: "upstream_timeout",
}


class ErrorBody(BaseModel):
    """Structured error payload details."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Root error envelope returned by all API error responses."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


class APIError(Exception):
    """Application-level exception with explicit HTTP status and error code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_json_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Build a standard JSONResponse matching ErrorResponse."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI application."""

    @app.exception_handler(APIError)
    async def handle_api_error(_request: Request, exc: APIError) -> JSONResponse:
        return error_json_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors: list[dict[str, Any]] = exc.errors()
        if errors:
            first_err = errors[0]
            raw_loc = [str(x) for x in first_err.get("loc", ())]
            filtered_loc = [x for x in raw_loc if x not in {"query", "path", "body"}]
            param_name = filtered_loc[-1] if filtered_loc else (raw_loc[-1] if raw_loc else "parameter")
            err_msg = str(first_err.get("msg", "invalid value")).rstrip(".")
            message = f"Invalid parameter '{param_name}': {err_msg}."
        else:
            message = "Invalid request parameter."
        return error_json_response(400, "invalid_parameter", message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = HTTP_STATUS_TO_ERROR_CODE.get(exc.status_code, "internal_error")
        return error_json_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled internal server error: %s", exc)
        return error_json_response(500, "internal_error", "Internal server error.")
