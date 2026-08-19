"""
utils/evidence.py — Evidence collection helpers.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config.settings import settings


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_console_errors(errors: list[str], test_id: str) -> Path:
    path = settings.evidence_dir / "console" / f"{test_id}_{_timestamp()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(errors, indent=2), encoding="utf-8")
    return path


def save_network_log(entries: list[dict[str, Any]], test_id: str) -> Path:
    path = settings.evidence_dir / "network" / f"{test_id}_{_timestamp()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return path


def evidence_filename(test_id: str, description: str, ext: str) -> str:
    """Build a consistent evidence filename.

    Example: TC_INV_004_item_import_duplicate.png
    """
    clean = description.lower().replace(" ", "_")[:50]
    return f"{test_id}_{clean}.{ext}"
