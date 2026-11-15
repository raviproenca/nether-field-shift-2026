# AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
"""IBGE municipality code of a point in Sergipe, from the IBGE municipal mesh.

The mesh is ``data/sample/ibge_se_municipalities.geojson`` (IBGE, malhas API v3,
state 28, lowest quality, 75 municipalities). A point on or outside the mesh has no code.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.data.paths import ROOT

MESH_PATH = ROOT / "data" / "sample" / "ibge_se_municipalities.geojson"

Ring = list[list[float]]


def _in_ring(lon: float, lat: float, ring: Ring) -> bool:
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(p[:2] for p in ring):
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _in_polygon(lon: float, lat: float, rings: list[Ring]) -> bool:
    return _in_ring(lon, lat, rings[0]) and not any(_in_ring(lon, lat, hole) for hole in rings[1:])


@lru_cache(maxsize=1)
def _load(path: Path) -> tuple[tuple[str, tuple[list[Ring], ...]], ...]:
    features = json.loads(path.read_text(encoding="utf-8"))["features"]
    municipalities = []
    for feature in features:
        geometry = feature["geometry"]
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        municipalities.append((str(feature["properties"]["codarea"]), tuple(polygons)))
    return tuple(municipalities)


def municipality_code(lat: float, lon: float, path: Path | None = None) -> str | None:
    """7-digit IBGE code of the municipality containing the point, or None."""
    try:
        municipalities = _load(path or MESH_PATH)
    except (OSError, ValueError, KeyError):
        return None
    for code, polygons in municipalities:
        if any(_in_polygon(lon, lat, rings) for rings in polygons):
            return code
    return None
