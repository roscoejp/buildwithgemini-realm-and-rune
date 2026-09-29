import asyncio
import os
import glob
from playwright.async_api import async_playwright

APP_URL = "https://realm-and-rune-frontend-1053681111416.us-central1.run.app"
ARTIFACT_DIR = "/config/.gemini/antigravity/brain/04f314ed-094d-43f3-9c29-0ecffcca5297"

async def record():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=ARTIFACT_DIR,
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        
        print("Navigating to app...")
        await page.goto(APP_URL)
        await page.wait_for_timeout(2000)
        
        # 1. First prompt: Owlbear stat card
        print("Submitting first prompt (Owlbear Stat Card)...")
        await page.click("text=Owlbear Stat Card")
        
        # Wait for agent card to render
        print("Waiting for Owlbear card...")
        await page.wait_for_selector(".a2card", timeout=30000)
        await page.wait_for_timeout(4000)
        
        # Toggle Dark Mode in header
        print("Toggling Dark Mode...")
        await page.click("#theme-toggle")
        await page.wait_for_timeout(2000)
        
        # 2. Second prompt: Richer prompt with tool call / spell lookup
        print("Submitting second prompt (Look up spell Fireball)...")
        await page.fill("#input", "Look up spell Fireball")
        await page.click("button.send-btn")
        
        # Wait for second card to render
        print("Waiting for Fireball spell card...")
        await page.wait_for_timeout(10000)
        
        await page.wait_for_timeout(3000)
        await context.close()
        await browser.close()
        print("Recording finished.")

if __name__ == "__main__":
    asyncio.run(record())
