"""
agent/reporter.py — QA report generation.

Generates structured QA reports in Markdown and JSON formats.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings
from utils.helpers import format_table


def generate_report(
    requirement: str,
    test_plan: dict[str, Any],
    results: list[dict[str, Any]],
) -> Path:
    """
    Generate a structured QA report and save it to the reports directory.

    Returns:
        Path to the generated Markdown report.
    """
    settings.ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    module = test_plan.get("module", "Unknown")
    feature = test_plan.get("feature", "Unknown")

    report_path = settings.report_dir / f"QA_Report_{module}_{timestamp}.md"
    json_path = settings.report_dir / f"QA_Report_{module}_{timestamp}.json"

    # Compute summary stats
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    blocked = sum(1 for r in results if r["status"] == "BLOCKED")
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")

    # Collect confirmed defects
    defects = [
        r for r in results
        if r["status"] == "FAIL" and r.get("failure_analysis", {}).get("failure_type") == "application_defect"
    ]

    severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for d in defects:
        sev = (d.get("defect_classification") or {}).get("severity", "medium")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    md = _build_markdown(
        requirement=requirement,
        module=module,
        feature=feature,
        timestamp=timestamp,
        total=total,
        passed=passed,
        failed=failed,
        blocked=blocked,
        skipped=skipped,
        results=results,
        defects=defects,
        severity_counts=severity_counts,
    )

    report_path.write_text(md, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "requirement": requirement,
                "test_plan": test_plan,
                "results": results,
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "blocked": blocked,
                    "skipped": skipped,
                },
                "defects": defects,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    return report_path


def _build_markdown(
    *,
    requirement: str,
    module: str,
    feature: str,
    timestamp: str,
    total: int,
    passed: int,
    failed: int,
    blocked: int,
    skipped: int,
    results: list[dict[str, Any]],
    defects: list[dict[str, Any]],
    severity_counts: dict[str, int],
) -> str:
    lines = [
        f"# QA Report — {module} / {feature}",
        f"",
        f"**Generated:** {timestamp}  ",
        f"**Requirement:** {requirement}",
        f"",
        "---",
        "",
        "## Test Summary",
        "",
        f"| Metric   | Count |",
        f"|----------|-------|",
        f"| Total    | {total} |",
        f"| ✅ Passed  | {passed} |",
        f"| ❌ Failed  | {failed} |",
        f"| 🚫 Blocked | {blocked} |",
        f"| ⏭️ Skipped | {skipped} |",
        "",
        "## Defect Summary",
        "",
        f"| Severity | Count |",
        f"|----------|-------|",
        f"| 🔴 Critical | {severity_counts.get('critical', 0)} |",
        f"| 🟠 High     | {severity_counts.get('high', 0)} |",
        f"| 🟡 Medium   | {severity_counts.get('medium', 0)} |",
        f"| 🔵 Low      | {severity_counts.get('low', 0)} |",
        "",
        "---",
        "",
        "## Test Results",
        "",
    ]

    # Results table
    table_rows = []
    for r in results:
        status_icon = {
            "PASS": "✅ PASS",
            "FAIL": "❌ FAIL",
            "BLOCKED": "🚫 BLOCKED",
            "SKIPPED": "⏭️ SKIPPED",
        }.get(r["status"], r["status"])

        table_rows.append(
            f"| {r['id']} | {r['title'][:50]} | {r['type']} | {status_icon} | {r['actual_result'][:80]} |"
        )

    lines.append("| TC ID | Scenario | Type | Status | Actual Result |")
    lines.append("|-------|----------|------|--------|---------------|")
    lines.extend(table_rows)
    lines.append("")
    lines.append("---")
    lines.append("")

    # Defect details
    if defects:
        lines.append("## Confirmed Defects")
        lines.append("")
        for i, d in enumerate(defects, 1):
            fa = d.get("failure_analysis") or {}
            dc = d.get("defect_classification") or {}
            lines += [
                f"### Bug {i:03d} — {d['title']}",
                "",
                f"**TC ID:** {d['id']}  ",
                f"**Severity:** {dc.get('severity', 'N/A')}  ",
                f"**Priority:** {dc.get('priority', 'N/A')}  ",
                f"**Failure Type:** {fa.get('failure_type', 'N/A')}  ",
                f"**Reproducible:** {fa.get('reproducible', 'N/A')}  ",
                "",
                f"**Actual Result:** {d.get('actual_result', '')}",
                "",
                f"**Explanation:** {fa.get('explanation', '')}",
                "",
                f"**Suggested Investigation:** {fa.get('suggested_investigation', '')}",
                "",
                f"**Evidence:** {', '.join(d.get('evidence', [])) or 'None'}",
                "",
                "---",
                "",
            ]

    lines.append("*Report generated by AI QA Agent*")
    return "\n".join(lines)
