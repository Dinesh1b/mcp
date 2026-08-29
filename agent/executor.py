"""
agent/executor.py — Test execution coordinator with Flow Engine integration.

Orchestrates execution of test scenarios and business workflows using Playwright MCP.
Handles execution, raw state capture, and evidence collection.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.playwright_client import PlaywrightClient
from mcp.core.routing import resolve_module_url
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
    execution_context: Any | None = None,
) -> list[dict[str, Any]]:
    """
    Execute all scenarios in the test plan and capture resulting application states.

    Args:
        test_plan: Structured plan from agent.planner.
        base_url: Override base URL from settings.
        execution_context: Optional ExecutionContext for evidence registration.

    Returns:
        List of result dicts, one per scenario.
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
        except Exception as exc:
            blocked_res = {
                "id": "AUTH_FAILURE",
                "title": "Application Authentication",
                "type": "system",
                "doc_status": "UNDOCUMENTED",
                "status": "BLOCKED",
                "actual_result": f"Login failed: {exc}",
                "defects": [],
                "evidence": [],
                "failure_analysis": {"failure_type": "authentication_issue", "reason": str(exc)},
            }
            results.append(blocked_res)
            memory.record_run_result({"feature": "authentication", "results_count": 1, "status": "BLOCKED"})
            return results

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

            result = await _run_scenario(client, scenario, base_url=url, execution_context=execution_context)
            results.append(result)

    memory.record_run_result({"feature": test_plan.get("feature"), "results_count": len(results)})
    return results


async def _run_scenario(
    client: PlaywrightClient,
    scenario: dict[str, Any],
    base_url: str | None = None,
    execution_context: Any | None = None,
) -> dict[str, Any]:
    """Run a single test scenario and record its execution state."""
    tc_id = scenario.get("id", "TC_001")
    doc_status = scenario.get("doc_status", "DOCUMENTED")

    result: dict[str, Any] = {
        "id": tc_id,
        "title": scenario["title"],
        "type": scenario.get("type", "functional"),
        "doc_status": doc_status,
        "status": "EXECUTED",
        "actual_result": "",
        "defects": [],
        "evidence": [],
        "failure_analysis": None,
        "execution_state": {},
    }

    try:
        client.clear_logs()

        # Execute steps
        for step in scenario.get("steps", []):
            await _execute_step(client, step, base_url=base_url)

        # Capture raw execution state for independent validation stage
        curr_url = await client.get_url()
        curr_title = await client.get_title()
        dom_snippet = (await client.get_dom_snapshot())[:3000]

        result["execution_state"] = {
            "url": curr_url,
            "title": curr_title,
            "dom_snippet": dom_snippet,
            "console_logs": client.get_console_logs()[:5],
            "network_logs": client.get_network_logs()[:10],
        }

        # Verification step
        verification = await verify_scenario(client, scenario)
        result["actual_result"] = verification["actual_result"]
        result["status"] = verification.get("status", "PASS" if verification.get("passed") else "FAIL")

        if not verification.get("passed"):
            fname = evidence_filename(tc_id, scenario["title"], "png")
            screenshot_path = await client.screenshot(fname.replace(".png", ""))
            path_str = str(screenshot_path)
            result["evidence"].append(path_str)
            if execution_context and hasattr(execution_context, "evidence_paths"):
                execution_context.evidence_paths.append(path_str)

            result["failure_analysis"] = await analyze_failure(client, scenario, verification)

    except Exception as exc:
        result["status"] = "BLOCKED" if doc_status == "DOCUMENTED" else "UNVERIFIABLE"
        result["actual_result"] = f"Exception during execution: {exc}"
        try:
            fname = evidence_filename(tc_id, f"blocked_{scenario['title']}", "png")
            screenshot_path = await client.screenshot(fname.replace(".png", ""))
            path_str = str(screenshot_path)
            result["evidence"].append(path_str)
            if execution_context and hasattr(execution_context, "evidence_paths"):
                execution_context.evidence_paths.append(path_str)
        except Exception:
            pass

    return result


async def _execute_step(client: PlaywrightClient, step: str, base_url: str | None = None) -> None:
    """Execute simple step instructions."""
    step_lower = step.lower().strip()

    if step_lower.startswith("navigate to "):
        target = step[len("navigate to "):].strip()
        url = resolve_module_url(base_url, target)
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
