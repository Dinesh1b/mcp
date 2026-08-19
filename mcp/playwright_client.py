"""
mcp/playwright_client.py — Playwright MCP client wrapper.

Exposes a clean async API for browser automation actions.
The LLM decides WHAT to do; this module handles HOW to do it.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from config.settings import settings


class PlaywrightClient:
    """
    Thin async wrapper around Playwright.

    Usage:
        async with PlaywrightClient() as client:
            await client.navigate("https://example.com")
            title = await client.get_title()
    """

    def __init__(
        self,
        browser_type: Optional[str] = None,
        headless: Optional[bool] = None,
        storage_state: Optional[str | Path] = None,
    ) -> None:
        self._browser_type = browser_type or settings.browser
        self._headless = headless if headless is not None else settings.headless
        self._storage_state = storage_state

        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def __aenter__(self) -> "PlaywrightClient":
        await self.start()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.stop()

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        launcher = getattr(self._pw, self._browser_type)
        self._browser = await launcher.launch(headless=self._headless)
        context_kwargs: dict[str, Any] = {
            "viewport": {"width": 1280, "height": 800},
        }
        if self._storage_state:
            context_kwargs["storage_state"] = str(self._storage_state)
        self._context = await self._browser.new_context(**context_kwargs)
        self._context.set_default_timeout(settings.timeout)
        self._page = await self._context.new_page()

    async def stop(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    # ── Navigation ────────────────────────────────────────────────────────────

    async def navigate(self, url: str) -> None:
        await self.page.goto(url, wait_until="domcontentloaded")

    async def get_url(self) -> str:
        return self.page.url

    async def get_title(self) -> str:
        return await self.page.title()

    # ── Interaction ───────────────────────────────────────────────────────────

    async def click(self, selector: str) -> None:
        await self.page.click(selector)

    async def fill(self, selector: str, value: str) -> None:
        await self.page.fill(selector, value)

    async def select(self, selector: str, value: str) -> None:
        await self.page.select_option(selector, value)

    async def press(self, selector: str, key: str) -> None:
        await self.page.press(selector, key)

    async def hover(self, selector: str) -> None:
        await self.page.hover(selector)

    # ── Inspection ────────────────────────────────────────────────────────────

    async def get_text(self, selector: str) -> str:
        return (await self.page.text_content(selector)) or ""

    async def is_visible(self, selector: str) -> bool:
        return await self.page.is_visible(selector)

    async def is_enabled(self, selector: str) -> bool:
        return await self.page.is_enabled(selector)

    async def get_attribute(self, selector: str, attr: str) -> Optional[str]:
        return await self.page.get_attribute(selector, attr)

    async def evaluate(self, expression: str) -> Any:
        return await self.page.evaluate(expression)

    async def get_dom_snapshot(self) -> str:
        """Return a simplified DOM snapshot for LLM analysis."""
        return await self.page.content()

    # ── Waits ─────────────────────────────────────────────────────────────────

    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> None:
        await self.page.wait_for_selector(selector, timeout=timeout or settings.timeout)

    async def wait_for_url(self, url: str, timeout: Optional[int] = None) -> None:
        await self.page.wait_for_url(url, timeout=timeout or settings.timeout)

    async def wait_for_network_idle(self) -> None:
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

    # ── Evidence ─────────────────────────────────────────────────────────────

    async def screenshot(self, name: str) -> Path:
        path = settings.evidence_dir / "screenshots" / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=str(path), full_page=True)
        return path

    async def start_trace(self) -> None:
        await self._context.tracing.start(screenshots=True, snapshots=True)

    async def stop_trace(self, name: str) -> Path:
        path = settings.evidence_dir / "traces" / f"{name}.zip"
        path.parent.mkdir(parents=True, exist_ok=True)
        await self._context.tracing.stop(path=str(path))
        return path

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def save_storage_state(self, path: str | Path) -> None:
        await self._context.storage_state(path=str(path))

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("PlaywrightClient not started. Use 'async with' or call start().")
        return self._page
