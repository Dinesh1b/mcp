import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add project root to path so config is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from config.settings import settings

EVIDENCE_DIR = settings.evidence_dir
EVIDENCE_DIR.mkdir(exist_ok=True, parents=True)

URL = settings.base_url
USERNAME = settings.qa_username
PASSWORD = settings.qa_password

def log(msg):
    print(msg, flush=True)

async def main():
    async with async_playwright() as p:
        log("[INFO] Starting Playwright Chromium browser...")
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        
        log("Logging in...")
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await page.fill("input[placeholder='Email']", USERNAME)
        await page.fill("input[placeholder='Password']", PASSWORD)
        await page.click("button:has-text('Login')")
        await page.wait_for_timeout(4000)
        
        log("Navigating to /home/audit...")
        await page.goto("https://yellow-river-0ebeae800.2.azurestaticapps.net/home/audit", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        log("Opening Quick Audit form...")
        await page.locator("button:has-text('Create Audit')").first.click()
        await page.wait_for_timeout(1000)
        await page.locator("text='Manual'").first.click()
        await page.wait_for_timeout(1000)
        await page.locator("text='Quick Audit'").first.click()
        await page.wait_for_timeout(1000)
        await page.locator("button:has-text('Continue')").first.click()
        await page.wait_for_timeout(2000)
        
        log("Entering Audit Name and Submitting...")
        await page.locator("input[placeholder='Enter audit name']").first.fill("Q Audit Test Tracker")
        await page.locator("button:has-text('Create Audit')").last.click()
        await page.wait_for_timeout(4000)
        
        await page.screenshot(path=EVIDENCE_DIR / "10_audit_settings_page.png")
        log(f"Current URL: {page.url}")
        
        log("Clicking 'Import Stock Sheet'...")
        try:
            import_btn = page.locator("text='Import Stock Sheet'").first
            await import_btn.click()
            await page.wait_for_timeout(2000)
        except Exception as e:
            log(f"Error clicking Import Stock Sheet: {e}")
            
        await page.screenshot(path=EVIDENCE_DIR / "11_import_stock_sheet_modal.png")
        
        body_text = await page.inner_text("body")
        log(f"Modal/Page text:\n{body_text[:2500]}")
        
        inputs = await page.query_selector_all("input")
        log(f"Found {len(inputs)} inputs on page:")
        for i, inp in enumerate(inputs):
            type_attr = await inp.get_attribute("type")
            name = await inp.get_attribute("name")
            id_attr = await inp.get_attribute("id")
            accept = await inp.get_attribute("accept")
            log(f"  Input {i}: type='{type_attr}', name='{name}', id='{id_attr}', accept='{accept}'")

        buttons = await page.query_selector_all("button, a, div[role='button']")
        log(f"Found {len(buttons)} visible buttons:")
        for b in buttons:
            txt = (await b.text_content()).strip()
            if txt and len(txt) < 80:
                log(f"  - '{txt}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
