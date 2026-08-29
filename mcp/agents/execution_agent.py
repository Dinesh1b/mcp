"""
mcp/agents/execution_agent.py — Execution Agent adapter for MCP.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from agent.executor import execute_test_plan

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


async def run_execution_agent(ctx: "ExecutionContext", **kwargs: Any) -> dict[str, Any]:
    """Execute test plan scenarios with Playwright and record results."""
    results = await execute_test_plan(
        test_plan=ctx.test_plan,
        base_url=ctx.base_url,
        execution_context=ctx,
    )
    ctx.test_results = results
    return {"status": "SUCCESS", "test_results": results}
