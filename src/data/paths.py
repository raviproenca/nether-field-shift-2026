# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Default folders (all git-ignored): raw = downloaded granules, cache = API responses, processed = output."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
CACHE_DIR = ROOT / "data" / "cache"
PROCESSED_DIR = ROOT / "data" / "processed"


def safe_filename(text: str) -> str:
    """Keep only letters, digits and _ . - so names from files, variables or STAC ids are safe on disk."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", text)
