# AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
"""Pre-compute the demo Recommendations for the two pilots into apps/web/public/demo/.

The dashboard demo mode reads these static files, so judges see a complete result
without waiting for the API. Run it again to refresh them (needs the network for the
15-day forecast; the ZARC CSVs in data/processed/ come from ``python -m src.data.zarc``):

    python scripts/build_demo_cache.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.api.diagnosis import build_engine_diagnosis  # noqa: E402
from apps.api.forecast import build_engine_projection  # noqa: E402
from src.engine.model import Crop, Priority  # noqa: E402
from src.engine.recommend import recommend  # noqa: E402
from src.engine.rules import load_rules  # noqa: E402
from src.engine.zarc_check import load_zarc_table  # noqa: E402
from src.explain.template import explain  # noqa: E402

OUT_DIR = ROOT / "apps" / "web" / "public" / "demo"

# (pilot id as in pilots.geojson, lat, lon, IBGE municipality code, crop, priority)
PILOTS = (
    ("sergipe_agreste_itabaiana", -10.685, -37.425, "2802908", Crop.MAIZE, Priority.WATER),
    ("sergipe_semiarido_ns_gloria", -10.218, -37.42, "2804508", Crop.MAIZE, Priority.WATER),
)


def inputs(lat: float, lon: float, code: str):
    """Engine inputs for one pilot, built once and reused for every crop and priority."""
    plot, diagnosis = build_engine_diagnosis(lat=lat, lon=lon, radius_km=5.0)
    plot = replace(plot, municipality_code=code)
    projection = build_engine_projection(lat=lat, lon=lon, forecast_days=15)
    return plot, diagnosis, projection


def build(plot, diagnosis, projection, crop: Crop, priority: Priority, lang: str) -> dict:
    result = recommend(plot, diagnosis, projection, crop, priority, load_rules(), zarc=load_zarc_table())
    return {
        "recommendation": result.to_dict(),
        "explanation": explain(result, lang),
        "lang": lang,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if load_zarc_table() is None:
        print("error: no ZARC CSV in data/processed/; run python -m src.data.zarc first", file=sys.stderr)
        return 2
    for pilot_id, lat, lon, code, default_crop, default_priority in PILOTS:
        plot, diagnosis, projection = inputs(lat, lon, code)
        for lang, suffix in (("en", ""), ("pt-BR", ".pt-BR")):
            # Every crop and priority, so the dashboard can switch them instantly without the API.
            for crop in Crop:
                for priority in Priority:
                    payload = build(plot, diagnosis, projection, crop, priority, lang)
                    write(OUT_DIR / pilot_id / f"{crop.value}-{priority.value}{suffix}.json", payload)
                    if crop is default_crop and priority is default_priority:
                        write(OUT_DIR / f"{pilot_id}{suffix}.json", payload)  # the default view
            print(f"wrote demo files for {pilot_id} ({lang})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
