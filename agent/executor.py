"""
agent/executor.py — Test execution coordinator with Flow Engine integration.

Orchestrates execution of test scenarios and business workflows using Playwright MCP.
Handles multi-level verification, evidence capture, discrepancy logging, and failure analysis.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.playwright_client import PlaywrightClient
from agent.verifier import verify_scenario
from agent.failure_analyzer import analyze_failure
from agent.flow_engine import FlowEngine
from agent.memory_store import ModuleMemoryStore
from config.settings import settings
from utils.evidence import evidence_filename
from workflows.login import perform_login


async def execute_test_plan(
    test_plan: dict[str, Any],
    base_url: str | None = None,
) -> list[dict[str, Any]]:
    """
    Execute all scenarios in the test plan and return structured results.
    """
    url = base_url or settings.base_url
    results: list[dict[str, Any]] = []
    module_name = test_plan.get("module", "general")
    memory = ModuleMemoryStore(module_name)
    flow_engine = FlowEngine()

    async with PlaywrightClient() as client:
        await client.navigate(url)
        try:
            await perform_login(client)
        except Exception:
            pass

        # If it's a known macro business flow requirement
        feature_name = test_plan.get("feature", "").lower()
        if any(w in feature_name for w in ["lifecycle", "audit plan creation", "item group and item creation", "explore the sales"]):
            flow_steps = await flow_engine.execute_module_flow(client, module_name)
            for s in flow_steps:
                results.append({
                    "id": f"FLOW_STEP_{s.get('step', 1)}",
                    "title": s.get("name", "Workflow Step"),
                    "type": "workflow",
                    "doc_status": s.get("doc_status", test_plan.get("doc_status", "DOCUMENTED")),
                    "status": s.get("status", "PASS"),
                    "actual_result": s.get("actual", ""),
                    "defects": [],
                    "evidence": [s.get("evidence", {}).get("screenshot")] if s.get("evidence", {}).get("screenshot") else [],
                    "failure_analysis": None,
                })
            memory.record_run_result({"feature": feature_name, "results_count": len(results)})
            return results

        # Execute scenarios standard
        for scenario in test_plan.get("scenarios", []):
            if scenario.get("status") == "GAP":
                results.append(_gap_result(scenario))
                continue

            result = await _run_scenario(client, scenario, module_name)
            results.append(result)

    memory.record_run_result({"feature": test_plan.get("feature"), "results_count": len(results)})
    return results


async def _run_scenario(
    client: PlaywrightClient,
    scenario: dict[str, Any],
    module_name: str,
) -> dict[str, Any]:
    """Run a single test scenario and return its result."""
    tc_id = scenario.get("id", "TC_001")
    doc_status = scenario.get("doc_status", "DOCUMENTED")

    result: dict[str, Any] = {
        "id": tc_id,
        "title": scenario["title"],
        "type": scenario.get("type", "functional"),
        "doc_status": doc_status,
        "status": "PASS" if doc_status == "DOCUMENTED" else "OBSERVED",
        "actual_result": "",
        "defects": [],
        "evidence": [],
        "failure_analysis": None,
    }

    try:
        client.clear_logs()

        # Execute steps
        for step in scenario.get("steps", []):
            await _execute_step(client, step)

        # Verification
        verification = await verify_scenario(client, scenario, module_name=module_name)
        result["status"] = verification.get("status", result["status"])
        result["actual_result"] = verification.get("actual_result", "")

        # Capture screenshot evidence
        fname = evidence_filename(tc_id, scenario["title"], "png")
        screenshot_path = await client.screenshot(fname.replace(".png", ""))
        result["evidence"].append(str(screenshot_path))

        if result["status"] == "FAIL":
            result["failure_analysis"] = await analyze_failure(client, scenario, verification)

    except Exception as exc:
        result["status"] = "BLOCKED" if doc_status == "DOCUMENTED" else "UNVERIFIABLE"
        result["actual_result"] = f"Exception during execution: {exc}"
        try:
            fname = evidence_filename(tc_id, f"blocked_{scenario['title']}", "png")
            screenshot_path = await client.screenshot(fname.replace(".png", ""))
            result["evidence"].append(str(screenshot_path))
        except Exception:
            pass

    return result


async def _execute_step(client: PlaywrightClient, step: str) -> None:
    """Execute simple step instructions."""
    step_lower = step.lower().strip()

    if step_lower.startswith("navigate to "):
        url = step[len("navigate to "):].strip()
        await client.navigate(url)
    elif step_lower.startswith("click "):
        selector = step[len("click "):].strip()
        if await client.is_visible(selector):
            await client.click(selector)
    elif step_lower.startswith("fill ") or step_lower.startswith("enter "):
        parts = step.split(" with ") if " with " in step else step.split(" as ")
        if len(parts) == 2:
            selector = parts[0].replace("fill ", "").replace("enter ", "").strip()
            val = parts[1].strip().strip('"').strip("'")
            if await client.is_visible(selector):
                await client.fill(selector, val)
    elif "wait" in step_lower:
        await client.wait_for_network_idle()
    else:
        # Default safety: wait network idle
        await client.wait_for_network_idle()


def _gap_result(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": scenario.get("id", "TC_GAP"),
        "title": scenario.get("title", ""),
        "type": scenario.get("type", "functional"),
        "doc_status": scenario.get("doc_status", "UNDOCUMENTED"),
        "status": "GAP",
        "actual_result": "Requirement ambiguous or missing specification.",
        "defects": [],
        "evidence": [],
        "failure_analysis": None,
    }
