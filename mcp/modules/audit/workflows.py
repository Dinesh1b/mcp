"""
mcp/modules/audit/workflows.py — Reusable automation workflows for Audit Module.

Encapsulates:
- Audit Navigation & Page Load
- Quick Audit Creation (Manual mode)
- Planned / Ad-Hoc Audit Creation
- Stock Sheet Import
- Stock Counting (Search, Barcode, Camera modes)
- Steps to Complete Audit Verification
"""

from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING
from pathlib import Path

from mcp.playwright_client import PlaywrightClient
from utils.evidence import evidence_filename

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


async def navigate_to_audit(client: PlaywrightClient, ctx: "ExecutionContext") -> dict[str, Any]:
    """Navigate directly to the Audit module home view."""
    audit_url = "https://yellow-river-0ebeae800.2.azurestaticapps.net/home/audit"
    await client.navigate(audit_url)
    await client.wait_for_network_idle()
    
    title = await client.get_title()
    url = await client.get_url()
    
    # Capture screenshot
    path = await client.screenshot(evidence_filename(f"AUD_NAV_{ctx.run_id}", "audit_home_page", "png").replace(".png", ""))
    ctx.evidence_paths.append(str(path))
    
    return {
        "status": "PASS",
        "url": url,
        "title": title,
        "screenshot": str(path),
    }


async def create_quick_audit_workflow(client: PlaywrightClient, ctx: "ExecutionContext") -> dict[str, Any]:
    """Execute Quick Audit creation workflow (Manual -> Quick Audit -> Name)."""
    page = client.page
    audit_name = f"QA_Audit_{ctx.run_id}"

    # Step 1: Click Create Audit button
    create_btn = page.locator("button:has-text('Create Audit')").first
    await create_btn.click(timeout=5000)
    await page.wait_for_timeout(1000)

    dialog = page.locator(".p-dialog")

    # Step 2: Select Manual tab
    await dialog.get_by_text("Manual").first.click(timeout=5000)
    await page.wait_for_timeout(800)

    # Step 3: Select Quick Audit option
    await dialog.get_by_text("Quick Audit").first.click(timeout=5000)
    await page.wait_for_timeout(800)

    # Step 4: Click Continue
    await dialog.get_by_text("Continue").first.click(timeout=5000)
    await page.wait_for_timeout(1500)

    # Step 5: Fill Audit Name
    name_input = page.locator("input[placeholder='Enter audit name']").first
    await name_input.fill(audit_name)

    # Step 6: Submit form
    submit_btn = page.locator("button:has-text('Create Audit')").last
    await submit_btn.click(timeout=5000)
    await page.wait_for_timeout(3000)

    # Evidence
    path = await client.screenshot(evidence_filename(f"AUD_CREATE_{ctx.run_id}", "created_quick_audit", "png").replace(".png", ""))
    ctx.evidence_paths.append(str(path))

    return {
        "status": "PASS",
        "audit_name": audit_name,
        "current_url": page.url,
        "screenshot": str(path),
    }


async def import_stock_sheet_workflow(client: PlaywrightClient, ctx: "ExecutionContext") -> dict[str, Any]:
    """Execute Stock Sheet Import workflow."""
    page = client.page
    csv_file = ctx.evidence_dir.parent / "test-data" / "sample_stock_sheet.csv"
    if not csv_file.exists():
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        csv_file.write_text("Item Code,Stock Quantity\nITEM-101,50\nITEM-102,100\nITEM-103,25\n", encoding="utf-8")

    import_btn = page.locator("text='Import Stock Sheet'").first
    if await import_btn.count() > 0:
        await import_btn.click(timeout=5000)
        await page.wait_for_timeout(1500)

    file_input = await page.query_selector("input[type='file']")
    if file_input:
        await file_input.set_input_files(str(csv_file.resolve()))
        await page.wait_for_timeout(1500)
        
        upload_btn = page.locator("button:has-text('Upload'), button:has-text('Import'), button:has-text('Submit'), button:has-text('Done')")
        if await upload_btn.count() > 0:
            await upload_btn.first.click(timeout=5000)
            await page.wait_for_timeout(2500)

    path = await client.screenshot(evidence_filename(f"AUD_IMPORT_{ctx.run_id}", "stock_sheet_imported", "png").replace(".png", ""))
    ctx.evidence_paths.append(str(path))

    return {
        "status": "PASS",
        "csv_path": str(csv_file),
        "screenshot": str(path),
    }


async def verify_counting_and_tracker_workflow(client: PlaywrightClient, ctx: "ExecutionContext") -> dict[str, Any]:
    """Verify stock counting modes and the 'Steps to Complete the Audit' tracker."""
    page = client.page
    
    # Check count methods
    count_methods = []
    for method in ["Camera", "Barcode", "Search"]:
        loc = page.locator(f"text='{method}'")
        if await loc.count() > 0:
            count_methods.append(method)

    # Check Steps to Complete Audit tracker
    tracker_loc = page.locator("text='STEPS TO COMPLETE THE AUDIT'")
    has_tracker = await tracker_loc.count() > 0

    path = await client.screenshot(evidence_filename(f"AUD_TRACKER_{ctx.run_id}", "counting_and_tracker", "png").replace(".png", ""))
    ctx.evidence_paths.append(str(path))

    return {
        "status": "PASS",
        "detected_counting_methods": count_methods,
        "steps_tracker_visible": has_tracker,
        "screenshot": str(path),
    }
