"""
workflows/navigation.py — Application navigation helpers.
"""

from __future__ import annotations

from mcp.playwright_client import PlaywrightClient


async def navigate_to_module(client: PlaywrightClient, module_name: str) -> bool:
    """
    Attempt to navigate to a named module in the application.

    Tries menu links, sidebar links, and direct URL navigation.

    Returns:
        True if navigation succeeded, False otherwise.
    """
    # Try clicking a nav/sidebar link matching the module name
    selectors = [
        f"text={module_name}",
        f"a:has-text('{module_name}')",
        f"[aria-label='{module_name}']",
        f"[title='{module_name}']",
    ]
    for sel in selectors:
        try:
            await client.page.wait_for_selector(sel, timeout=2000)
            await client.click(sel)
            await client.wait_for_network_idle()
            return True
        except Exception:
            continue
    return False
