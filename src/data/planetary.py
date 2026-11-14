# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Microsoft Planetary Computer STAC (public, no account, no key): Sentinel-2 L2A and other collections.

Sentinel-2 is ESA/Copernicus data, not NASA data. For 30 m NASA imagery use the `hls` source.
"""

from datetime import datetime
from pathlib import Path

import planetary_computer
import pystac_client
import rioxarray
from pystac import Item

from . import clip
from .dates import DateRange
from .errors import InputError, RemoteDataError
from .regions import BBox

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
DEFAULT_COLLECTION = "sentinel-2-l2a"
DEFAULT_MAX_CLOUD = 20.0


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
    try:
        return pystac_client.Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    except Exception as exc:
        raise RemoteDataError(f"could not reach the Planetary Computer STAC API: {exc}") from exc


def search(client: pystac_client.Client, bbox: BBox, dates: DateRange, collection: str, max_cloud: float) -> list[Item]:
    query = build_search(bbox, dates, collection, max_cloud)
    try:
        items = list(client.search(**query).items())
    except Exception as exc:
        raise RemoteDataError(f"Planetary Computer search failed for {collection}: {exc}") from exc
    if not items:
        raise RemoteDataError(
            f"no {collection} items for this box and period with cloud < {max_cloud:g}% "
            "(try more dates, a higher --max-cloud or another --collection)"
        )
    return sorted(items, key=lambda item: item.datetime)


def latest_item_datetime(client: pystac_client.Client, bbox: BBox, collection: str) -> datetime:
    """Date of the newest item over the box, whatever the cloud cover (sortby datetime desc, limit 1)."""
    try:
        search_ = client.search(
            collections=[collection],
            bbox=list(bbox.as_tuple),
            sortby=[{"field": "datetime", "direction": "desc"}],
            max_items=1,
        )
        newest = next(iter(search_.items()), None)
    except Exception as exc:
        raise RemoteDataError(f"Planetary Computer search failed for {collection}: {exc}") from exc
    if newest is None:
        raise RemoteDataError(f"no {collection} items over this box")
    return newest.datetime


def asset_href(item: Item, asset: str) -> str:
    if asset not in item.assets:
        raise InputError(f"asset '{asset}' not found in {item.id}; available: {', '.join(sorted(item.assets))}")
    return item.assets[asset].href


def fetch_clips(items: list[Item], asset: str, bbox: BBox, out_dir: Path) -> list[Path]:
    """Write one GeoTIFF per item with the box cut out of the asset.

    The asset is a cloud-optimized GeoTIFF opened lazily: only the window of the box is read over HTTP.
    The lat/lon box is reprojected to each item's CRS before clipping. Items without data in the box are skipped.
    """
    hrefs = [(item, asset_href(item, asset)) for item in items]
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for item, href in hrefs:
        try:
            with rioxarray.open_rasterio(href, masked=True) as lazy:
                clipped = clip.clip_box_latlon(lazy, bbox, item.id).load()
        except InputError:
            continue
        except Exception as exc:
            raise RemoteDataError(f"could not read {asset} of {item.id}: {exc}") from exc
        target = out_dir / f"{item.id}_{asset}.tif"
        clipped.rio.to_raster(target)
        written.append(target)
    if not written:
        raise InputError("no item has data inside the bounding box")
    return written
