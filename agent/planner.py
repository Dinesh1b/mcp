"""
agent/planner.py — LLM-driven test plan generator with Doc-Reference & Persistent Memory Grounding.

Receives a requirement string, step sequence, or repro request and produces structured
test scenarios grounded in:
1. Documentation reference context (RAG)
2. Live application exploration data
3. Persistent Module Memory (known selectors, prior results, discrepancies)
"""

from __future__ import annotations

import json
from typing import Any

from agent.llm import call_llm
from prompts import SYSTEM_PROMPT
from utils.helpers import parse_llm_json
from knowledge.rag_retriever import RAGRetriever
from agent.memory_store import ModuleMemoryStore


PLANNER_PROMPT = """\
You are a QA test planner for web applications.

Core Principle: "The Live Website is the primary source of truth. Docs are reference only."

## Testing Requirement / Input
{requirement}

## Documentation Reference Context (Use only for clarification)
{doc_reference}

## Known Persistent Module Memory (Prior Selectors, APIs & Flows)
{memory_summary}

## Application Exploration Data (Live State - PRIMARY SOURCE)
{exploration_data}

## Instructions
- Identify the module and its documentation status (DOCUMENTED or UNDOCUMENTED).
- Create test scenarios strictly grounded in the **Application Exploration Data (Live State)** and **Persistent Module Memory**.
- Ground steps entirely in known selectors, interactive elements, and forms from the live exploration data.
- Ensure all test steps use selectors that actually exist in the live UI.

Respond ONLY with a valid JSON object matching this schema:
{{
  "module": "string",
  "feature": "string",
  "doc_status": "DOCUMENTED" | "UNDOCUMENTED",
  "testing_types": ["string"],
  "scenarios": [
    {{
      "id": "TC_XXX_001",
      "title": "string",
      "type": "functional|validation|negative|crud|search|ui|exploratory",
      "doc_status": "DOCUMENTED" | "UNDOCUMENTED",
      "preconditions": ["string"],
      "steps": ["string"],
      "expected_result": "string",
      "status": "PLANNED|GAP"
    }}
  ]
}}
"""


async def generate_test_plan(
    requirement: str,
    exploration_data: dict[str, Any],
    module_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Use the LLM to generate a structured test plan from a requirement,
    application exploration data, and persistent module memory.

    Args:
        requirement: Free-text testing requirement (e.g. "Test Item Import in Inventory").
        exploration_data: Dict produced by the ApplicationExplorer.
        module_memory: Optional persistent knowledge about this module.

    Returns:
        Parsed JSON test plan dict.
    """
    mod_name = (module_memory or {}).get("module", "audit")
    retriever = RAGRetriever()
    doc_chunks = retriever.retrieve_relevant_chunks(requirement, module_name=mod_name, max_chunks=2)

    prompt = PLANNER_PROMPT.format(
        requirement=requirement,
        doc_reference=json.dumps(doc_chunks, indent=2),
        memory_summary=json.dumps(module_memory or {}, indent=2),
        exploration_data=json.dumps(exploration_data, indent=2),
    )

    try:
        response = await call_llm(system=SYSTEM_PROMPT, user=prompt)
        return parse_llm_json(response)
    except Exception as exc:
        mod_key = (module_memory or {}).get("module", "audit").lower()
        mod_title = (module_memory or {}).get("display_name", mod_key.title())
        route = (module_memory or {}).get("default_route", f"/home/{mod_key}")

        return {
            "module": mod_key,
            "feature": requirement,
            "doc_status": "DOCUMENTED",
            "testing_types": ["functional", "validation", "ui"],
            "scenarios": [
                {
                    "id": f"TC_{mod_key[:3].upper()}_001",
                    "title": f"Verify {mod_title} navigation and primary dashboard load",
                    "type": "functional",
                    "doc_status": "DOCUMENTED",
                    "preconditions": ["User is authenticated"],
                    "steps": [f"navigate to {route}", "wait for body"],
                    "expected_result": f"{mod_title} view is rendered and title is populated",
                    "status": "PLANNED",
                }
            ],
            "fallback_reason": str(exc),
        }
