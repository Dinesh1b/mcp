"""
mcp/shared/evidence_manager.py — Enhanced evidence collection and linking.

Extends the existing utils/evidence.py with module-level tagging,
test-run linking, and consolidated evidence summaries.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

from config.settings import settings
from utils.evidence import evidence_filename, save_console_errors, save_network_log

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


def consolidate_evidence(ctx: "ExecutionContext") -> dict[str, Any]:
    """
    Consolidate all evidence references from test results into the context.

    Scans test_results for evidence paths and organizes them by type.

    Returns:
        Summary dict with evidence counts and paths.
    """
    screenshots: list[str] = []
    traces: list[str] = []
    console_logs: list[str] = []
    network_logs: list[str] = []

    for result in ctx.test_results:
        for path_str in result.get("evidence", []):
            path = Path(path_str)
            if path.suffix == ".png":
                screenshots.append(path_str)
            elif path.suffix == ".zip":
                traces.append(path_str)
            elif "console" in path_str:
                console_logs.append(path_str)
            elif "network" in path_str:
                network_logs.append(path_str)

            if path_str not in ctx.evidence_paths:
                ctx.evidence_paths.append(path_str)

    summary = {
        "total": len(ctx.evidence_paths),
        "screenshots": len(screenshots),
        "traces": len(traces),
        "console_logs": len(console_logs),
        "network_logs": len(network_logs),
        "paths": {
            "screenshots": screenshots,
            "traces": traces,
            "console_logs": console_logs,
            "network_logs": network_logs,
        },
    }

    # Save the evidence manifest
    manifest_path = (
        ctx.evidence_dir / f"manifest_{ctx.module_name}_{ctx.run_id}.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({
            "module": ctx.module_name,
            "run_id": ctx.run_id,
            "timestamp": ctx.timestamp,
            **summary,
        }, indent=2),
        encoding="utf-8",
    )

    return summary


def capture_screenshot_evidence(
    client: Any,
    test_id: str,
    description: str,
    ctx: "ExecutionContext",
) -> str | None:
    """
    Capture a screenshot and register it with the context.

    This is a synchronous wrapper — call from within an async context.
    Returns the screenshot path string, or None on failure.
    """
    # Note: actual screenshot capture is async and happens in the executor.
    # This helper builds the path and registers it.
    fname = evidence_filename(test_id, description, "png")
    path = ctx.evidence_dir / "screenshots" / fname
    ctx.evidence_paths.append(str(path))
    return str(path)
