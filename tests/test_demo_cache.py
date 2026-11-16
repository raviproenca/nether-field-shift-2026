# AI-assisted: generated with Codex, reviewed by Ravi.
"""Saved demo files must not claim a rotation break when crop history is unknown."""

from __future__ import annotations

import json
from pathlib import Path


DEMO_DIR = Path(__file__).resolve().parents[1] / "apps" / "web" / "public" / "demo"


def test_saved_demos_with_unknown_history_have_no_pest_cycle_claims() -> None:
    paths = tuple(sorted(DEMO_DIR.rglob("*.json")))
    assert paths

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        recommendation = payload.get("recommendation", payload)
        plot = recommendation["plot"]
        if plot.get("previous_crops"):
            continue

        for strategy in recommendation["strategies"]:
            assert strategy["breaks_pest_cycle"] is False, path
            assert "history is unknown" in strategy["pest_cycle_note"].casefold(), path
            assert "cannot be assessed" in strategy["pest_cycle_note"].casefold(), path
