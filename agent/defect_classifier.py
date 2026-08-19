"""
agent/defect_classifier.py — Defect severity and priority assignment.

Severity levels:
  - Critical: System unusable / data corruption / security-critical
  - High:     Major functionality broken
  - Medium:   Important but workaround exists
  - Low:      Minor UI / cosmetic / low-impact
"""

from __future__ import annotations

import json
from typing import Any

from agent.llm import call_llm
from prompts import SYSTEM_PROMPT
from utils.helpers import parse_llm_json


CLASSIFIER_PROMPT = """\
You are a QA defect classifier.

Classify the severity and priority of the following defect based on business impact.

## Failed Scenario
{scenario}

## Failure Analysis
{failure_analysis}

## Severity Guidelines
- Critical: System unusable, data corruption, security-critical failure, major business process blocked.
- High: Major business functionality broken with significant impact.
- Medium: Important functionality affected but workaround exists.
- Low: Minor UI, cosmetic, usability, or low-impact behavior issue.

## Instructions
- Base severity on BUSINESS IMPACT, not ease of reproduction.
- Respond ONLY with valid JSON:
{{
  "severity": "critical|high|medium|low",
  "priority": "P1|P2|P3|P4",
  "impact": "string describing business impact",
  "reproducibility": "always|intermittent|rare",
  "defect_title": "string",
  "recommended_action": "string"
}}
"""


async def classify_defect(
    scenario: dict[str, Any],
    failure_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Classify defect severity and priority using LLM reasoning."""
    prompt = CLASSIFIER_PROMPT.format(
        scenario=json.dumps(scenario, indent=2),
        failure_analysis=json.dumps(failure_analysis, indent=2),
    )
    response = await call_llm(system=SYSTEM_PROMPT, user=prompt)
    return parse_llm_json(
        response,
        fallback={
            "severity": "medium",
            "priority": "P3",
            "impact": "Unable to classify — manual review required.",
            "reproducibility": "unknown",
            "defect_title": scenario.get("title", "Unknown Defect"),
            "recommended_action": "Manual review required.",
        },
    )
