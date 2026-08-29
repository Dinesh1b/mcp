"""
agent/verifier.py — Multi-Level Application State & Discrepancy Verification Engine.

Implements Phase 5:
- Documented areas: Validate actual (live-app) behavior against documented expectations.
  If the app's actual behavior diverges from documentation, record it as a discrepancy finding.
- Undocumented areas: Explore the live application, capture UI/API behavior, and report findings
  as OBSERVED / UNVERIFIABLE; never fabricate expected results.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from agent.llm import call_llm
from mcp.playwright_client import PlaywrightClient
from prompts import SYSTEM_PROMPT
from utils.helpers import parse_llm_json
from knowledge.rag_retriever import RAGRetriever
from agent.memory_store import ModuleMemoryStore


VERIFIER_PROMPT = """\
You are a QA verification engine for Stockount.

Core Principle: "Docs are reference; the live app is what we actually test."

## Scenario
{scenario}

## Reference Documentation (Expectations)
{doc_reference}

## Current Live Application State
URL: {url}
Title: {title}
Observed Network Calls: {network_summary}
Console Errors: {console_summary}
DOM Snippet:
{dom_snippet}

## Instructions
- For DOCUMENTED modules: Compare the live app state against documented expectations.
  - If actual matches doc expectation -> status: "PASS".
  - If actual differs from doc expectation -> status: "DISCREPANCY" (describe mismatch precisely).
  - If actual application error occurred -> status: "FAIL".
- For UNDOCUMENTED modules:
  - Report findings strictly as status: "OBSERVED" (describe observed state) or "UNVERIFIABLE".
  - Never fabricate pass/fail judgments.

Respond ONLY with a valid JSON object:
{{
  "status": "PASS" | "FAIL" | "OBSERVED" | "UNVERIFIABLE" | "DISCREPANCY",
  "actual_result": "detailed description of what was observed",
  "discrepancies": ["list of specific doc vs app mismatches"],
  "confidence": "high" | "medium" | "low"
}}
"""


async def verify_scenario(
    client: PlaywrightClient,
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """
    Verify the application state after a scenario executes.

    Args:
        client: Active Playwright client.
        scenario: Executed scenario definition.
        expected_doc: Optional documented behavior reference.

    Returns:
        Dict with keys: passed, actual_result, discrepancies, confidence.
    """
    dom_snippet = await client.get_dom_snapshot()
    prompt = VERIFIER_PROMPT.format(
        scenario=json.dumps(scenario, indent=2),
        expected_result=scenario.get("expected_result", ""),
        url=await client.get_url(),
        title=await client.get_title(),
        network_summary=net_summary,
        console_summary=console_logs[:5],
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
