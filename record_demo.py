import asyncio
import os
from playwright.async_api import async_playwright

URL = "http://localhost:8000"
USERNAME = "demo"
PASSWORD = "demo123"
OUT = r"E:\Outputs\SpellScroll_demo.webm"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, record_video_dir="E:\\Outputs", record_video_size={"width": 1440, "height": 900})
        page = await context.new_page()
        
        # 1. Open landing page
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        
        # 2. Login
        await page.fill('input[name="username"]', USERNAME)
        await page.wait_for_timeout(400)
        await page.fill('input[name="password"]', PASSWORD)
        await page.wait_for_timeout(400)
        await page.click('button:has-text("Enter the Archive")')
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        
        # 3. Interact with feed
        await page.click('button:has-text("Expand Feed")')
        await page.wait_for_timeout(4000)
        await page.screenshot(path="E:\\Outputs\\SpellScroll_feed.png")
        await page.wait_for_timeout(1500)
        
        # 4. Genre filter interaction
        genres = await page.query_selector_all('button:has-text("Romance"), button:has-text("Fantasy"), button:has-text("Action")')
        for btn in genres[:2]:
            try:
                await btn.click()
                await page.wait_for_timeout(800)
                break
            except Exception:
                pass
                
        await page.screenshot(path="E:\\Outputs\\SpellScroll_filtered.png")
        await page.wait_for_timeout(1500)
        
        # 5. API docs briefly
        await page.goto(URL + "/api/v1/docs", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="E:\\Outputs\\SpellScroll_api_docs.png")
        await page.wait_for_timeout(1000)
        
        # 6. Final feed
        await page.goto(URL + "/feed/", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="E:\\Outputs\\SpellScroll_final.png")
        
        await context.close()
        await browser.close()
        
        # Playwright saves videos on context close; rename to final path if present
        # Final path is typically auto-named; we just leave output dir populated
        print("Recording artifacts in E:\\Outputs")


if __name__ == "__main__":
    asyncio.run(main())
