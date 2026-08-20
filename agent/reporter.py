"""
agent/reporter.py — Multi-Level QA Report Generation.

Implements Phase 7:
Generates structured QA reports in Markdown and JSON formats, clearly separating:
1. Validated Results (PASS / FAIL)
2. Exploratory Findings (OBSERVED / UNVERIFIABLE)
3. Documentation Discrepancies (Doc vs Live App conflicts)
4. Defect Classifications & Evidence
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings
from agent.memory_store import ModuleMemoryStore


def generate_report(
    requirement: str,
    test_plan: dict[str, Any],
    results: list[dict[str, Any]],
) -> Path:
    """
    Generate a structured QA report and save it to the reports directory.
    """
    settings.ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    module = test_plan.get("module", "Unknown")
    feature = test_plan.get("feature", "Unknown")
    doc_status = test_plan.get("doc_status", "DOCUMENTED")

    report_path = settings.report_dir / f"QA_Report_{module}_{timestamp}.md"
    json_path = settings.report_dir / f"QA_Report_{module}_{timestamp}.json"

    # Compute summary stats
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "PASS")
    failed = sum(1 for r in results if r.get("status") == "FAIL")
    observed = sum(1 for r in results if r.get("status") == "OBSERVED")
    unverifiable = sum(1 for r in results if r.get("status") == "UNVERIFIABLE")
    discrepancies = sum(1 for r in results if r.get("status") == "DISCREPANCY")
    blocked = sum(1 for r in results if r.get("status") == "BLOCKED")
    gap = sum(1 for r in results if r.get("status") == "GAP")

    # Retrieve persistent discrepancies from module memory
    memory = ModuleMemoryStore(module)
    stored_discrepancies = memory.state.get("discrepancies", [])

    # Collect confirmed defects
    defects = [
        r for r in results
        if r.get("status") == "FAIL" and r.get("failure_analysis", {}).get("failure_type") == "application_defect"
    ]

    severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for d in defects:
        sev = (d.get("defect_classification") or {}).get("severity", "medium")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    md = _build_markdown(
        requirement=requirement,
        module=module,
        feature=feature,
        doc_status=doc_status,
        timestamp=timestamp,
        total=total,
        passed=passed,
        failed=failed,
        observed=observed,
        unverifiable=unverifiable,
        discrepancies_count=discrepancies,
        blocked=blocked,
        gap=gap,
        results=results,
        defects=defects,
        stored_discrepancies=stored_discrepancies,
        severity_counts=severity_counts,
    )

    report_path.write_text(md, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "requirement": requirement,
                "module": module,
                "doc_status": doc_status,
                "timestamp": timestamp,
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "observed": observed,
                    "unverifiable": unverifiable,
                    "discrepancies": discrepancies,
                    "blocked": blocked,
                    "gap": gap,
                },
                "results": results,
                "discrepancies": stored_discrepancies,
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
    doc_status: str,
    timestamp: str,
    total: int,
    passed: int,
    failed: int,
    observed: int,
    unverifiable: int,
    discrepancies_count: int,
    blocked: int,
    gap: int,
    results: list[dict[str, Any]],
    defects: list[dict[str, Any]],
    stored_discrepancies: list[dict[str, Any]],
    severity_counts: dict[str, int],
) -> str:
    lines = [
        f"# Stockount QA Report — {module} [{doc_status}]",
        f"",
        f"**Generated:** {timestamp}  ",
        f"**Requirement:** {requirement}  ",
        f"**Feature:** {feature}  ",
        f"**Documentation Status:** `{doc_status}`",
        f"",
        "---",
        "",
        "## Summary Metrics",
        "",
        f"| Category | Count | Status Description |",
        f"|---|---|---|",
        f"| Total Steps / Scenarios | {total} | Overall execution items |",
        f"| ✅ Validated (PASS) | {passed} | Actual live behavior matched reference docs |",
        f"| ❌ Failed (FAIL) | {failed} | Confirmed functional/technical failure |",
        f"| 🔍 Exploratory (OBSERVED) | {observed} | Observed live app behavior (undocumented area) |",
        f"| ❓ Unverifiable | {unverifiable} | Could not verify against spec |",
        f"| ⚠️ Doc Discrepancies | {discrepancies_count} | Live app diverged from reference docs |",
        f"| 🚫 Blocked | {blocked} | Execution blocked by dependencies/errors |",
        f"| 📋 Requirement Gap | {gap} | Ambiguous requirements |",
        "",
        "---",
        "",
        "## Execution Details",
        "",
        "| ID | Step / Scenario | Doc Status | Status | Actual Live Behavior / Finding |",
        "|---|---|---|---|---|",
    ]

    for r in results:
        status = r.get("status", "PASS")
        status_badge = {
            "PASS": "✅ PASS",
            "FAIL": "❌ FAIL",
            "OBSERVED": "🔍 OBSERVED",
            "UNVERIFIABLE": "❓ UNVERIFIABLE",
            "DISCREPANCY": "⚠️ DISCREPANCY",
            "BLOCKED": "🚫 BLOCKED",
            "GAP": "📋 GAP",
        }.get(status, status)

        doc_tag = r.get("doc_status", doc_status)
        actual = (r.get("actual_result") or "").replace("\n", " ")[:100]
        lines.append(f"| {r.get('id', 'TC')} | {r.get('title', '')[:45]} | `{doc_tag}` | {status_badge} | {actual} |")

    lines.append("")

    # Documentation Discrepancies Section
    if stored_discrepancies:
        lines += [
            "---",
            "",
            "## ⚠️ Documentation vs. Live App Discrepancies",
            "",
            "> The following mismatches between reference documentation and actual live-app behavior were recorded:",
            "",
        ]
        for i, disc in enumerate(stored_discrepancies[-5:], 1):
            lines += [
                f"### Discrepancy #{i:02d}: {disc.get('title')}",
                f"- **Documented Expectation:** {disc.get('documented_expectation')}",
                f"- **Live Application Behavior:** {disc.get('actual_behavior')}",
                f"- **Recorded At:** {disc.get('recorded_at')}",
                "",
            ]

    # Confirmed Defects Section
    if defects:
        lines += [
            "---",
            "",
            "## ❌ Confirmed Defects",
            "",
        ]
        for i, d in enumerate(defects, 1):
            fa = d.get("failure_analysis") or {}
            dc = d.get("defect_classification") or {}
            lines += [
                f"### Defect #{i:02d} — {d['title']}",
                f"- **Scenario ID:** {d['id']}",
                f"- **Severity:** `{dc.get('severity', 'medium').upper()}`",
                f"- **Failure Type:** {fa.get('failure_type', 'N/A')}",
                f"- **Actual Result:** {d.get('actual_result', '')}",
                f"- **Explanation:** {fa.get('explanation', '')}",
                f"- **Evidence:** {', '.join(d.get('evidence', [])) or 'None'}",
                "",
            ]

    lines.append("---")
    lines.append("*Report generated by Stockount AI QA Agent (Antigravity + Gemini + MCP + Playwright)*")
    return "\n".join(lines)
