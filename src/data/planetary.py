# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Microsoft Planetary Computer STAC (public, no account, no key): Sentinel-2 L2A and other collections.

Sentinel-2 is ESA/Copernicus data, not NASA data. For 30 m NASA imagery use the `hls` source.
"""

import math
from datetime import UTC, datetime
from pathlib import Path

import planetary_computer
import pystac_client
import rioxarray
from pystac import Item

from . import clip
from .dates import DateRange
from .errors import InputError, RemoteDataError, remote_errors
from .paths import safe_filename
from .regions import KM_PER_DEGREE_LAT, BBox

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
DEFAULT_COLLECTION = "sentinel-2-l2a"
DEFAULT_MAX_CLOUD = 20.0
DEFAULT_MAX_PIXELS = 25_000_000


def build_search(bbox: BBox, dates: DateRange, collection: str, max_cloud: float) -> dict:
    """Keyword arguments for pystac_client search: box, whole days, and eo:cloud_cover < max_cloud."""
    if not 0 < max_cloud <= 100:
        raise InputError(f"--max-cloud must be in (0, 100], got {max_cloud}")
    return {
        "collections": [collection],
        "bbox": list(bbox.as_tuple),
        "datetime": f"{dates.start.isoformat()}T00:00:00Z/{dates.end.isoformat()}T23:59:59Z",
        "query": {"eo:cloud_cover": {"lt": max_cloud}},
    }


def open_client() -> pystac_client.Client:
    """STAC client that signs asset URLs on the fly (planetary_computer.sign_inplace)."""
    with remote_errors("connecting to the Planetary Computer STAC API"):
        return pystac_client.Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)


def search(client: pystac_client.Client, bbox: BBox, dates: DateRange, collection: str, max_cloud: float) -> list[Item]:
    query = build_search(bbox, dates, collection, max_cloud)
    with remote_errors(f"Planetary Computer search for {collection}"):
        items = list(client.search(**query).items())
    if not items:
        raise RemoteDataError(
            f"no {collection} items for this box and period with cloud < {max_cloud:g}% "
            "(try more dates, a higher --max-cloud or another --collection)"
        )
    return sorted(items, key=item_time)


def item_time(item: Item) -> datetime:
    """When the item was acquired: datetime, else start_datetime, else the oldest possible UTC time."""
    return item.datetime or item.common_metadata.start_datetime or datetime.min.replace(tzinfo=UTC)


def latest_item_datetime(client: pystac_client.Client, bbox: BBox, collection: str) -> datetime:
    """Date of the newest item over the box, whatever the cloud cover (sortby datetime desc, limit 1)."""
    with remote_errors(f"Planetary Computer search for {collection}"):
        search_ = client.search(
            collections=[collection],
            bbox=list(bbox.as_tuple),
            sortby=[{"field": "datetime", "direction": "desc"}],
            max_items=1,
        )
        newest = next(iter(search_.items()), None)
    if newest is None:
        raise RemoteDataError(f"no {collection} items over this box")
    return item_time(newest)


def asset_href(item: Item, asset: str) -> str:
    if asset not in item.assets:
        raise InputError(f"asset '{asset}' not found in {item.id}; available: {', '.join(sorted(item.assets))}")
    return item.assets[asset].href


def window_pixels(item: Item, asset: str, bbox: BBox) -> int | None:
    """Pixels per band of the box window, from the asset resolution (gsd or proj:transform).

    Capped by the asset's own size (proj:shape). None when the item does not say its resolution.
    """
    fields = item.assets[asset].extra_fields
    resolution = fields.get("gsd") or abs((fields.get("proj:transform") or [0])[0])
    if not resolution:
        return None
    width_m = (bbox.east - bbox.west) * KM_PER_DEGREE_LAT * 1000 * math.cos(math.radians(bbox.center[0]))
    height_m = (bbox.north - bbox.south) * KM_PER_DEGREE_LAT * 1000
    pixels = math.ceil(width_m / resolution) * math.ceil(height_m / resolution)
    shape = fields.get("proj:shape")
    return min(pixels, shape[0] * shape[1]) if shape else pixels


def check_size(items: list[Item], asset: str, bbox: BBox, max_pixels: int) -> None:
    """Refuse to read windows above max_pixels per band, before touching the network."""
    for item in items:
        pixels = window_pixels(item, asset, bbox)
        if pixels is not None and pixels > max_pixels:
            raise InputError(
                f"the box is about {pixels / 1e6:.0f} million pixels per band, above the limit of "
                f"{max_pixels / 1e6:.0f} million: use a smaller --point/--radius-km (or --bbox), "
                "or raise the limit with --max-pixels"
            )


def fetch_clips(
    items: list[Item], asset: str, bbox: BBox, out_dir: Path, max_pixels: int = DEFAULT_MAX_PIXELS
) -> list[Path]:
    """Write one GeoTIFF per item with the box cut out of the asset.

    The asset is a cloud-optimized GeoTIFF opened lazily: only the window of the box is read over HTTP.
    The lat/lon box is reprojected to each item's CRS before clipping. Items without data in the box are skipped.
    """
    hrefs = [(item, asset_href(item, asset)) for item in items]
    check_size(items, asset, bbox, max_pixels)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for item, href in hrefs:
        with remote_errors(f"reading {asset} of {item.id}"):
            try:
                with rioxarray.open_rasterio(href, masked=True) as lazy:
                    clipped = clip.clip_box_latlon(lazy, bbox, item.id).load()
            except InputError:
                continue
            target = out_dir / f"{safe_filename(item.id)}_{safe_filename(asset)}.tif"
            clipped.rio.to_raster(target)
        written.append(target)
    if not written:
        raise InputError("no item has data inside the bounding box")
    return written
