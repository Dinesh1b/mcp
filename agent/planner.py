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
from agent.repro_engine import ReproductionEngine


PLANNER_PROMPT = """\
You are a QA test planner for Stockount web applications.

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
- Use the **Documentation Reference Context** ONLY to understand terminology, business flows, or clarify unclear functionality. Do NOT blindly reproduce exact flows described in the documentation if they differ from the live state.
- If the module is UNDOCUMENTED (e.g., Sales, Purchases, Reports) or if the feature is not found in the docs:
  - You MUST STILL generate comprehensive test cases based on the discovered live state.
  - Mark testing_types as ["exploratory"] and doc_status as "UNDOCUMENTED".
  - Do NOT fabricate assumed ERP workflows (e.g., no assumed PO/PI/GRN if not present in the live data).
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
    Use the LLM to generate a structured test plan from a requirement
    and the application exploration data.

    Args:
        requirement: Free-text testing requirement (e.g. "Test Item Import in Inventory").
        exploration_data: Dict produced by the ApplicationExplorer.

    Returns:
        Parsed JSON test plan dict.
    """
    prompt = PLANNER_PROMPT.format(
        requirement=requirement,
        exploration_data=json.dumps(exploration_data, indent=2),
    )
    response = await call_llm(system=SYSTEM_PROMPT, user=prompt)
    return parse_llm_json(response)
