"""
scratch/inspect_inventory_dom.py — Inspect live Inventory page DOM in detail.
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

        print("[*] Navigating to /home/inventory...")
        await page.goto("https://yellow-river-0ebeae800.2.azurestaticapps.net/home/inventory")
        await page.wait_for_timeout(4000)

        # 1. Inputs
        inputs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input, select, textarea, [role="searchbox"], [role="combobox"]')).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.type || '',
                placeholder: el.placeholder || '',
                id: el.id || '',
                className: el.className || '',
                name: el.getAttribute('name') || '',
                ariaLabel: el.getAttribute('aria-label') || ''
            }));
        }""")
        print("\n--- ALL INPUTS ---")
        print(json.dumps(inputs, indent=2))

        # 2. All clickable items / list items
        list_items = await page.evaluate("""() => {
            const items = Array.from(document.querySelectorAll('.item-card, .list-item, tr, [role="row"], .p-datatable-tbody > tr, div.item, .item-name, h3, h4, h5, h6, span.font-bold'));
            return items.map(el => ({
                tag: el.tagName.toLowerCase(),
                className: el.className || '',
                text: el.innerText ? el.innerText.trim().replace(/\\n/g, ' | ') : ''
            })).filter(x => x.text.length > 0 && x.text.length < 150);
        }""")
        print("\n--- LIST / ITEM ELEMENTS (sample) ---")
        print(json.dumps(list_items[:25], indent=2))

        # 3. Check for text containing "Configuration" or "CONFIG" or "SEARCH"
        matches = await page.evaluate("""() => {
            const all = Array.from(document.querySelectorAll('*'));
            return all.filter(el => el.children.length === 0 && (el.textContent.includes('Config') || el.textContent.includes('CONFIG') || el.textContent.includes('Search') || el.textContent.includes('SEARCH') || el.textContent.includes('Delete') || el.textContent.includes('DELETE')))
                      .map(el => ({
                          tag: el.tagName.toLowerCase(),
                          parentTag: el.parentElement ? el.parentElement.tagName.toLowerCase() : '',
                          parentClass: el.parentElement ? el.parentElement.className : '',
                          text: el.textContent.trim(),
                          id: el.id || (el.parentElement ? el.parentElement.id : ''),
                          className: el.className || ''
                      }));
        }""")
        print("\n--- TEXT MATCHES (Config, Search, Delete) ---")
        print(json.dumps(matches, indent=2))

        # 4. Check right-hand panel / cards
        cards = await page.evaluate("""() => {
            const els = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6, .card-title, .p-card-title, div[class*="header"], div[class*="title"], div[class*="card"]'));
            return els.map(el => ({
                tag: el.tagName.toLowerCase(),
                class: el.className || '',
                text: el.innerText ? el.innerText.trim().substring(0, 100) : ''
            })).filter(x => x.text.length > 0 && x.text.length < 80);
        }""")
        print("\n--- TITLES AND CARDS ---")
        print(json.dumps(cards[:30], indent=2))

        await b.close()

if __name__ == "__main__":
    asyncio.run(main())
