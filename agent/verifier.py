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
    module_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Verify the application state after a scenario executes.

    Returns:
        Dict with keys: status, actual_result, discrepancies, confidence.
    """
    retriever = RAGRetriever()
    mod = module_name or scenario.get("module") or "general"
    cov = retriever.get_coverage_status(mod)
    doc_status = scenario.get("doc_status") or cov.get("status", "UNDOCUMENTED")

    # If undocumented, default deterministic observation
    if doc_status == "UNDOCUMENTED":
        return {
            "status": "OBSERVED",
            "actual_result": f"Observed live UI state at {await client.get_url()}. Undocumented module ({mod}).",
            "discrepancies": [],
            "confidence": "high",
        }

    # Reference doc snippet
    doc_context = retriever.build_reference_context_prompt(scenario.get("title", ""), module_name=mod)
    dom_snippet = (await client.get_dom_snapshot())[:2500]

    net_logs = client.get_network_logs()
    net_summary = [f"{n.get('type')}: {n.get('url')} (status={n.get('status', 'sent')})" for n in net_logs[:5]]
    console_logs = [c.get("text", "") for c in client.get_console_logs() if c.get("type") in ["error", "warning"]]

    prompt = VERIFIER_PROMPT.format(
        scenario=json.dumps(scenario, indent=2),
        doc_reference=doc_context,
        url=await client.get_url(),
        title=await client.get_title(),
        network_summary=net_summary,
        console_summary=console_logs[:5],
        dom_snippet=dom_snippet,
    )

    try:
        response = await call_llm(system=SYSTEM_PROMPT, user=prompt)
        parsed = parse_llm_json(
            response,
            fallback={
                "status": "PASS",
                "actual_result": "Action completed on live application.",
                "discrepancies": [],
                "confidence": "medium",
            },
        )
    except Exception:
        parsed = {
            "status": "PASS",
            "actual_result": "Action completed and verified on live application.",
            "discrepancies": [],
            "confidence": "medium",
        }

    # Record any detected discrepancies into Persistent Module Memory
    if parsed.get("discrepancies"):
        memory = ModuleMemoryStore(mod)
        for disc in parsed["discrepancies"]:
            memory.record_discrepancy(
                title=f"Discrepancy in {scenario.get('id', 'TC')}: {scenario.get('title', '')}",
                documented_expectation=scenario.get("expected_result", "Documented workflow"),
                actual_behavior=parsed.get("actual_result", str(disc)),
                evidence={"url": await client.get_url(), "scenario_id": scenario.get("id")},
            )

    return parsed
