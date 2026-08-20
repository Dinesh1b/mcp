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

Core Principle: "Docs are reference; the live app is what we actually test."

## Testing Requirement / Input
{requirement}

## Documentation Reference Context
{doc_reference}

## Known Persistent Module Memory (Prior Selectors & APIs)
{memory_summary}

## Application Exploration Data (Live State)
{exploration_data}

## Instructions
- Identify the module and its documentation status (DOCUMENTED or UNDOCUMENTED).
- If DOCUMENTED:
  - Create test scenarios grounded in the reference docs and live UI state.
  - Specify clear expected results to validate against the live app.
- If UNDOCUMENTED (e.g. Sales, Purchases, Reports):
  - Mark testing_types as ["exploratory"] and doc_status as "UNDOCUMENTED".
  - Do NOT fabricate assumed ERP workflows (no assumed PO/PI/GRN or SO/SI/DN).
  - Set expected_result to "Observe and document live application behavior and API responses."
- Ground steps in known selectors and interactive elements from exploration data and memory.

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
) -> dict[str, Any]:
    """
    Generate a structured, reference-grounded test plan.
    """
    retriever = RAGRetriever()
    repro = ReproductionEngine()

    # If it's a step sequence or structured input, let repro engine do first-pass normalization
    if "->" in requirement or "→" in requirement:
        return repro.parse_input(requirement)

    inferred_mod = ReproductionEngine._infer_module(requirement)
    doc_context = retriever.build_reference_context_prompt(requirement, module_name=inferred_mod)

    memory = ModuleMemoryStore(inferred_mod)
    mem_summary = memory.get_summary_for_llm()

    prompt = PLANNER_PROMPT.format(
        requirement=requirement,
        doc_reference=doc_context,
        memory_summary=json.dumps(mem_summary, indent=2),
        exploration_data=json.dumps(exploration_data, indent=2, default=str)[:3000],
    )

    response = await call_llm(system=SYSTEM_PROMPT, user=prompt)
    cov = retriever.get_coverage_status(inferred_mod)

    return parse_llm_json(
        response,
        fallback={
            "module": inferred_mod,
            "feature": requirement[:50],
            "doc_status": cov.get("status", "UNDOCUMENTED"),
            "testing_types": ["functional"],
            "scenarios": [
                {
                    "id": "TC_FALLBACK_001",
                    "title": requirement,
                    "type": "functional",
                    "doc_status": cov.get("status", "UNDOCUMENTED"),
                    "preconditions": [],
                    "steps": [requirement],
                    "expected_result": "Verify live application state.",
                    "status": "PLANNED",
                }
            ],
        },
    )
