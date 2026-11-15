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


def build(lat: float, lon: float, code: str, crop: Crop, priority: Priority, lang: str) -> dict:
    plot, diagnosis = build_engine_diagnosis(lat=lat, lon=lon, radius_km=5.0)
    plot = replace(plot, municipality_code=code)
    projection = build_engine_projection(lat=lat, lon=lon, forecast_days=15)
    result = recommend(plot, diagnosis, projection, crop, priority, load_rules(), zarc=load_zarc_table())
    return {
        "recommendation": result.to_dict(),
        "explanation": explain(result, lang),
        "lang": lang,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main() -> int:
    if load_zarc_table() is None:
        print("error: no ZARC CSV in data/processed/; run python -m src.data.zarc first", file=sys.stderr)
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for pilot_id, lat, lon, code, crop, priority in PILOTS:
        for lang, suffix in (("en", ""), ("pt-BR", ".pt-BR")):
            path = OUT_DIR / f"{pilot_id}{suffix}.json"
            path.write_text(json.dumps(build(lat, lon, code, crop, priority, lang), indent=2) + "\n", encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
