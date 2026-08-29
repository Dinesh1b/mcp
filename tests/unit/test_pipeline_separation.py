"""
tests/unit/test_pipeline_separation.py — Verifies pipeline stage separation and routing.

Tests:
1. Dynamic URL resolution helper
2. Stage 7 independent validation agent functionality
"""

from __future__ import annotations

import pytest
from mcp.core.routing import resolve_module_url
from mcp.core.execution_context import ExecutionContext
from mcp.agents.validation_agent import run_validation_agent


def test_dynamic_url_resolution():
    """Verify resolve_module_url handles various base URLs and routes without hardcoded hosts."""
    base_spa = "https://app.stockount.com/#/home/dashboard"
    base_std = "https://app.stockount.com"

    # Hash SPA routing
    assert resolve_module_url(base_spa, "/home/audit") == "https://app.stockount.com/#/home/audit"
    assert resolve_module_url(base_spa, "home/inventory") == "https://app.stockount.com/#/home/inventory"

    # Standard path routing
    assert resolve_module_url(base_std, "/home/audit") == "https://app.stockount.com/home/audit"
    assert resolve_module_url(base_std, "home/purchase/newpurchase") == "https://app.stockount.com/home/purchase/newpurchase"

    # Full URLs passed directly
    assert resolve_module_url(base_std, "https://custom.com/test") == "https://custom.com/test"


@pytest.mark.asyncio
async def test_validation_agent_evaluates_executed_scenarios():
    """Verify that run_validation_agent independently validates test execution states."""
    ctx = ExecutionContext(
        module_name="inventory",
        run_id="val_test_run",
        base_url="https://app.stockount.com",
    )

    # Mock executed scenarios from Stage 6
    ctx.test_results = [
        {
            "id": "TC_INV_001",
            "title": "Inventory Overview",
            "type": "functional",
            "status": "EXECUTED",
            "execution_state": {
                "url": "https://app.stockount.com/home/inventory",
                "title": "Stockount Inventory",
                "dom_snippet": "<div>Inventory Overview Table</div>",
            },
        },
        {
            "id": "TC_INV_002",
            "title": "Failed Search",
            "type": "search",
            "status": "EXECUTED",
            "execution_state": {
                "url": "https://app.stockount.com/home/inventory",
                "title": "Stockount Inventory",
                "dom_snippet": "<div>Error: 404 Item not found</div>",
            },
        },
    ]

    summary = await run_validation_agent(ctx)
    assert summary["status"] == "SUCCESS"
    assert summary["validated_count"] == 2
    assert summary["passed_count"] == 1
    assert summary["failed_count"] == 1

    # Check that verdicts were attached
    assert ctx.test_results[0]["status"] == "PASS"
    assert ctx.test_results[1]["status"] == "FAIL"
    assert ctx.test_results[0]["validation"]["validated"] is True
