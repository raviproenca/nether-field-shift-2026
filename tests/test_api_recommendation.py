# AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
"""Tests for POST /recommendation (schema validity, error envelope, forecast fallback)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from apps.api import recommendation as recommendation_module
from apps.api.main import create_app
from src.engine.model import Projection

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "docs" / "data-format"
REC_SCHEMA = json.loads((SCHEMAS_DIR / "recommendation.schema.json").read_text(encoding="utf-8"))
REGISTRY = Registry().with_resources(
    (path.name, Resource.from_contents(json.loads(path.read_text(encoding="utf-8"))))
    for path in SCHEMAS_DIR.glob("*.schema.json")
)

VALID_BODY = {
    "lat": -10.685,
    "lon": -37.425,
    "radius_km": 5.0,
    "crop": "maize",
    "priority": "water",
    "previous_crops": ["beans"],
}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    def fake_projection(**kwargs: object) -> Projection:
        return Projection(
            period_start="2026-11-15",
            period_end="2026-11-30",
            horizon_days=15,
            available=False,
        )

    monkeypatch.setattr(recommendation_module, "build_engine_projection", fake_projection)
    return TestClient(create_app())


def test_valid_request_matches_schema_and_has_text(client: TestClient) -> None:
    response = client.post("/recommendation", json=VALID_BODY)

    assert response.status_code == 200
    body = response.json()
    Draft202012Validator(REC_SCHEMA, registry=REGISTRY).validate(body["recommendation"])
    assert len(body["recommendation"]["strategies"]) >= 3
    assert body["recommendation"]["plot"]["previous_crops"] == ["beans"]
    assert body["lang"] == "en"
    assert body["explanation"].strip()


def test_portuguese_text_on_request(client: TestClient) -> None:
    response = client.post("/recommendation", json={**VALID_BODY, "lang": "pt-BR"})

    assert response.status_code == 200
    assert "Incerteza:" in response.json()["explanation"]


@pytest.mark.parametrize(
    "patch",
    [
        {"crop": "wheat"},
        {"priority": "fun"},
        {"lat": "north"},
        {"lang": "fr"},
        {"unknown_field": 1},
    ],
)
def test_invalid_body_returns_error_envelope(client: TestClient, patch: dict) -> None:
    response = client.post("/recommendation", json={**VALID_BODY, **patch})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_parameter"


def test_missing_field_returns_error_envelope(client: TestClient) -> None:
    body = {k: v for k, v in VALID_BODY.items() if k != "crop"}
    response = client.post("/recommendation", json=body)

    assert response.status_code == 400
    assert "crop" in response.json()["error"]["message"]


def test_location_outside_sergipe_returns_422(client: TestClient) -> None:
    response = client.post("/recommendation", json={**VALID_BODY, "lat": -23.5, "lon": -46.6})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "no_data"


def test_zarc_note_reaches_the_response(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import pandas as pd

    from src.engine.zarc_check import DECENDIO_COLUMNS

    row = {"Nome_cultura": "Milho 1ª Safra", "geocodigo": "2802908"}
    row.update({column: (20 if 10 <= number <= 19 else 0) for number, column in enumerate(DECENDIO_COLUMNS, start=1)})
    monkeypatch.setattr(recommendation_module, "_zarc_table", lambda: pd.DataFrame([row]))

    note = client.post("/recommendation", json=VALID_BODY).json()["recommendation"]["validation_note"]

    assert "ZARC" in note and "could not be done" not in note
