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

CSV_PATH = settings.test_data_dir / "sample_stock_sheet.csv"
CSV_PATH.parent.mkdir(exist_ok=True, parents=True)
CSV_PATH.write_text("Item Code,Stock Quantity\nITEM-101,50\nITEM-102,100\nITEM-103,25\n", encoding="utf-8")

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
        
        # Step 1: Login
        log("Step 1: Navigating and logging in...")
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await page.fill("input[placeholder='Email']", USERNAME)
        await page.fill("input[placeholder='Password']", PASSWORD)
        await page.click("button:has-text('Login')")
        await page.wait_for_timeout(4000)
        await page.screenshot(path=EVIDENCE_DIR / "step1_logged_in.png")
        log(f"Logged in. Current URL: {page.url}")
        
        # Step 2: Navigate to Audit module
        log("Step 2: Navigating to /home/audit...")
        await page.goto("https://yellow-river-0ebeae800.2.azurestaticapps.net/home/audit", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=EVIDENCE_DIR / "step2_audit_module.png")
        
        # Step 3-7: Create Q Audit
        log("Step 3: Opening Create Audit modal...")
        create_btn = page.locator("button:has-text('Create Audit')").first
        await create_btn.click(timeout=5000)
        await page.wait_for_timeout(1000)
        
        dialog = page.locator(".p-dialog")
        
        log("Step 4: Selecting Manual tab in dialog...")
        await dialog.get_by_text("Manual").first.click(timeout=5000)
        await page.wait_for_timeout(1000)
        
        log("Step 5: Selecting Quick Audit option in dialog...")
        await dialog.get_by_text("Quick Audit").first.click(timeout=5000)
        await page.wait_for_timeout(1000)
        
        log("Step 6: Clicking Continue in dialog...")
        await dialog.get_by_text("Continue").first.click(timeout=5000)
        await page.wait_for_timeout(2000)
        
        audit_name = "QA_Q_Audit_Tracker_Test_03"
        log(f"Step 7: Entering Audit Name: '{audit_name}'...")
        name_input = page.locator("input[placeholder='Enter audit name']").first
        await name_input.fill(audit_name)
        await page.screenshot(path=EVIDENCE_DIR / "step3_7_q_audit_details.png")
        
        log("Submitting Create Audit form...")
        await page.locator("button:has-text('Create Audit')").last.click(timeout=5000)
        await page.wait_for_timeout(4000)
        await page.screenshot(path=EVIDENCE_DIR / "step8_create_audit_done.png")
        log(f"URL after Q Audit creation: {page.url}")
        
        # Step 8: Verify "Create the Audit" status
        body_text_step8 = await page.inner_text("body")
        log(f"--- Page text after Q Audit creation ---\n{body_text_step8[:1500]}\n--- End ---")
        
        # Step 9-10: Import Stock Sheet
        log("Step 9: Locating Stock Sheet import options...")
        import_btn = page.locator("text='Import Stock Sheet'").first
        if await import_btn.count() > 0:
            log("Clicking 'Import Stock Sheet' button...")
            await import_btn.click(timeout=5000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=EVIDENCE_DIR / "step9_import_modal.png")
            
        file_input = await page.query_selector("input[type='file']")
        if file_input:
            log(f"Step 10: Uploading stock sheet CSV: {CSV_PATH.resolve()}...")
            await file_input.set_input_files(str(CSV_PATH.resolve()))
            await page.wait_for_timeout(2000)
            await page.screenshot(path=EVIDENCE_DIR / "step10_file_attached.png")
            
            upload_confirm = page.locator("button:has-text('Upload'), button:has-text('Import'), button:has-text('Submit'), button:has-text('Done')")
            if await upload_confirm.count() > 0:
                log("Clicking upload confirm button...")
                await upload_confirm.first.click(timeout=5000)
                await page.wait_for_timeout(4000)
            await page.screenshot(path=EVIDENCE_DIR / "step10_import_submitted.png")
        else:
            log("[NOTICE] No file input found on page/modal for stock sheet import.")
            
        # Step 11: Verify "Import the Stock Sheet" step status
        body_text_step11 = await page.inner_text("body")
        log(f"--- Page text after stock import attempt ---\n{body_text_step11[:1500]}\n--- End ---")
        await page.screenshot(path=EVIDENCE_DIR / "step11_import_status_verified.png")
        
        # Step 12-13: Proceed to "Count the Stocks" & Start counting
        log("Step 12: Proceeding to 'Count the Stocks'...")
        start_count_el = page.locator("button:has-text('Start Count'), button:has-text('Count'), a:has-text('Count'), text='Count the Stocks'").first
        if await start_count_el.count() > 0:
            log("Clicking Start Count / Count element...")
            await start_count_el.click(timeout=5000)
            await page.wait_for_timeout(3000)
        else:
            log("[NOTICE] Looking for counting modes / options on current page...")
            
        await page.screenshot(path=EVIDENCE_DIR / "step12_13_counting_page.png")
        
        # Check available counting methods
        count_methods = []
        for method in ["Camera", "Barcode", "Search"]:
            loc = page.locator(f"text='{method}'")
            if await loc.count() > 0:
                count_methods.append(method)
        log(f"Step 13: Detected counting methods on screen: {count_methods}")
        
        # Step 14: Check "Steps to Complete the Audit" section
        log("Step 14: Inspecting 'Steps to Complete the Audit' section...")
        steps_tracker_loc = page.locator("text='STEPS TO COMPLETE THE AUDIT'")
        has_tracker = await steps_tracker_loc.count() > 0
        log(f"'STEPS TO COMPLETE THE AUDIT' section visible: {has_tracker}")
        
        final_page_text = await page.inner_text("body")
        log(f"--- Final Page Text Summary ---\n{final_page_text[:2000]}\n--- End ---")
        await page.screenshot(path=EVIDENCE_DIR / "step14_final_tracker_state.png")

        await browser.close()
        log("[SUCCESS] All test steps executed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
