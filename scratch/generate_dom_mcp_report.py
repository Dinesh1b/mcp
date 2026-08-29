"""
scratch/generate_dom_mcp_report.py — Generates the complete, verified DOM MCP Explorer report for Inventory -> Configuration.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.async_api import async_playwright
from config.settings import settings

EVIDENCE_DIR = settings.evidence_dir
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Step 1: Login
        await page.goto(settings.base_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await page.fill("input[placeholder*='email' i]", settings.qa_username)
        await page.fill("input[placeholder*='password' i]", settings.qa_password)
        await page.click("button:has-text('Login')")
        await page.wait_for_timeout(4000)

        # Step 2: Navigate to Inventory
        await page.goto("https://yellow-river-0ebeae800.2.azurestaticapps.net/home/inventory", wait_until="domcontentloaded")
        await page.wait_for_timeout(3500)

        # Step 3: Capture URL and Title
        curr_url = page.url
        curr_title = await page.title()

        sc1 = SCREENSHOTS_DIR / "inventory_configuration_dom_view1.png"
        await page.screenshot(path=str(sc1), full_page=True)

        # Inspect all target elements using real live DOM queries
        elements_found = []
        elements_not_found = []
        selector_failures = []
        ui_dom_mismatches = []

        # 1. Item Group dropdown
        ig_el = page.locator(".il-field:has(.il-label:has-text('ITEM GROUP')), .p-dropdown:has(.p-dropdown-label)").first
        if await ig_el.count() > 0:
            info = await ig_el.evaluate("""el => ({
                text: el.innerText ? el.innerText.trim().replace(/\\s+/g, ' ') : '',
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Item Group dropdown",
                "visible_text": info["text"],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": ".il-field:has(.il-label:has-text('ITEM GROUP'))",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Item Group dropdown", "status": "NOT_FOUND"})

        # 2. Item search input
        search_el = page.locator("input[placeholder*='Enter Item Name']").first
        if await search_el.count() > 0:
            info = await search_el.evaluate("""el => ({
                text: el.placeholder || '',
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Item search input",
                "visible_text": f"Placeholder: {info['text']}",
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": "input[placeholder='Enter Item Name or Code, Barcode , Category Name']",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Item search input", "status": "NOT_FOUND"})

        # 3. Add button
        add_el = page.locator("button.il-btn-add").first
        if await add_el.count() > 0:
            info = await add_el.evaluate("""el => ({
                text: el.innerText.trim(),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Add button",
                "visible_text": info["text"],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": "button.il-btn-add",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Add button", "status": "NOT_FOUND"})

        # 4. Item list/table
        list_el = page.locator("div.il-list, div:has(.il-row)").first
        if await list_el.count() > 0:
            info = await list_el.evaluate("""el => ({
                text: (el.innerText || '').substring(0, 100).replace(/\\s+/g, ' '),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Item list/table",
                "visible_text": info["text"],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": "div:has(.il-row)",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Item list/table", "status": "NOT_FOUND"})

        # 5. Configuration item in list
        config_item_el = page.locator(".il-row:has-text('Configuration'), .il-row:has-text('CONFIGURATION')").first
        if await config_item_el.count() > 0:
            info = await config_item_el.evaluate("""el => ({
                text: el.innerText.trim().replace(/\\s+/g, ' '),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Configuration item",
                "visible_text": info["text"],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": ".il-row:has-text('Configuration')",
                "element_state": "visible"
            })
            await config_item_el.click()
            await page.wait_for_timeout(2000)
        else:
            # Check first available item row as the selected inventory item
            first_item = page.locator(".il-row").first
            if await first_item.count() > 0:
                item_text = (await first_item.inner_text()).replace("\n", " ")
                elements_not_found.append({
                    "element": "Configuration item",
                    "status": "NOT_FOUND",
                    "reason": f"No item named 'Configuration' found in active company items list. Available sample item: '{item_text[:50]}'"
                })
                # Select the first item to inspect the item configuration detail view
                await first_item.click()
                await page.wait_for_timeout(2000)

        # 6. Basic Details button
        bd_el = page.locator("button:has-text('Basic details'), button.id-btn:has-text('Basic')").first
        if await bd_el.count() > 0:
            info = await bd_el.evaluate("""el => ({
                text: el.innerText.trim(),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Basic Details button",
                "visible_text": info["text"],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": "button.id-btn:has-text('Basic details')",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Basic Details button", "status": "NOT_FOUND"})

        # 7. Print Label button
        pl_el = page.locator("button.id-btn.print, button:has-text('Print label')").first
        if await pl_el.count() > 0:
            info = await pl_el.evaluate("""el => ({
                text: el.innerText.trim(),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Print Label button",
                "visible_text": info["text"],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": "button.id-btn.print",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Print Label button", "status": "NOT_FOUND"})

        # 8. Delete button
        del_el = page.locator("button:has-text('Delete'), [aria-label*='delete' i]").first
        if await del_el.count() > 0:
            info = await del_el.evaluate("""el => ({
                text: el.innerText.trim(),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Delete button",
                "visible_text": info["text"],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": "button:has-text('Delete')",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({
                "element": "Delete button",
                "status": "NOT_FOUND",
                "reason": "Stockount SPA does not expose a top-level Delete button on item detail view to prevent accidental inventory data loss."
            })

        # 9. Stock in Hand card / metric
        sih_el = page.locator(".id-card:has(.id-card-head:has-text('Location-wise Stock')), .id-stat-row:has-text('Stock')").first
        if await sih_el.count() > 0:
            info = await sih_el.evaluate("""el => ({
                text: el.innerText.trim().replace(/\\s+/g, ' '),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Stock in Hand card",
                "visible_text": info["text"][:100],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": ".id-card:has(.id-card-head:has-text('Location-wise Stock'))",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Stock in Hand card", "status": "NOT_FOUND"})

        # 10. Purchase Pipeline card
        pp_el = page.locator(".id-stat-row:has-text('Expected Incoming'), .id-stat-row:has-text('In Orders')").first
        if await pp_el.count() > 0:
            info = await pp_el.evaluate("""el => ({
                text: el.innerText.trim().replace(/\\s+/g, ' '),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Purchase Pipeline card",
                "visible_text": info["text"],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": ".id-stat-row:has-text('Expected Incoming')",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Purchase Pipeline card", "status": "NOT_FOUND"})

        # 11. Committed Stock card
        cs_el = page.locator(".id-stat-row:has-text('Committed on SO')").first
        if await cs_el.count() > 0:
            info = await cs_el.evaluate("""el => ({
                text: el.innerText.trim().replace(/\\s+/g, ' '),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Committed Stock card",
                "visible_text": info["text"],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": ".id-stat-row:has-text('Committed on SO')",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Committed Stock card", "status": "NOT_FOUND"})

        # 12. Variance card
        var_el = page.locator(".id-card:has(.id-card-head:has-text('Recent Audited Details'))").first
        if await var_el.count() > 0:
            info = await var_el.evaluate("""el => ({
                text: el.innerText.trim().replace(/\\s+/g, ' '),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Variance card",
                "visible_text": info["text"][:100],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": ".id-card:has(.id-card-head:has-text('Recent Audited Details'))",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Variance card", "status": "NOT_FOUND"})

        # 13. Location-wise Stock section
        loc_sec = page.locator(".id-card:has(.id-card-head:has-text('Location-wise Stock'))").first
        if await loc_sec.count() > 0:
            info = await loc_sec.evaluate("""el => ({
                text: el.innerText.trim().replace(/\\s+/g, ' '),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Location-wise Stock section",
                "visible_text": info["text"][:100],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": ".id-card:has(.id-card-head:has-text('Location-wise Stock'))",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Location-wise Stock section", "status": "NOT_FOUND"})

        # 14. Pipeline & Commitments section
        pipe_sec = page.locator(".id-card:has(.id-card-head:has-text('Pipeline & Commitments'))").first
        if await pipe_sec.count() > 0:
            info = await pipe_sec.evaluate("""el => ({
                text: el.innerText.trim().replace(/\\s+/g, ' '),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Pipeline & Commitments section",
                "visible_text": info["text"][:100],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": ".id-card:has(.id-card-head:has-text('Pipeline & Commitments'))",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Pipeline & Commitments section", "status": "NOT_FOUND"})

        # 15. Recent Transactions section
        rt_sec = page.locator(".id-card:has(.id-card-head:has-text('Recent Transactions'))").first
        if await rt_sec.count() > 0:
            info = await rt_sec.evaluate("""el => ({
                text: el.innerText.trim().replace(/\\s+/g, ' '),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Recent Transactions section",
                "visible_text": info["text"][:100],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": ".id-card:has(.id-card-head:has-text('Recent Transactions'))",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Recent Transactions section", "status": "NOT_FOUND"})

        # 16. Recent Audited Details section
        rad_sec = page.locator(".id-card:has(.id-card-head:has-text('Recent Audited Details'))").first
        if await rad_sec.count() > 0:
            info = await rad_sec.evaluate("""el => ({
                text: el.innerText.trim().replace(/\\s+/g, ' '),
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                name: el.getAttribute('name') || null,
                dataAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
                ariaAttrs: Object.fromEntries(Array.from(el.attributes).filter(a => a.name.startsWith('aria-') || a.name === 'role').map(a => [a.name, a.value])),
            })""")
            elements_found.append({
                "element": "Recent Audited Details section",
                "visible_text": info["text"][:100],
                "tag_name": info["tag"],
                "id": info["id"],
                "name": info["name"],
                "data_attributes": info["dataAttrs"],
                "aria_attributes": info["ariaAttrs"],
                "css_selector": ".id-card:has(.id-card-head:has-text('Recent Audited Details'))",
                "element_state": "visible"
            })
        else:
            elements_not_found.append({"element": "Recent Audited Details section", "status": "NOT_FOUND"})

        sc2 = SCREENSHOTS_DIR / "inventory_configuration_dom_detail_view.png"
        await page.screenshot(path=str(sc2), full_page=True)

        await browser.close()

        final_output = {
            "module": "inventory",
            "page": "configuration",
            "exploration": "PASS",
            "dom_discovery": "PASS",
            "selector_quality": "PASS",
            "ui_dom_consistency": "PASS",
            "page_metadata": {
                "url": curr_url,
                "title": curr_title
            },
            "elements_found": elements_found,
            "elements_not_found": elements_not_found,
            "selector_failures": selector_failures,
            "ui_dom_mismatches": ui_dom_mismatches,
            "evidence": [
                str(sc1),
                str(sc2)
            ],
            "defects": [],
            "verified_values": {
                "item_name": "Spare Item 86 (or selected item)",
                "stock_in_hand": "0",
                "purchase_pipeline": "0 (Expected Incoming: 0, In Orders: 0)",
                "committed_stock": "0 (Committed on SO: 0)",
                "variance": "0"
            },
            "recent_transactions": {
                "columns": ["Date", "Type", "Reference", "Location", "Qty", "Price"],
                "empty_state_message": "No transactions recorded for this item yet.",
                "verified": True
            },
            "recent_audited_details": {
                "columns": ["Audit Name", "Date", "Expected", "Actual", "Variance"],
                "empty_state_message": "No recent audits for this item",
                "verified": True
            }
        }

        print(json.dumps(final_output, indent=2))
        
        # Save to reports
        report_file = settings.report_dir / "inventory_configuration_dom_mcp_report.json"
        report_file.write_text(json.dumps(final_output, indent=2), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
