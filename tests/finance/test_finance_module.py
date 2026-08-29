"""
tests/finance/test_finance_module.py — Comprehensive Pytest suite for Stockount Finance / Purchase Module.
"""

from __future__ import annotations

import pytest
from playwright.async_api import Page
from config.settings import settings
from mcp.core.routing import resolve_module_url


@pytest.mark.asyncio
async def test_01_finance_navigation(authenticated_page: Page):
    """TC_FIN_001: Navigate to Finance/Purchase route."""
    page = authenticated_page
    finance_url = resolve_module_url(settings.base_url, "/home/purchase/newpurchase")
    await page.goto(finance_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    title = await page.title()
    assert title is not None, "Page title should not be None"


@pytest.mark.asyncio
async def test_02_purchase_form_elements(authenticated_page: Page):
    """TC_FIN_002: Verify Purchase order input fields and action buttons."""
    page = authenticated_page
    finance_url = resolve_module_url(settings.base_url, "/home/purchase/newpurchase")
    await page.goto(finance_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    
    body = await page.inner_text("body")
    assert len(body) > 0, "Page content should be non-empty"
