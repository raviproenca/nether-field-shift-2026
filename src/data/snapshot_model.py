# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Plain data types shared by the snapshot generator: regions, source metadata and fetch results."""

from dataclasses import dataclass, field

import numpy as np

from .regions import BBox


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    bbox: BBox
    spacing: float
    prefix: str


@dataclass(frozen=True)
class PilotSite:
    """A named place with the same series as the grid points (pilot farming areas of the team)."""

    id: str
    name: str
    zone: str
    state: str
    lat: float
    lon: float
    radius_km: float
    region: str


@dataclass(frozen=True)
class Variable:
    name: str
    long_name: str
    unit: str
    decimals: int = 2


@dataclass(frozen=True)
class SourceInfo:
    """Static description of a source, copied into index.json and into each data file."""

    id: str
    name: str
    provider: str
    nasa: bool
    resolution: str
    temporal_resolution: str
    aggregation: str
    dataset: str
    doi: str | None
    url: str
    notice: str | None = None
    kind: str = "timeseries"


@dataclass
class SourceData:
    """What a fetcher returns: values[point, time, variable] for the points it was given, in that order."""

    variables: list[Variable]
    times: list[str]
    values: np.ndarray
    latest_date: str | None
    warnings: list[str] = field(default_factory=list)


@dataclass
class StaticData:
    """A layer without time (terrain): values[point, variable]."""

    variables: list[Variable]
    values: np.ndarray
    warnings: list[str] = field(default_factory=list)
