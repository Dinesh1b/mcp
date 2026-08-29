"""
mcp/agents/explorer_agent.py — Explorer Agent adapter for MCP.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from agent.explorer import explore_application

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


async def run_explorer_agent(ctx: "ExecutionContext", **kwargs: Any) -> dict[str, Any]:
    """Execute explorer agent for context's target module."""
    data = await explore_application(
        base_url=ctx.base_url,
        module_name=ctx.module_name,
    )
    ctx.exploration_data = data
    return {"status": "SUCCESS", "exploration_data": data}
