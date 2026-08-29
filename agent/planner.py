"""
agent/planner.py — LLM-driven test plan generator.

Receives a requirement string and produces structured test scenarios
by reasoning over the application's documentation and exploration data.
"""

from __future__ import annotations

import json
from typing import Any

from agent.llm import call_llm
from prompts import SYSTEM_PROMPT
from utils.helpers import parse_llm_json


PLANNER_PROMPT = """\
You are a QA test planner for web applications.

Given the following testing requirement and application exploration data,
generate a structured test plan in JSON format.

## Testing Requirement
{requirement}

## Application Exploration Data
{exploration_data}

## Instructions
- Identify the module, feature, and testing type.
- Generate test scenarios covering: Functional, Validation, Negative, CRUD, Search/Filter, and UI.
- For each scenario specify: id, title, type, preconditions, steps, expected_result.
- Use the exploration data to ground the steps in actual UI elements.
- Do NOT invent behavior not supported by the exploration data or requirement.
- If requirements are ambiguous, mark the scenario as status=GAP.

Respond ONLY with a valid JSON object matching this schema:
{{
  "module": "string",
  "feature": "string",
  "testing_types": ["string"],
  "scenarios": [
    {{
      "id": "TC_XXX_001",
      "title": "string",
      "type": "functional|validation|negative|crud|search|ui",
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
    memory_section = f"\n## Module Memory / Historical Knowledge\n{json.dumps(module_memory or {}, indent=2)}" if module_memory else ""
    prompt = PLANNER_PROMPT.format(
        requirement=requirement,
        exploration_data=json.dumps(exploration_data, indent=2) + memory_section,
    )

    try:
        response = await call_llm(system=SYSTEM_PROMPT, user=prompt)
        return parse_llm_json(response)
    except Exception as exc:
        # Fallback default plan based on requirement/module memory
        mod_key = (module_memory or {}).get("module", "audit").lower()
        mod_title = (module_memory or {}).get("display_name", mod_key.title())
        route = (module_memory or {}).get("default_route", f"/home/{mod_key}")
        
        return {
            "module": mod_key,
            "feature": requirement,
            "testing_types": ["functional", "validation", "ui"],
            "scenarios": [
                {
                    "id": f"TC_{mod_key[:3].upper()}_001",
                    "title": f"Verify {mod_title} navigation and primary dashboard load",
                    "type": "functional",
                    "preconditions": ["User is authenticated"],
                    "steps": [f"navigate to {route}", "wait for body"],
                    "expected_result": f"{mod_title} view is rendered and title is populated",
                    "status": "PLANNED",
                }
            ],
            "fallback_reason": str(exc),
        }
