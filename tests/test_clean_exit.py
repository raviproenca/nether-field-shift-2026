# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Clipping a GeoTIFF must not leave an open file that spams stderr at interpreter shutdown (HLS bug)."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
import rasterio.warp
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]


def test_clip_raster_leaves_stderr_clean(tmp_path):
    path = tmp_path / "HLS.L30.T24LYN.B04.tif"
    transform = from_origin(669000, 8795000, 30, 30)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=60,
        width=60,
        count=1,
        dtype="int16",
        crs="EPSG:32724",
        transform=transform,
        nodata=-9999,
    ) as dst:
        dst.write(np.ones((1, 60, 60), dtype="int16"))
        west, south, east, north = rasterio.warp.transform_bounds(dst.crs, "EPSG:4326", *dst.bounds)
    box = (
        west + (east - west) * 0.3,
        south + (north - south) * 0.3,
        west + (east - west) * 0.6,
        south + (north - south) * 0.6,
    )
    code = (
        "import sys, pathlib\n"
        "from src.data import clip\n"
        "from src.data.regions import BBox\n"
        f"d = clip.clip_raster(pathlib.Path(sys.argv[1]), BBox{box!r})\n"
        "d.rio.to_raster(sys.argv[2])\n"
        "print(d.shape)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(path), str(tmp_path / "out.tif")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
