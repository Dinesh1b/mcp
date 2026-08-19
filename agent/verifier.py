"""
agent/verifier.py — Application state verification engine.

A successful UI action does NOT mean the test passed.
This module verifies the resulting state after each scenario.
"""

from __future__ import annotations

import json
from typing import Any

from agent.llm import call_llm
from mcp.playwright_client import PlaywrightClient
from prompts import SYSTEM_PROMPT
from utils.helpers import parse_llm_json


VERIFIER_PROMPT = """\
You are a QA verification engine.

A test scenario was executed. Evaluate whether the application's actual
state matches the expected result.

## Scenario
{scenario}

## Expected Result
{expected_result}

## Current Application State
URL: {url}
Title: {title}
DOM Snippet:
{dom_snippet}

## Instructions
- Compare the actual application state against the expected result.
- Do NOT assume the action succeeded just because the UI accepted it.
- Check: record created, correct values displayed, notifications shown, state persisted.
- Respond ONLY with a valid JSON object:
{{
  "passed": true | false,
  "actual_result": "string describing what was actually observed",
  "discrepancies": ["list of specific mismatches"],
  "confidence": "high|medium|low"
}}
"""


async def verify_scenario(
    client: PlaywrightClient,
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """
    Verify the application state after a scenario executes.

    Returns:
        Dict with keys: passed, actual_result, discrepancies, confidence.
    """
    dom_snippet = await client.get_dom_snapshot()
    prompt = VERIFIER_PROMPT.format(
        scenario=json.dumps(scenario, indent=2),
        expected_result=scenario.get("expected_result", ""),
        url=await client.get_url(),
        title=await client.get_title(),
        dom_snippet=dom_snippet,
    )
    response = await call_llm(system=SYSTEM_PROMPT, user=prompt)
    return parse_llm_json(
        response,
        fallback={
            "passed": False,
            "actual_result": f"Verifier returned unparseable response: {response[:200]}",
            "discrepancies": ["LLM response parse failure"],
            "confidence": "low",
        },
    )
