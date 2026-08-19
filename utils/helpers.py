"""utils/helpers.py — General-purpose helpers."""

from __future__ import annotations

import json
import re
from typing import Any


def slugify(text: str) -> str:
    """Convert text to a lowercase slug suitable for filenames."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text for display/logging."""
    return text if len(text) <= max_len else text[:max_len] + "…"


def format_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    """Format a list of dicts as a plain-text table."""
    widths = {col: max(len(col), max((len(str(r.get(col, ""))) for r in rows), default=0)) for col in columns}
    header = " | ".join(col.ljust(widths[col]) for col in columns)
    sep = "-+-".join("-" * widths[col] for col in columns)
    lines = [header, sep]
    for row in rows:
        lines.append(" | ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns))
    return "\n".join(lines)


def parse_llm_json(response: str, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    """Parse a JSON response from the LLM, stripping markdown code fences.

    LLMs often wrap JSON in ```json ... ``` fences. This utility handles
    that consistently, avoiding the duplicated parsing logic that was
    previously copy-pasted across planner, verifier, failure_analyzer,
    and defect_classifier.

    Args:
        response: Raw LLM response text.
        fallback: If provided, returned on parse failure instead of raising.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If parsing fails and no fallback is provided.
    """
    raw = response.strip()
    if raw.startswith("```"):
        # Extract content between first pair of ``` fences
        parts = raw.split("```")
        if len(parts) >= 3:
            raw = parts[1]
        else:
            raw = parts[1] if len(parts) > 1 else raw
        # Strip optional language identifier (e.g. "json")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        if fallback is not None:
            return fallback
        raise ValueError(
            f"LLM returned invalid JSON: {exc}\n\nRaw:\n{response[:500]}"
        ) from exc


def sanitize_filename(text: str, max_len: int = 50) -> str:
    """Build a filesystem-safe filename fragment from arbitrary text.

    Uses slugify() to strip problematic characters (/, \\, :, etc.)
    that can break on Windows or other platforms.
    """
    return slugify(text[:max_len])

