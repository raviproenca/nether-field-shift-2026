# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Unit tests for the FastAPI product API skeleton (apps/api).

Validates:
- GET /health endpoint (status, version, UTC ISO-8601 timestamp).
- GET /sources catalog endpoint (NASA and non-NASA attribution, variables).
- Query filtering for /sources (nasa, kind, id).
- Uniform error responses (400 invalid_parameter, 404 not_found, 500 internal_error).
- CORS configuration from environment variables (API_CORS_ORIGINS, DASHBOARD_ORIGIN).
"""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from apps.api.main import API_VERSION, app, create_app


def test_health_returns_ok_version_and_utc_timestamp() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert body.get("status") == "ok"
    assert body.get("version") == API_VERSION

    time_str = body.get("time")
    assert isinstance(time_str, str)
    assert time_str.endswith("Z")
    parsed_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    assert parsed_time.tzinfo is not None


def test_sources_returns_catalog_with_nasa_and_non_nasa_attribution() -> None:
    client = TestClient(app)
    response = client.get("/sources")
    assert response.status_code == 200

    body = response.json()
    assert "sources" in body
    sources = body["sources"]

    expected_ids = {
        "power",
        "gldas",
        "imerg",
        "smap",
        "modis",
        "viirs",
        "hls",
        "srtm",
        "planetary",
    }
    source_ids = {s["id"] for s in sources}
    assert expected_ids.issubset(source_ids)

    for source in sources:
        variables = source.get("variables", [])
        assert len(variables) > 0
        for var in variables:
            assert isinstance(var.get("name"), str) and var["name"]
            assert isinstance(var.get("long_name"), str) and var["long_name"]
            assert "unit" in var

        attribution = source.get("attribution", {})
        assert isinstance(attribution.get("url"), str)
        assert attribution["url"].startswith("http")

        if source["id"] == "planetary":
            assert source.get("nasa") is False
            notice = attribution.get("notice", "")
            assert isinstance(notice, str) and "Not NASA" in notice
        else:
            assert source.get("nasa") is True


def test_sources_filters_by_nasa_kind_and_id() -> None:
    client = TestClient(app)

    # Filter by nasa=false -> returns only planetary
    res_nasa = client.get("/sources?nasa=false")
    assert res_nasa.status_code == 200
    nasa_sources = res_nasa.json()["sources"]
    assert [s["id"] for s in nasa_sources] == ["planetary"]

    # Filter by kind=static -> returns only srtm
    res_kind = client.get("/sources?kind=static")
    assert res_kind.status_code == 200
    kind_sources = res_kind.json()["sources"]
    assert [s["id"] for s in kind_sources] == ["srtm"]

    # Filter by id=power -> returns only power
    res_id = client.get("/sources?id=power")
    assert res_id.status_code == 200
    id_sources = res_id.json()["sources"]
    assert [s["id"] for s in id_sources] == ["power"]


@pytest.mark.parametrize(
    "path",
    [
        "/health?unexpected=1",
        "/sources?foo=bar",
        "/sources?nasa=not-a-bool",
        "/sources?kind=unknown",
        "/sources?id=unknown_source",
        "/sources?id=",
    ],
)
def test_invalid_parameters_return_400_with_standard_error_shape(path: str) -> None:
    client = TestClient(app)
    response = client.get(path)
    assert response.status_code == 400

    body = response.json()
    assert set(body.keys()) == {"error"}
    error = body["error"]
    assert set(error.keys()) == {"code", "message"}
    assert error["code"] == "invalid_parameter"
    assert isinstance(error["message"], str) and len(error["message"]) > 0


def test_not_found_and_internal_error_return_standard_error_shape() -> None:
    client = TestClient(app)

    # 404 Not Found
    res_404 = client.get("/does-not-exist")
    assert res_404.status_code == 404
    body_404 = res_404.json()
    assert set(body_404.keys()) == {"error"}
    error_404 = body_404["error"]
    assert set(error_404.keys()) == {"code", "message"}
    assert error_404["code"] == "not_found"
    assert isinstance(error_404["message"], str) and bool(error_404["message"])

    # 500 Internal Server Error
    test_app = create_app()

    @test_app.get("/_boom")
    def _boom() -> None:
        raise RuntimeError("internal secret traceback")

    boom_client = TestClient(test_app, raise_server_exceptions=False)
    res_500 = boom_client.get("/_boom")
    assert res_500.status_code == 500
    assert res_500.json() == {
        "error": {
            "code": "internal_error",
            "message": "Internal server error.",
        }
    }
    assert "internal secret traceback" not in res_500.text


def test_cors_reads_allowed_origin_from_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 1. Cleared environment: defaults to localhost:5173
    for var in (
        "API_CORS_ORIGINS",
        "DASHBOARD_ORIGIN",
        "CORS_ALLOWED_ORIGINS",
        "CORS_ORIGIN",
    ):
        monkeypatch.delenv(var, raising=False)

    client_default = TestClient(create_app())
    res_default = client_default.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert res_default.status_code == 200
    assert (
        res_default.headers.get("access-control-allow-origin")
        == "http://localhost:5173"
    )

    # 2. Configured via API_CORS_ORIGINS comma-separated list
    monkeypatch.setenv(
        "API_CORS_ORIGINS",
        "https://dashboard.example.org, https://preview.example.org",
    )
    client_custom = TestClient(create_app())

    # Preflight OPTIONS request
    preflight = client_custom.options(
        "/sources",
        headers={
            "Origin": "https://dashboard.example.org",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 200
    assert (
        preflight.headers.get("access-control-allow-origin")
        == "https://dashboard.example.org"
    )

    # GET with second allowed origin
    get_res = client_custom.get(
        "/sources",
        headers={"Origin": "https://preview.example.org"},
    )
    assert get_res.status_code == 200
    assert (
        get_res.headers.get("access-control-allow-origin")
        == "https://preview.example.org"
    )

    # GET with disallowed origin
    evil_res = client_custom.get(
        "/sources",
        headers={"Origin": "https://evil.example.net"},
    )
    assert "access-control-allow-origin" not in evil_res.headers

    # 3. Fallback to DASHBOARD_ORIGIN
    monkeypatch.delenv("API_CORS_ORIGINS", raising=False)
    monkeypatch.setenv("DASHBOARD_ORIGIN", "https://panel.sergipe.example.org")
    client_fallback = TestClient(create_app())
    res_fallback = client_fallback.get(
        "/health",
        headers={"Origin": "https://panel.sergipe.example.org"},
    )
    assert res_fallback.status_code == 200
    assert (
        res_fallback.headers.get("access-control-allow-origin")
        == "https://panel.sergipe.example.org"
    )
