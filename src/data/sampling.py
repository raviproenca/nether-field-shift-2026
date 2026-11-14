# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Regular point grids over a bounding box and box means of gridded layers, for the snapshot generator."""

import math
import warnings
from dataclasses import dataclass

import numpy as np

from .errors import InputError
from .regions import BBox

EDGE_TOLERANCE = 1e-6


@dataclass(frozen=True)
class Point:
    """A grid point. `half` is half the grid spacing in degrees: the point stands for the box lat/lon +- half."""

    id: str
    lat: float
    lon: float
    half: float


def _axis(low: float, high: float, step: float) -> list[float]:
    """Multiples of `step` inside [low, high], rounded to 4 decimals."""
    first = math.ceil(round(low / step, 6))
    last = math.floor(round(high / step, 6))
    return [round(index * step, 4) for index in range(first, last + 1)]


def grid_points(bbox: BBox, spacing: float, prefix: str) -> list[Point]:
    """Points at multiples of `spacing` degrees inside the box, north to south then west to east: SE001, SE002..."""
    if not math.isfinite(spacing) or spacing <= 0:
        raise InputError(f"grid spacing must be a positive number of degrees, got {spacing}")
    lats = sorted(_axis(bbox.south, bbox.north, spacing), reverse=True)
    lons = _axis(bbox.west, bbox.east, spacing)
    cells = [(lat, lon) for lat in lats for lon in lons]
    if not cells:
        raise InputError(f"no grid point of {spacing} degrees falls inside the box {bbox.as_tuple}")
    return [Point(f"{prefix}{number:03d}", lat, lon, spacing / 2) for number, (lat, lon) in enumerate(cells, start=1)]


@dataclass(frozen=True)
class Layer:
    """Gridded values over time: values[time, lat, lon] with ascending 1-D `lat` and `lon`; NaN where invalid."""

    lat: np.ndarray
    lon: np.ndarray
    values: np.ndarray


def _indexes(axis: np.ndarray, center: float, half: float) -> np.ndarray:
    """Positions of the axis values inside center +- half; the nearest one when the box holds none."""
    inside = np.flatnonzero(np.abs(axis - center) <= half + EDGE_TOLERANCE)
    return inside if inside.size else np.array([int(np.argmin(np.abs(axis - center)))])


def sample_layer(layer: Layer, points: list[Point]) -> np.ndarray:
    """Mean of the valid cells inside each point's box, as an array [time, point]; NaN when no cell is valid.

    A box smaller than one cell falls back to the nearest cell. A point outside the layer gets NaN.
    """
    result = np.full((layer.values.shape[0], len(points)), np.nan, dtype="float64")
    for column, point in enumerate(points):
        outside = (
            point.lat < layer.lat.min() - point.half
            or point.lat > layer.lat.max() + point.half
            or point.lon < layer.lon.min() - point.half
            or point.lon > layer.lon.max() + point.half
        )
        if outside:
            continue
        rows, cols = _indexes(layer.lat, point.lat, point.half), _indexes(layer.lon, point.lon, point.half)
        block = layer.values[:, rows][:, :, cols].reshape(layer.values.shape[0], -1)
        valid = np.isfinite(block)
        counts = valid.sum(axis=1)
        sums = np.where(valid, block, 0.0).sum(axis=1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            result[:, column] = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
    return result
