"""
mcp/agents/test_agent.py — Test Planner Agent adapter for MCP.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from agent.planner import generate_test_plan
from mcp.agents.memory_agent import load_memory

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


async def run_test_planner_agent(ctx: "ExecutionContext", requirement: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Generate structured test plan with module memory context."""
    req = requirement or f"Test the {ctx.module_name} module."
    memory = load_memory(ctx.module_name)
    test_plan = await generate_test_plan(
        requirement=req,
        exploration_data=ctx.exploration_data,
        module_memory=memory,
    )
    ctx.test_plan = test_plan
    return {"status": "SUCCESS", "test_plan": test_plan}
