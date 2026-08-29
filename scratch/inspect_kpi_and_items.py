"""
scratch/inspect_kpi_and_items.py — Inspect KPI cards and search items on /home/inventory.
"""

import asyncio
import json
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

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(settings.base_url)
        await page.wait_for_timeout(2000)
        await page.fill("input[placeholder*='email' i]", settings.qa_username)
        await page.fill("input[placeholder*='password' i]", settings.qa_password)
        await page.click("button:has-text('Login')")
        await page.wait_for_timeout(4000)
        
        await page.goto("https://yellow-river-0ebeae800.2.azurestaticapps.net/home/inventory")
        await page.wait_for_timeout(3500)

        # 1. Search for "Configuration" or check all items on all pages
        search_input = page.locator("input[placeholder*='Enter Item Name']")
        print("Filling search input with 'Configuration'...")
        await search_input.fill("Configuration")
        await page.wait_for_timeout(2000)

        # Check item list after search
        search_results = await page.evaluate("""() => {
            const items = Array.from(document.querySelectorAll('.il-item, .il-card, [class*="item-row"], [class*="il-"], div[class*="item"]')).map(el => ({
                tag: el.tagName,
                className: el.className,
                text: (el.innerText || '').trim().replace(/\\n/g, ' | ')
            })).filter(x => x.text.length > 0 && x.text.length < 150);
            return items;
        }""")
        print("\n--- SEARCH RESULTS FOR 'Configuration' ---")
        print(json.dumps(search_results[:20], indent=2))

        # Check all KPI/Stat cards in right panel
        kpi_cards = await page.evaluate("""() => {
            const cards = Array.from(document.querySelectorAll('.id-stat, .id-metric, .stat-card, .kpi, [class*="stat"], [class*="metric"], [class*="badge"], div.id-hero div, div.id-header div')).map(el => ({
                tag: el.tagName,
                className: el.className,
                text: (el.innerText || '').trim().replace(/\\n/g, ' | ')
            })).filter(x => x.text.length > 0 && x.text.length < 100);
            return cards;
        }""")
        print("\n--- KPI STAT CARDS ---")
        print(json.dumps(kpi_cards[:30], indent=2))

        # Check if clicking "Basic details" opens a modal with a Delete button
        bd_btn = page.locator("button:has-text('Basic details')")
        if await bd_btn.count() > 0:
            print("\nClicking 'Basic details' button...")
            await bd_btn.first.click()
            await page.wait_for_timeout(2000)

            modal_buttons = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('.p-dialog button, .modal button, [role="dialog"] button')).map(el => ({
                    text: el.innerText ? el.innerText.trim() : el.textContent.trim(),
                    className: el.className,
                    ariaLabel: el.getAttribute('aria-label') || ''
                }));
            }""")
            print("Buttons in Basic Details modal:", json.dumps(modal_buttons, indent=2))

        await b.close()

if __name__ == "__main__":
    asyncio.run(main())
