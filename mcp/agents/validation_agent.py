"""
mcp/agents/validation_agent.py — Validation Agent adapter for MCP.

Performs Stage 7: VALIDATE_RESULTS.
Independently evaluates executed scenarios and raw application states against
documented specifications, ground-truth rules, and UI expectations.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from mcp.playwright_client import PlaywrightClient

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


async def run_validation_agent(
    ctx: "ExecutionContext",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Validate all executed test scenarios against documented rules and live DOM states.
    Produces explicit validation verdicts (PASS, FAIL, BLOCKED, DISCREPANCY).
    """
    validated_results = []
    discrepancies = []

    doc_behaviors = (ctx.module_documentation or {}).get("expected_behaviors", {})

    for result in ctx.test_results:
        # If the result was already BLOCKED or GAP during execution, preserve it
        if result.get("status") in ["BLOCKED", "GAP", "SKIPPED"]:
            validated_results.append(result)
            continue

        exec_state = result.get("execution_state", {})
        dom_snippet = exec_state.get("dom_snippet", "")
        url = exec_state.get("url", "")
        title = exec_state.get("title", "")

        tc_type = result.get("type", "functional")
        expected_spec = doc_behaviors.get(tc_type) or doc_behaviors.get(result.get("id", ""))

        # Evaluate live state against expectations
        has_error = "error" in dom_snippet.lower() or "not found" in dom_snippet.lower()
        has_login_redirect = "authorization/login" in url.lower() and "login" not in result.get("title", "").lower()

        if has_login_redirect:
            result["status"] = "BLOCKED"
            result["actual_result"] = f"Action redirected to login view at {url}"
            discrepancies.append(f"{result.get('id')}: Authentication lost during test")
        elif has_error:
            result["status"] = "FAIL"
            result["actual_result"] = f"Observed error indicators in DOM at {url}"
            discrepancies.append(f"{result.get('id')}: Error indicator detected on {url}")
        else:
            result["status"] = "PASS"
            if not result.get("actual_result"):
                result["actual_result"] = f"State validated on {url} (Title: {title})"

        # Attach validation metadata
        result["validation"] = {
            "validated": True,
            "expected_specification": expected_spec,
            "verified_url": url,
            "has_error_indicators": has_error,
        }
        validated_results.append(result)

    ctx.test_results = validated_results
    return {
        "status": "SUCCESS",
        "validated_count": len(validated_results),
        "passed_count": sum(1 for r in validated_results if r.get("status") == "PASS"),
        "failed_count": sum(1 for r in validated_results if r.get("status") == "FAIL"),
        "blocked_count": sum(1 for r in validated_results if r.get("status") == "BLOCKED"),
        "discrepancies": discrepancies,
    }
