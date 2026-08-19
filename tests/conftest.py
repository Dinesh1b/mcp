"""
tests/conftest.py — Pytest fixtures for AI QA Agent test suite.
"""

from __future__ import annotations

import asyncio
import pytest
from playwright.async_api import async_playwright, Browser, Page

from config.settings import settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    async with async_playwright() as pw:
        launcher = getattr(pw, settings.browser)
        b: Browser = await launcher.launch(headless=settings.headless)
        yield b
        await b.close()


@pytest.fixture
async def page(browser):
    context = await browser.new_context(viewport={"width": 1280, "height": 800})
    context.set_default_timeout(settings.timeout)
    p: Page = await context.new_page()
    yield p
    await context.close()


@pytest.fixture
async def authenticated_page(page):
    """Page fixture that navigates to base_url and performs login."""
    from workflows.login import perform_login
    from mcp.playwright_client import PlaywrightClient

    await page.goto(settings.base_url, wait_until="domcontentloaded")

    class _Wrapper:
        """Minimal PlaywrightClient-compatible wrapper for a pytest Page."""
        def __init__(self, _page: Page):
            self._page = _page
            self.page = _page

        async def fill(self, sel, val):
            await self._page.fill(sel, val)

        async def click(self, sel):
            await self._page.click(sel)

        async def get_url(self):
            return self._page.url

        async def get_title(self):
            return await self._page.title()

        async def wait_for_network_idle(self):
            try:
                await self._page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass

    wrapper = _Wrapper(page)
    await perform_login(wrapper)
    yield page
