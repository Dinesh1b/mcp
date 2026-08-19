"""
agent/failure_analyzer.py — Failure classification and analysis.

Determines whether a failure is an:
  - Application defect
  - Test defect
  - Environment issue
  - Data issue
  - Authentication issue
  - Network/API issue
  - Timing issue
"""

from __future__ import annotations

import json
from typing import Any

from agent.llm import call_llm
from mcp.playwright_client import PlaywrightClient
from prompts import SYSTEM_PROMPT
from utils.helpers import parse_llm_json


FAILURE_ANALYZER_PROMPT = """\
You are a QA failure analyst.

A test scenario has failed. Classify the failure and provide a structured analysis.

## Scenario
{scenario}

## Verification Result
{verification}

## Current Application State
URL: {url}
DOM Snippet:
{dom_snippet}

## Failure Classification Options
- application_defect: The application does not behave as expected.
- test_defect: The test steps or assertion are incorrect.
- environment_issue: Infrastructure, server, or configuration problem.
- data_issue: Missing or invalid test data.
- authentication_issue: Login, session, or permission failure.
- network_api_issue: API or network error.
- timing_issue: Race condition, slow response, or async problem.

## Instructions
- Reproduce independently in your reasoning.
- Only classify as application_defect if you have sufficient evidence.
- Respond ONLY with valid JSON:
{{
  "failure_type": "string",
  "explanation": "string",
  "reproduction_steps": ["string"],
  "reproducible": true | false,
  "should_retry": true | false,
  "suggested_investigation": "string"
}}
"""


async def analyze_failure(
    client: PlaywrightClient,
    scenario: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, Any]:
    """Classify and analyze a test failure using LLM reasoning."""
    dom_snippet = await client.get_dom_snapshot()
    prompt = FAILURE_ANALYZER_PROMPT.format(
        scenario=json.dumps(scenario, indent=2),
        verification=json.dumps(verification, indent=2),
        url=await client.get_url(),
        dom_snippet=dom_snippet,
    )
    response = await call_llm(system=SYSTEM_PROMPT, user=prompt)
    return parse_llm_json(
        response,
        fallback={
            "failure_type": "unknown",
            "explanation": response[:300],
            "reproduction_steps": [],
            "reproducible": False,
            "should_retry": False,
            "suggested_investigation": "Manual review required.",
        },
    )
