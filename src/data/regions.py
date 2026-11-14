# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Study regions: bounding boxes, presets and point + radius conversion."""

import math
from dataclasses import dataclass

from .errors import InputError

KM_PER_DEGREE_LAT = 111.32
MAX_POINT_LATITUDE = 89.0


@dataclass(frozen=True)
class BBox:
    """Bounding box in degrees (WGS84). Crossing the antimeridian is not supported."""

    west: float
    south: float
    east: float
    north: float

    def __post_init__(self) -> None:
        if not (-180 <= self.west < self.east <= 180):
            raise InputError(f"invalid longitudes: need -180 <= west < east <= 180, got {self.west}, {self.east}")
        if not (-90 <= self.south < self.north <= 90):
            raise InputError(f"invalid latitudes: need -90 <= south < north <= 90, got {self.south}, {self.north}")

    @property
    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.west, self.south, self.east, self.north)

    @property
    def center(self) -> tuple[float, float]:
        """Center as (lat, lon)."""
        return ((self.south + self.north) / 2, (self.west + self.east) / 2)


PRESETS: dict[str, BBox] = {
    "sergipe": BBox(-38.25, -11.57, -36.39, -9.51),
    "nordeste": BBox(-48.80, -18.40, -34.70, -1.00),
}
DEFAULT_PRESET = "sergipe"


def _parse_floats(text: str, count: int, label: str, hint: str) -> list[float]:
    parts = [part.strip() for part in text.split(",")]
    try:
        values = [float(part) for part in parts]
    except ValueError:
        raise InputError(f"invalid {label} '{text}': expected {hint}") from None
    if len(values) != count or not all(math.isfinite(v) for v in values):
        raise InputError(f"invalid {label} '{text}': expected {hint}")
    return values


def parse_bbox(text: str) -> BBox:
    """Accept a preset name ('sergipe', 'nordeste') or a free 'W,S,E,N' string."""
    key = text.strip().lower()
    if key in PRESETS:
        return PRESETS[key]
    west, south, east, north = _parse_floats(text, 4, "bbox", f"W,S,E,N or a preset ({', '.join(PRESETS)})")
    return BBox(west, south, east, north)


def parse_point(text: str) -> tuple[float, float]:
    lat, lon = _parse_floats(text, 2, "point", "LAT,LON")
    if not -MAX_POINT_LATITUDE <= lat <= MAX_POINT_LATITUDE:
        raise InputError(f"point latitude must be within +-{MAX_POINT_LATITUDE}, got {lat}")
    if not -180 <= lon <= 180:
        raise InputError(f"point longitude must be within +-180, got {lon}")
    return lat, lon


def point_to_bbox(lat: float, lon: float, radius_km: float) -> BBox:
    """Square box of half-side radius_km around a point (lat deg = km/111.32, lon deg = km/(111.32*cos(lat)))."""
    if not math.isfinite(radius_km) or radius_km <= 0:
        raise InputError(f"radius must be a positive number of km, got {radius_km}")
    if not -MAX_POINT_LATITUDE <= lat <= MAX_POINT_LATITUDE:
        raise InputError(f"point latitude must be within +-{MAX_POINT_LATITUDE}, got {lat}")
    delta_lat = radius_km / KM_PER_DEGREE_LAT
    delta_lon = radius_km / (KM_PER_DEGREE_LAT * math.cos(math.radians(lat)))
    return BBox(lon - delta_lon, lat - delta_lat, lon + delta_lon, lat + delta_lat)


def resolve_region(bbox: str | None = None, point: str | None = None, radius_km: float | None = None) -> BBox:
    """Pick the region from --bbox or --point/--radius-km (mutually exclusive). Default: Sergipe."""
    if bbox is not None and point is not None:
        raise InputError("use either --bbox or --point, not both")
    if point is None:
        if radius_km is not None:
            raise InputError("--radius-km needs --point")
        return parse_bbox(bbox if bbox is not None else DEFAULT_PRESET)
    if radius_km is None:
        raise InputError("--point needs --radius-km")
    lat, lon = parse_point(point)
    return point_to_bbox(lat, lon, radius_km)
