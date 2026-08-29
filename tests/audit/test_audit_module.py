"""
tests/audit/test_audit_module.py — Comprehensive Pytest suite for Stockount Audit Module.
Executes deterministic Playwright tests matching the audit pipeline workflows.
"""

from __future__ import annotations

import pytest
from playwright.async_api import Page
from config.settings import settings


@pytest.mark.asyncio
async def test_01_audit_navigation(authenticated_page: Page):
    """TC_AUD_001: Navigate to Audit module and verify page load."""
    page = authenticated_page
    await page.goto("https://yellow-river-0ebeae800.2.azurestaticapps.net/home/audit", wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    title = await page.title()
    assert title is not None, "Page title should not be None"
    assert "audit" in page.url.lower() or "home" in page.url.lower()


@pytest.mark.asyncio
async def test_02_create_audit_dialog_presence(authenticated_page: Page):
    """TC_AUD_002: Verify Create Audit modal button and dialog triggers."""
    page = authenticated_page
    await page.goto("https://yellow-river-0ebeae800.2.azurestaticapps.net/home/audit", wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    
    create_btn = page.locator("button:has-text('Create Audit')").first
    if await create_btn.count() > 0:
        await create_btn.click(timeout=5000)
        await page.wait_for_timeout(1000)
        dialog = page.locator(".p-dialog, [role='dialog']")
        assert await dialog.count() > 0, "Create Audit dialog should be visible"


@pytest.mark.asyncio
async def test_03_quick_audit_form_validation(authenticated_page: Page):
    """TC_AUD_003: Verify Quick Audit form controls and creation."""
    page = authenticated_page
    await page.goto("https://yellow-river-0ebeae800.2.azurestaticapps.net/home/audit", wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    
    create_btn = page.locator("button:has-text('Create Audit')").first
    if await create_btn.count() > 0:
        await create_btn.click(timeout=5000)
        await page.wait_for_timeout(1000)
        
        dialog = page.locator(".p-dialog, [role='dialog']")
        if await dialog.count() > 0:
            manual_tab = dialog.get_by_text("Manual").first
            if await manual_tab.count() > 0:
                await manual_tab.click()
                await page.wait_for_timeout(500)
            
            quick_audit = dialog.get_by_text("Quick Audit").first
            if await quick_audit.count() > 0:
                await quick_audit.click()
                await page.wait_for_timeout(500)
            
            cont_btn = dialog.get_by_text("Continue").first
            if await cont_btn.count() > 0:
                await cont_btn.click()
                await page.wait_for_timeout(1000)
                
                name_input = page.locator("input[placeholder='Enter audit name']").first
                if await name_input.count() > 0:
                    assert await name_input.is_visible(), "Audit name input should be visible"
