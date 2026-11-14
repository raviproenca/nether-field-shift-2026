# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Default folders. Raw cache and processed output are git-ignored."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
