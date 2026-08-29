"""
mcp/agents/validation_agent.py — Validation Agent adapter for MCP.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from agent.verifier import verify_scenario
from mcp.playwright_client import PlaywrightClient

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


async def run_validation_agent(
    client: PlaywrightClient,
    scenario: dict[str, Any],
    ctx: "ExecutionContext | None" = None,
) -> dict[str, Any]:
    """Validate scenario outcomes against actual state and documented rules."""
    expected_doc = None
    if ctx and ctx.module_documentation:
        behaviors = ctx.module_documentation.get("expected_behaviors", {})
        expected_doc = behaviors.get(scenario.get("type", "")) or behaviors.get(scenario.get("id", ""))

    return await verify_scenario(client, scenario, expected_doc=expected_doc)
