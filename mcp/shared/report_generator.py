"""
mcp/shared/report_generator.py — Enhanced module-level QA report generation.

Extends the existing agent/reporter.py with module-aware reports,
execution verdicts, workflow coverage metrics, and evidence references.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

from config.settings import settings

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


def generate_module_report(ctx: "ExecutionContext") -> Path:
    """
    Generate a comprehensive module-level QA report.

    Uses the ExecutionContext to produce both Markdown and JSON reports.

    Returns:
        Path to the generated Markdown report.
    """
    settings.ensure_dirs()

    module = ctx.module_name
    ts = ctx.timestamp
    run_id = ctx.run_id

    report_path = settings.report_dir / f"QA_Report_{module}_{ts}.md"
    json_path = settings.report_dir / f"QA_Report_{module}_{ts}.json"

    # Severity distribution
    severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for d in ctx.defects:
        sev = d.get("severity", "medium").lower()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Workflow coverage
    workflows_tested: set[str] = set()
    for r in ctx.test_results:
        workflows_tested.add(r.get("type", "unknown"))

    # Determine verdict
    verdict = _determine_verdict(ctx, severity_counts)

    # Build Markdown
    md = _build_module_markdown(
        module=module,
        run_id=run_id,
        timestamp=ts,
        total=ctx.total_count,
        passed=ctx.passed_count,
        failed=ctx.failed_count,
        blocked=ctx.blocked_count,
        skipped=ctx.skipped_count,
        results=ctx.test_results,
        defects=ctx.defects,
        severity_counts=severity_counts,
        workflows_tested=sorted(workflows_tested),
        evidence_count=len(ctx.evidence_paths),
        completed_stages=ctx.completed_stages,
        stage_errors=ctx.stage_errors,
        verdict=verdict,
    )

    report_path.write_text(md, encoding="utf-8")

    # Build JSON
    json_path.write_text(
        json.dumps({
            "module": module,
            "run_id": run_id,
            "timestamp": ts,
            "test_plan": ctx.test_plan,
            "results": ctx.test_results,
            "summary": {
                "total": ctx.total_count,
                "passed": ctx.passed_count,
                "failed": ctx.failed_count,
                "blocked": ctx.blocked_count,
                "skipped": ctx.skipped_count,
            },
            "defects": ctx.defects,
            "severity_counts": severity_counts,
            "workflows_tested": sorted(workflows_tested),
            "evidence_paths": ctx.evidence_paths,
            "completed_stages": ctx.completed_stages,
            "verdict": verdict,
        }, indent=2, default=str),
        encoding="utf-8",
    )

    return report_path


def _determine_verdict(
    ctx: "ExecutionContext",
    severity_counts: dict[str, int],
) -> dict[str, str]:
    """Determine the overall test verdict."""
    if ctx.failed_count == 0 and ctx.blocked_count == 0:
        status = "PASS"
        recommendation = "Release ready"
    elif severity_counts.get("critical", 0) > 0:
        status = "FAIL — CRITICAL DEFECTS"
        recommendation = "Do not release — critical defects must be resolved"
    elif severity_counts.get("high", 0) > 0:
        status = "FAIL — HIGH SEVERITY DEFECTS"
        recommendation = "Release blocked until high-severity defects are resolved"
    elif ctx.failed_count > 0:
        status = "PASS WITH ISSUES"
        recommendation = "Release with known issues"
    else:
        status = "BLOCKED"
        recommendation = "Tests blocked — investigation required"

    return {"status": status, "recommendation": recommendation}


def _build_module_markdown(
    *,
    module: str,
    run_id: str,
    timestamp: str,
    total: int,
    passed: int,
    failed: int,
    blocked: int,
    skipped: int,
    results: list[dict[str, Any]],
    defects: list[dict[str, Any]],
    severity_counts: dict[str, int],
    workflows_tested: list[str],
    evidence_count: int,
    completed_stages: list[str],
    stage_errors: dict[str, str],
    verdict: dict[str, str],
) -> str:
    """Build the full Markdown report."""
    lines = [
        f"# QA Report — {module.upper()} Module",
        "",
        f"**Run ID:** {run_id}  ",
        f"**Generated:** {timestamp}  ",
        f"**Module:** {module}  ",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Tests | {total} |",
        f"| ✅ Passed | {passed} |",
        f"| ❌ Failed | {failed} |",
        f"| 🚫 Blocked | {blocked} |",
        f"| ⏭️ Skipped | {skipped} |",
        f"| 🐛 Defects | {len(defects)} |",
        f"| 📸 Evidence Items | {evidence_count} |",
        "",
        f"**Verdict:** {verdict['status']}  ",
        f"**Recommendation:** {verdict['recommendation']}",
        "",
        "---",
        "",
        "## Defect Severity Distribution",
        "",
        f"| Severity | Count |",
        f"|----------|-------|",
        f"| 🔴 Critical | {severity_counts.get('critical', 0)} |",
        f"| 🟠 High | {severity_counts.get('high', 0)} |",
        f"| 🟡 Medium | {severity_counts.get('medium', 0)} |",
        f"| 🔵 Low | {severity_counts.get('low', 0)} |",
        "",
        "---",
        "",
        "## Workflow Coverage",
        "",
        f"Workflows tested: {', '.join(workflows_tested) or 'None'}",
        "",
        "---",
        "",
        "## Test Results",
        "",
        "| TC ID | Scenario | Type | Status | Actual Result |",
        "|-------|----------|------|--------|---------------|",
    ]

    for r in results:
        status_icon = {
            "PASS": "✅ PASS",
            "FAIL": "❌ FAIL",
            "BLOCKED": "🚫 BLOCKED",
            "SKIPPED": "⏭️ SKIPPED",
        }.get(r.get("status", ""), r.get("status", ""))

        title = str(r.get("title", ""))[:50]
        actual = str(r.get("actual_result", ""))[:80]
        lines.append(
            f"| {r.get('id', '')} | {title} | {r.get('type', '')} | {status_icon} | {actual} |"
        )

    lines += ["", "---", ""]

    # Defect details
    if defects:
        lines.append("## Confirmed Defects")
        lines.append("")
        for i, d in enumerate(defects, 1):
            lines += [
                f"### {d.get('defect_id', f'BUG-{i:03d}')} — {d.get('title', 'Unknown')}",
                "",
                f"**Severity:** {d.get('severity', 'N/A')}  ",
                f"**Priority:** {d.get('priority', 'N/A')}  ",
                f"**Module:** {d.get('module', module)}  ",
                f"**Workflow:** {d.get('workflow', 'N/A')}  ",
                f"**Reproducibility:** {d.get('reproducibility', 'N/A')}  ",
                "",
                f"**Expected:** {d.get('expected_result', 'N/A')}  ",
                f"**Actual:** {d.get('actual_result', 'N/A')}  ",
                "",
                f"**Root Cause Hypothesis:** {d.get('root_cause_hypothesis', 'N/A')}  ",
                f"**Recommended Fix:** {d.get('recommended_fix', 'N/A')}  ",
                "",
                f"**Evidence:** {', '.join(d.get('evidence_references', [])) or 'None'}",
                "",
                "---",
                "",
            ]

    # Pipeline stages
    lines += [
        "## Pipeline Execution",
        "",
        f"**Completed stages:** {', '.join(completed_stages)}",
        "",
    ]
    if stage_errors:
        lines.append("**Stage errors:**")
        for stage, error in stage_errors.items():
            lines.append(f"- {stage}: {error}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Report generated by MCP QA Platform*")

    return "\n".join(lines)
