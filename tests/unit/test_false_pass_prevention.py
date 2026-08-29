"""
tests/unit/test_false_pass_prevention.py — Regression tests to prevent false PASS returns.

Verifies that workflows return FAIL or BLOCKED whenever expected elements,
forms, or UI outcomes are missing, rather than returning a false PASS.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from mcp.core.execution_context import ExecutionContext
from mcp.modules.audit.workflows import (
    navigate_to_audit,
    create_quick_audit_workflow,
    import_stock_sheet_workflow,
    verify_counting_and_tracker_workflow,
)
from mcp.modules.inventory.workflows import (
    navigate_to_inventory,
    search_and_filter_workflow,
    verify_item_groups_workflow,
)
from mcp.modules.finance.workflows import (
    navigate_to_finance,
    purchase_form_validation_workflow,
)


@pytest.fixture
def dummy_ctx() -> ExecutionContext:
    ctx = ExecutionContext(
        module_name="test_module",
        run_id="test_run_123",
        base_url="https://test.stockount.com",
    )
    return ctx


def create_empty_mock_page():
    """Create a mock page where locators return 0 count / not visible by default."""
    page = MagicMock()
    mock_locator = MagicMock()
    mock_locator.first = mock_locator
    mock_locator.last = mock_locator
    mock_locator.count = AsyncMock(return_value=0)
    mock_locator.is_visible = AsyncMock(return_value=False)
    mock_locator.click = AsyncMock()
    mock_locator.fill = AsyncMock()
    mock_locator.get_by_text = MagicMock(return_value=mock_locator)
    
    page.locator = MagicMock(return_value=mock_locator)
    page.get_by_text = MagicMock(return_value=mock_locator)
    page.wait_for_timeout = AsyncMock()
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()
    page.url = "https://test.stockount.com/home/test"
    page.query_selector = AsyncMock(return_value=None)
    return page


@pytest.mark.asyncio
async def test_audit_navigation_returns_blocked_on_login_redirect(dummy_ctx: ExecutionContext):
    """Verify that when audit navigation redirects to login, it returns BLOCKED (never PASS)."""
    mock_client = AsyncMock()
    mock_client.navigate = AsyncMock()
    mock_client.wait_for_network_idle = AsyncMock()
    mock_client.get_title = AsyncMock(return_value="Login - Stockount")
    mock_client.get_url = AsyncMock(return_value="https://test.stockount.com/authorization/login")
    mock_client.screenshot = AsyncMock(return_value=dummy_ctx.evidence_dir / "sc.png")

    result = await navigate_to_audit(mock_client, dummy_ctx)
    assert result["status"] == "BLOCKED"
    assert "Redirected to login" in result["actual"]


@pytest.mark.asyncio
async def test_audit_create_quick_audit_fails_when_button_missing(dummy_ctx: ExecutionContext):
    """Verify that missing Create Audit button returns FAIL."""
    mock_client = AsyncMock()
    mock_client.page = create_empty_mock_page()
    mock_client.screenshot = AsyncMock(return_value=dummy_ctx.evidence_dir / "sc.png")

    result = await create_quick_audit_workflow(mock_client, dummy_ctx)
    assert result["status"] == "FAIL"
    assert "Missing 'Create Audit' button" in result["reason"]


@pytest.mark.asyncio
async def test_inventory_navigation_fails_when_controls_missing(dummy_ctx: ExecutionContext):
    """Verify that inventory navigation returns FAIL when UI controls are not found."""
    mock_client = AsyncMock()
    mock_client.navigate = AsyncMock()
    mock_client.wait_for_network_idle = AsyncMock()
    mock_client.get_title = AsyncMock(return_value="Stockount")
    mock_client.get_url = AsyncMock(return_value="https://test.stockount.com/home/inventory")
    mock_client.screenshot = AsyncMock(return_value=dummy_ctx.evidence_dir / "sc.png")
    mock_client.page = create_empty_mock_page()

    result = await navigate_to_inventory(mock_client, dummy_ctx)
    assert result["status"] == "FAIL"
    assert "Inventory UI failed to render controls" in result["reason"]


@pytest.mark.asyncio
async def test_inventory_search_fails_when_input_missing(dummy_ctx: ExecutionContext):
    """Verify that missing search input returns FAIL (not PASS)."""
    mock_client = AsyncMock()
    mock_client.page = create_empty_mock_page()
    mock_client.screenshot = AsyncMock(return_value=dummy_ctx.evidence_dir / "sc.png")

    result = await search_and_filter_workflow(mock_client, dummy_ctx)
    assert result["status"] == "FAIL"
    assert "Missing search input element" in result["reason"]


@pytest.mark.asyncio
async def test_finance_form_validation_fails_when_save_button_missing(dummy_ctx: ExecutionContext):
    """Verify that finance validation workflow returns FAIL when save button is missing."""
    mock_client = AsyncMock()
    mock_client.page = create_empty_mock_page()
    mock_client.screenshot = AsyncMock(return_value=dummy_ctx.evidence_dir / "sc.png")

    result = await purchase_form_validation_workflow(mock_client, dummy_ctx)
    assert result["status"] == "FAIL"
    assert "Missing Save/Submit action button" in result["reason"]
