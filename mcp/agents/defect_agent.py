"""
mcp/agents/defect_agent.py — Defect Agent adapter for MCP.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from mcp.shared.defect_manager import detect_defects, save_defects

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


async def run_defect_agent(ctx: "ExecutionContext") -> dict[str, Any]:
    """Detect, classify, and persist defects for failed tests in context."""
    defects = await detect_defects(ctx)
    ctx.defects = defects
    saved_count = save_defects(ctx)
    return {"status": "SUCCESS", "defect_count": len(defects), "saved_count": saved_count}
