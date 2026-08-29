"""
agent/verifier.py — Application state & discrepancy verification engine.

Evaluates whether the application's actual state after test execution
matches the expected behavior defined in documentation and specifications.
"""

from __future__ import annotations

import json
from typing import Any

from agent.llm import call_llm
from mcp.playwright_client import PlaywrightClient
from prompts import SYSTEM_PROMPT
from utils.helpers import parse_llm_json


VERIFIER_PROMPT = """\
You are a QA verification engine for web applications.

Core Principle: "Docs are reference; the live app is what we actually test."

## Scenario
{scenario}

## Expected Documented Behavior (Reference)
{doc_reference}

## Expected Result from Test Plan
{expected_result}

## Current Live Application State
URL: {url}
Title: {title}
Observed Network Summary: {network_summary}
Console Errors: {console_summary}
DOM Snippet:
{dom_snippet}

## Instructions
- Evaluate whether the actual live application state matches the expected behavior.
- If actual behavior matches expectation -> set passed=true, status="PASS".
- If actual behavior contradicts expectation or error indicator is present -> set passed=false, status="FAIL".
- If documented behavior differs from live design -> list specific items in "discrepancies".

Respond ONLY with a valid JSON object:
{{
  "passed": true | false,
  "status": "PASS" | "FAIL" | "BLOCKED" | "DISCREPANCY",
  "actual_result": "detailed description of what was actually observed",
  "discrepancies": ["list of specific mismatches"],
  "confidence": "high" | "medium" | "low"
}}
"""


async def verify_scenario(
    client: PlaywrightClient,
    scenario: dict[str, Any],
    expected_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Verify the application state after a scenario executes.

    Args:
        client: Active Playwright client.
        scenario: Executed scenario definition.
        expected_doc: Optional documented behavior reference.

    Returns:
        Dict with keys: passed, status, actual_result, discrepancies, confidence.
    """
    dom_snippet = await client.get_dom_snapshot()
    url = await client.get_url()
    title = await client.get_title()

    console_logs = client.get_console_logs()
    network_logs = client.get_network_logs()
    net_summary = f"{len(network_logs)} network calls recorded"

    prompt = VERIFIER_PROMPT.format(
        scenario=json.dumps(scenario, indent=2),
        doc_reference=json.dumps(expected_doc or {}, indent=2),
        expected_result=scenario.get("expected_result", ""),
        url=url,
        title=title,
        network_summary=net_summary,
        console_summary=json.dumps(console_logs[:5]),
        dom_snippet=dom_snippet[:3000],
    )

    try:
        response = await call_llm(system=SYSTEM_PROMPT, user=prompt)
        res = parse_llm_json(response)
        passed = res.get("passed", True)
        status = res.get("status", "PASS" if passed else "FAIL")
        return {
            "passed": passed,
            "status": status,
            "actual_result": res.get("actual_result", f"State verified on {url}"),
            "discrepancies": res.get("discrepancies", []),
            "confidence": res.get("confidence", "high"),
        }
    except Exception:
        # Graceful deterministic fallback: inspect URL and DOM directly
        has_login_redirect = "authorization/login" in url.lower() and "login" not in scenario.get("title", "").lower()
        has_error = "error" in dom_snippet.lower() or "not found" in dom_snippet.lower()

        if has_login_redirect:
            return {
                "passed": False,
                "status": "BLOCKED",
                "actual_result": f"Execution redirected to login page: {url}",
                "discrepancies": ["Authentication session expired or login required"],
                "confidence": "high",
            }

        passed = not has_error
        return {
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
            "actual_result": f"Verified DOM state on {url} (Title: {title}, Error detected: {has_error})",
            "discrepancies": ["Error indicator detected in DOM snippet"] if has_error else [],
            "confidence": "medium",
        }
