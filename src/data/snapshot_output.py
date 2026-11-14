# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Turn fetched snapshot data into the JSON/GeoJSON files of docs/data-format.md, check their size and write them."""

import json
import math
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np

from .errors import SizeLimitError
from .sampling import Point
from .snapshot_model import Region, SourceData, SourceInfo, Variable

FORMAT_VERSION = 1
MAX_TOTAL_BYTES = 5 * 1024 * 1024


def _dump(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def points_geojson(points: list[Point]) -> dict:
    features = [
        {
            "type": "Feature",
            "id": point.id,
            "geometry": {"type": "Point", "coordinates": [point.lon, point.lat]},
            "properties": {"id": point.id, "lat": point.lat, "lon": point.lon},
        }
        for point in points
    ]
    return {"type": "FeatureCollection", "features": features}


def _rounded(value: float, decimals: int) -> float | None:
    return None if not math.isfinite(value) else round(float(value), decimals)


def kept_times(data: SourceData) -> list[int]:
    """Indexes of the times where at least one point has a valid value (empty dates are not published)."""
    valid = np.isfinite(data.values).any(axis=(0, 2))
    return [index for index, flag in enumerate(valid) if flag]


def _point_series(row: np.ndarray, times: list[str], keep: list[int], variables: list[Variable]) -> list[dict]:
    return [
        {"time": times[t], "values": {v.name: _rounded(row[t, i], v.decimals) for i, v in enumerate(variables)}}
        for t in keep
    ]


def _variable_json(variable: Variable) -> dict:
    return {"name": variable.name, "long_name": variable.long_name, "unit": variable.unit}


def attribution_json(info: SourceInfo) -> dict:
    return {"dataset": info.dataset, "doi": info.doi, "url": info.url, "notice": info.notice}


def source_file(info: SourceInfo, data: SourceData, region: Region, points: list[Point], rows: list[int]) -> dict:
    """The <region>/<source>.json payload: shared metadata plus the series of each point that has any value."""
    keep = kept_times(data)
    series = {}
    for point, row in zip(points, rows):
        entries = _point_series(data.values[row], data.times, keep, data.variables)
        if any(v is not None for entry in entries for v in entry["values"].values()):
            series[point.id] = entries
    times = [data.times[t] for t in keep]
    return {
        "source": info.id,
        "region": region.id,
        "variables": [_variable_json(v) for v in data.variables],
        "aggregation": info.aggregation,
        "resolution": info.resolution,
        "period": {"start": times[0], "end": times[-1]} if times else None,
        "attribution": attribution_json(info),
        "points": series,
    }


def build_files(
    generated_at: datetime,
    regions: list[Region],
    region_points: dict[str, list[Point]],
    infos: dict[str, SourceInfo],
    results: dict[str, SourceData],
    all_points: list[Point],
    failures: dict[str, str],
) -> dict[str, bytes]:
    """All output files as {relative path: bytes}, including index.json. Nothing is written here."""
    position = {point.id: row for row, point in enumerate(all_points)}
    files: dict[str, bytes] = {}
    index_regions, index_sources, warnings = [], [], []
    for region in regions:
        points = region_points[region.id]
        files[f"{region.id}/points.geojson"] = _dump(points_geojson(points))
        index_regions.append(
            {
                "id": region.id,
                "name": region.name,
                "bbox": list(region.bbox.as_tuple),
                "spacing_deg": region.spacing,
                "points": len(points),
                "points_file": f"{region.id}/points.geojson",
            }
        )
    for source_id, info in infos.items():
        if source_id in failures:
            index_sources.append(_index_source(info, None, "failed", {}))
            warnings.append({"source": source_id, "code": "source_failed", "message": failures[source_id]})
            continue
        data = results[source_id]
        names = {}
        for region in regions:
            points = region_points[region.id]
            payload = source_file(info, data, region, points, [position[p.id] for p in points])
            names[region.id] = f"{region.id}/{source_id}.json"
            files[names[region.id]] = _dump(payload)
        keep = kept_times(data)
        index_sources.append(_index_source(info, data, "ok", names, [data.times[t] for t in keep]))
        warnings.extend({"source": source_id, "code": "partial_data", "message": text} for text in data.warnings)
    index = {
        "format_version": FORMAT_VERSION,
        "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regions": index_regions,
        "sources": index_sources,
        "warnings": warnings,
    }
    files["index.json"] = _dump(index)
    return files


def _index_source(info: SourceInfo, data: SourceData | None, status: str, names: dict, times: list[str] | None = None):
    entry = {
        "id": info.id,
        "name": info.name,
        "provider": info.provider,
        "nasa": info.nasa,
        "status": status,
        "resolution": info.resolution,
        "temporal_resolution": info.temporal_resolution,
        "aggregation": info.aggregation,
        "attribution": attribution_json(info),
        "variables": [_variable_json(v) for v in data.variables] if data else [],
        "latest_date": data.latest_date if data else None,
        "period": {"start": times[0], "end": times[-1]} if times else None,
        "files": names,
    }
    return entry


def check_size(files: dict[str, bytes], limit: int = MAX_TOTAL_BYTES) -> int:
    """Total size in bytes; raises SizeLimitError with a per-file table when it exceeds `limit`."""
    total = sum(len(content) for content in files.values())
    if total > limit:
        biggest = sorted(files.items(), key=lambda item: len(item[1]), reverse=True)[:8]
        table = "; ".join(f"{name} {len(content) / 1024:.0f} KB" for name, content in biggest)
        raise SizeLimitError(
            f"snapshots total {total / 1048576:.2f} MB, above the limit of {limit / 1048576:.2f} MB "
            f"(largest files: {table}). Use fewer --days, a larger --spacing, fewer regions or --max-mb."
        )
    return total


def write_files(out_dir: Path, files: dict[str, bytes]) -> None:
    """Replace index.json and the region folders of this run in out_dir. Nothing else is touched."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.json").unlink(missing_ok=True)
    for region_dir in {Path(name).parent for name in files if "/" in name}:
        shutil.rmtree(out_dir / region_dir, ignore_errors=True)
    for name, content in files.items():
        target = out_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
