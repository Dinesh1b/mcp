"""
agent/explorer.py — Application exploration using Playwright MCP.

Logs into the application, navigates key sections, and captures
the UI structure for the LLM to reason over.
"""

from __future__ import annotations

from typing import Any

from mcp.playwright_client import PlaywrightClient
from config.settings import settings
from workflows.login import perform_login


async def explore_application(base_url: str | None = None) -> dict[str, Any]:
    """
    Explore the application and return a structured snapshot of its UI.

    Returns:
        Dict describing pages, navigation, and key elements observed.
    """
    url = base_url or settings.base_url
    exploration: dict[str, Any] = {
        "base_url": url,
        "pages": [],
    }

    async with PlaywrightClient() as client:
        # Login
        await client.navigate(url)
        await perform_login(client)

        # Capture post-login state
        page_entry = await _capture_page_state(client, "dashboard")
        exploration["pages"].append(page_entry)

        # Discover top-level nav items
        nav_links = await _discover_nav_links(client)
        exploration["nav_links"] = nav_links

        # Visit each nav link and capture state
        for link in nav_links[:10]:  # Limit to first 10 to avoid runaway exploration
            try:
                await client.click(link["selector"])
                await client.wait_for_network_idle()
                page_entry = await _capture_page_state(client, link["label"])
                exploration["pages"].append(page_entry)
            except Exception as exc:
                exploration["pages"].append(
                    {"label": link["label"], "error": str(exc)}
                )

    return exploration


async def _capture_page_state(client: PlaywrightClient, label: str) -> dict[str, Any]:
    """Capture the current page state for LLM analysis."""
    return {
        "label": label,
        "url": await client.get_url(),
        "title": await client.get_title(),
        "dom_snippet": (await client.get_dom_snapshot())[:3000],  # Trim for LLM context
    }


async def _discover_nav_links(client: PlaywrightClient) -> list[dict[str, Any]]:
    """Discover top-level navigation links."""
    links: list[dict[str, Any]] = []
    try:
        elements = await client.page.query_selector_all("nav a, [role='navigation'] a, aside a")
        for el in elements[:20]:
            text = (await el.text_content() or "").strip()
            href = await el.get_attribute("href") or ""
            if text:
                links.append({"label": text, "href": href, "selector": f"text={text}"})
    except Exception:
        pass
    return links
