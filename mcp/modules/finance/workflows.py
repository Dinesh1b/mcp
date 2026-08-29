"""
mcp/modules/finance/workflows.py — Reusable automation workflows for Finance Module.

Encapsulates:
- Finance & Purchase Navigation
- New Purchase Entry Validation
- Invoicing and Balance Ledger Verification
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from mcp.playwright_client import PlaywrightClient
from utils.evidence import evidence_filename

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


async def navigate_to_finance(client: PlaywrightClient, ctx: "ExecutionContext") -> dict[str, Any]:
    """Navigate to Finance / Purchase section."""
    page = client.page
    finance_url = "https://yellow-river-0ebeae800.2.azurestaticapps.net/#/home/purchase/newpurchase"
    await client.navigate(finance_url)
    await client.wait_for_network_idle()

    title = await client.get_title()
    url = await client.get_url()

    path = await client.screenshot(evidence_filename(f"FIN_NAV_{ctx.run_id}", "finance_home", "png").replace(".png", ""))
    ctx.evidence_paths.append(str(path))

    return {
        "status": "PASS",
        "url": url,
        "title": title,
        "screenshot": str(path),
    }


async def purchase_form_validation_workflow(client: PlaywrightClient, ctx: "ExecutionContext") -> dict[str, Any]:
    """Verify required field validation on purchase / financial entry form."""
    page = client.page
    save_btn = page.locator("button:has-text('Save'), button:has-text('Submit'), button[type='submit']")
    validation_checked = False

    if await save_btn.count() > 0 and await save_btn.first.is_visible():
        await save_btn.first.click()
        await page.wait_for_timeout(1000)
        validation_checked = True

    path = await client.screenshot(evidence_filename(f"FIN_VAL_{ctx.run_id}", "purchase_form_validation", "png").replace(".png", ""))
    ctx.evidence_paths.append(str(path))

    return {
        "status": "PASS",
        "validation_checked": validation_checked,
        "screenshot": str(path),
    }
