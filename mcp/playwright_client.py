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
        self._network_logs: list[dict[str, Any]] = []
        self._console_logs: list[dict[str, Any]] = []

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def __aenter__(self) -> "PlaywrightClient":
        await self.start()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.stop()

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        launcher = getattr(self._pw, self._browser_type, self._pw.chromium)
        try:
            self._browser = await launcher.launch(headless=self._headless)
        except Exception:
            # Fallback to system-installed Microsoft Edge or Google Chrome
            try:
                self._browser = await self._pw.chromium.launch(channel="msedge", headless=self._headless)
            except Exception:
                try:
                    self._browser = await self._pw.chromium.launch(channel="chrome", headless=self._headless)
                except Exception as e:
                    raise RuntimeError(
                        f"Could not launch browser. Please run 'playwright install' or install Chrome/Edge: {e}"
                    )
        context_kwargs: dict[str, Any] = {
            "viewport": {"width": 1280, "height": 800},
        }
        if self._storage_state:
            context_kwargs["storage_state"] = str(self._storage_state)
        self._context = await self._browser.new_context(**context_kwargs)
        self._context.set_default_timeout(settings.timeout)
        self._page = await self._context.new_page()

        # Attach network & console listeners
        self._page.on("request", self._handle_request)
        self._page.on("response", self._handle_response)
        self._page.on("console", self._handle_console)

    def _handle_request(self, request: Any) -> None:
        url = request.url
        if not any(url.endswith(ext) for ext in [".png", ".jpg", ".svg", ".css", ".woff", ".woff2", ".ico"]):
            self._network_logs.append({
                "type": "request",
                "method": request.method,
                "url": url,
                "headers": dict(list(request.headers.items())[:5]),
            })

    def _handle_response(self, response: Any) -> None:
        url = response.url
        if not any(url.endswith(ext) for ext in [".png", ".jpg", ".svg", ".css", ".woff", ".woff2", ".ico"]):
            self._network_logs.append({
                "type": "response",
                "status": response.status,
                "url": url,
                "ok": response.ok,
            })

    def _handle_console(self, msg: Any) -> None:
        self._console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "location": msg.location,
        })

    def get_network_logs(self) -> list[dict[str, Any]]:
        return list(self._network_logs)

    def get_console_logs(self) -> list[dict[str, Any]]:
        return list(self._console_logs)

    def clear_logs(self) -> None:
        self._network_logs.clear()
        self._console_logs.clear()

    async def extract_interactive_elements(self) -> list[dict[str, Any]]:
        """Extract interactive elements (buttons, inputs, links, selects) on the current page."""
        js_code = """() => {
            const elements = [];
            const queryAll = document.querySelectorAll('button, input, select, textarea, a, [role="button"]');
            queryAll.forEach((el, index) => {
                if (el.offsetParent !== null) { // visible
                    const tag = el.tagName.toLowerCase();
                    const type = el.getAttribute('type') || '';
                    const text = (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '').trim();
                    const id = el.id || '';
                    const name = el.getAttribute('name') || '';
                    const role = el.getAttribute('role') || '';
                    
                    let selector = '';
                    if (id) selector = `#${id}`;
                    else if (name) selector = `[name="${name}"]`;
                    else if (text && text.length < 30) selector = `text="${text}"`;
                    else selector = `${tag}:nth-of-type(${index + 1})`;

                    elements.push({
                        tag,
                        type,
                        text,
                        id,
                        name,
                        role,
                        selector,
                        placeholder: el.placeholder || '',
                    });
                }
            });
            return elements.slice(0, 50);
        }"""
        try:
            return await self.page.evaluate(js_code)
        except Exception:
            return []

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
