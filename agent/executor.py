"""
agent/executor.py — Test execution coordinator.

Orchestrates execution of test scenarios using Playwright MCP.
Each scenario is a dict produced by the test planner.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.playwright_client import PlaywrightClient
from agent.verifier import verify_scenario
from agent.failure_analyzer import analyze_failure
from config.settings import settings
from utils.evidence import evidence_filename
from workflows.login import perform_login


async def execute_test_plan(
    test_plan: dict[str, Any],
    base_url: str | None = None,
    execution_context: Any | None = None,
) -> list[dict[str, Any]]:
    """
    Execute all scenarios in the test plan and return results.

    Args:
        test_plan: Structured plan from agent.planner.
        base_url: Override base URL from settings.
        execution_context: Optional ExecutionContext for evidence registration.

    Returns:
        List of result dicts, one per scenario.
    """
    url = base_url or settings.base_url
    results: list[dict[str, Any]] = []

    async with PlaywrightClient() as client:
        await client.navigate(url)
        await perform_login(client)

        for scenario in test_plan.get("scenarios", []):
            if scenario.get("status") == "GAP":
                results.append(_gap_result(scenario))
                continue

            result = await _run_scenario(client, scenario, execution_context=execution_context)
            results.append(result)

    return results


async def _run_scenario(
    client: PlaywrightClient,
    scenario: dict[str, Any],
    execution_context: Any | None = None,
) -> dict[str, Any]:
    """Run a single test scenario and return its result."""
    tc_id = scenario["id"]
    result: dict[str, Any] = {
        "id": tc_id,
        "title": scenario["title"],
        "type": scenario.get("type", "functional"),
        "status": "PASS",
        "actual_result": "",
        "defects": [],
        "evidence": [],
        "failure_analysis": None,
    }

    try:
        # Execute steps
        for step in scenario.get("steps", []):
            await _execute_step(client, step)

        # Verify expected behavior — do NOT assume the action succeeded
        verification = await verify_scenario(client, scenario)
        result["actual_result"] = verification["actual_result"]

        if not verification["passed"]:
            result["status"] = "FAIL"
            # Capture screenshot evidence
            fname = evidence_filename(tc_id, scenario["title"], "png")
            screenshot_path = await client.screenshot(fname.replace(".png", ""))
            path_str = str(screenshot_path)
            result["evidence"].append(path_str)
            if execution_context and hasattr(execution_context, "evidence_paths"):
                execution_context.evidence_paths.append(path_str)

            # Analyze the failure
            result["failure_analysis"] = await analyze_failure(
                client, scenario, verification
            )

    except Exception as exc:
        result["status"] = "BLOCKED"
        result["actual_result"] = f"Exception: {exc}"
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


async def _execute_step(client: PlaywrightClient, step: str) -> None:
    """
    Execute a single step instruction.

    Steps are natural-language strings from the LLM.
    We perform simple pattern matching to dispatch to Playwright actions.
    For complex steps, the orchestrator should generate Playwright code directly.
    """
    step_lower = step.lower()

    if step_lower.startswith("navigate to "):
        target = step[len("navigate to "):].strip()
        if not target.startswith("http://") and not target.startswith("https://"):
            target_route = target if target.startswith("/") else f"/{target}"
            if "azurestaticapps.net" in settings.base_url:
                target = f"https://yellow-river-0ebeae800.2.azurestaticapps.net{target_route}"
            else:
                target = f"{settings.base_url.rstrip('/')}{target_route}"
        await client.navigate(target)

    elif step_lower.startswith("click "):
        selector = step[len("click "):].strip()
        await client.click(selector)

    elif step_lower.startswith("fill "):
        # Expected format: fill <selector> with <value>
        parts = step[len("fill "):].split(" with ", 1)
        if len(parts) == 2:
            await client.fill(parts[0].strip(), parts[1].strip())

    elif step_lower.startswith("wait for "):
        selector = step[len("wait for "):].strip()
        await client.wait_for_selector(selector)

    else:
        # Unrecognized step — log and continue (do not fail test on step ambiguity)
        pass


def _gap_result(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": scenario["id"],
        "title": scenario["title"],
        "type": scenario.get("type", "functional"),
        "status": "SKIPPED",
        "actual_result": "GAP: Requirement ambiguous — see planner output.",
        "defects": [],
        "evidence": [],
        "failure_analysis": None,
    }
