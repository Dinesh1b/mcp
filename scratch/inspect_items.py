"""
scratch/inspect_items.py — List all items in the inventory sidebar.
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

        # Let's inspect the entire DOM hierarchy of the left panel and right panel
        panel_info = await page.evaluate("""() => {
            const allText = [];
            const walk = (node, depth) => {
                if (!node) return;
                if (node.nodeType === 3) {
                    const t = node.textContent.trim();
                    if (t) allText.push('  '.repeat(depth) + t);
                } else if (node.nodeType === 1) {
                    for (let child of node.childNodes) {
                        walk(child, depth + 1);
                    }
                }
            };
            walk(document.body, 0);
            return allText.slice(0, 100);
        }""")
        print("\n--- PAGE TEXT STRUCTURE (FIRST 100 LINES) ---")
        for line in panel_info[:60]:
            print(line)

        # Check all buttons and clickable elements on right panel
        buttons = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button, a, .btn, [role="button"], span.p-button-label')).map(el => ({
                tag: el.tagName,
                text: el.innerText ? el.innerText.trim() : el.textContent.trim(),
                className: el.className || '',
                id: el.id || ''
            })).filter(x => x.text.length > 0 && x.text.length < 50);
        }""")
        print("\n--- ALL BUTTONS ON PAGE ---")
        print(json.dumps(buttons, indent=2))

        # Check all headers and cards
        cards = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6, .id-card, .id-stat-card, [class*="card"]')).map(el => ({
                tag: el.tagName,
                className: el.className || '',
                text: (el.innerText || '').trim().replace(/\\n/g, ' | ').substring(0, 100)
            })).filter(x => x.text.length > 0);
        }""")
        print("\n--- ALL HEADERS AND CARDS ---")
        print(json.dumps(cards, indent=2))

        await b.close()

if __name__ == "__main__":
    asyncio.run(main())
