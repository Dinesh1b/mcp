"""
mcp/shared/defect_manager.py — Structured defect detection, creation, and storage.

Detects defects from test failures, creates structured defect records,
and persists them as JSON files in the defects/ directory.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

from agent.defect_classifier import classify_defect

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


def _generate_defect_id(module: str, index: int) -> str:
    """Generate a unique defect ID like DEF-AUD-001."""
    prefix = module[:3].upper()
    return f"DEF-{prefix}-{index:03d}"


async def detect_defects(ctx: "ExecutionContext") -> list[dict[str, Any]]:
    """
    Detect defects from failed test results.

    Iterates over test_results, identifies application defects,
    and creates structured defect records.

    Returns:
        List of structured defect dicts.
    """
    defects: list[dict[str, Any]] = []
    defect_index = 1

    for result in ctx.test_results:
        if result.get("status") != "FAIL":
            continue

        fa = result.get("failure_analysis") or {}

        # Only classify as defect if failure analysis indicates application_defect
        if fa.get("failure_type") != "application_defect":
            continue

        # Attempt classification
        dc: dict[str, Any] = {}
        try:
            dc = await classify_defect(
                scenario={"id": result["id"], "title": result["title"]},
                failure_analysis=fa,
            )
        except Exception:
            dc = {
                "severity": "medium",
                "priority": "P3",
                "impact": "Unable to classify — manual review required.",
            }

        defect = {
            "defect_id": _generate_defect_id(ctx.module_name, defect_index),
            "title": dc.get("defect_title", result.get("title", "Unknown Defect")),
            "module": ctx.module_name,
            "workflow": result.get("type", "unknown"),
            "test_id": result.get("id", ""),
            "severity": dc.get("severity", "medium"),
            "priority": dc.get("priority", "P3"),
            "preconditions": result.get("preconditions", []),
            "steps_to_reproduce": fa.get("reproduction_steps", []),
            "expected_result": result.get("expected_result", ""),
            "actual_result": result.get("actual_result", ""),
            "evidence_references": result.get("evidence", []),
            "console_errors": fa.get("console_errors", []),
            "api_details": fa.get("api_details", {}),
            "reproduction_status": (
                "reproduced" if fa.get("reproducible") else "not_reproduced"
            ),
            "root_cause_hypothesis": fa.get("explanation", ""),
            "recommended_fix": dc.get("recommended_action", ""),
            "reproducibility": dc.get("reproducibility", "unknown"),
            "impact": dc.get("impact", ""),
            "run_id": ctx.run_id,
            "timestamp": datetime.now().isoformat(),
        }

        defects.append(defect)
        defect_index += 1

    return defects


def save_defects(ctx: "ExecutionContext") -> int:
    """
    Save defect records to the defects/ directory as JSON files.

    Returns:
        Number of defects saved.
    """
    if not ctx.defects:
        return 0

    defects_dir = ctx.defects_dir
    defects_dir.mkdir(parents=True, exist_ok=True)

    # Save individual defect files
    for defect in ctx.defects:
        defect_file = defects_dir / f"{defect['defect_id']}_{ctx.run_id}.json"
        defect_file.write_text(
            json.dumps(defect, indent=2, default=str),
            encoding="utf-8",
        )

    # Save consolidated defect summary
    summary_file = defects_dir / f"defects_{ctx.module_name}_{ctx.run_id}.json"
    summary_file.write_text(
        json.dumps({
            "module": ctx.module_name,
            "run_id": ctx.run_id,
            "timestamp": ctx.timestamp,
            "defect_count": len(ctx.defects),
            "defects": ctx.defects,
        }, indent=2, default=str),
        encoding="utf-8",
    )

    return len(ctx.defects)
