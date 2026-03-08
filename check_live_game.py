"""Check live site game page directly."""
import asyncio
import os

from playwright.async_api import async_playwright

BASE = "https://thechessfederation.pythonanywhere.com"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "screenshots", "live")
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # Login as TestPlayer
        await page.goto(BASE + "/login", wait_until="networkidle")
        await page.fill('input[name="username"]', "TestPlayer")
        await page.fill('input[name="password"]', "test1234")
        await page.click('button:has-text("Sign In")')
        await page.wait_for_load_state("networkidle")

        # Try game/1, game/2, game/3 to find a valid game
        for gid in [1, 2, 3]:
            await page.goto(f"{BASE}/game/{gid}", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            if page.url.endswith(f"/game/{gid}") and "404" not in await page.content():
                break

        await page.screenshot(path=os.path.join(OUTPUT_DIR, "04_chess_board.png"))
        squares = await page.locator("#chessBoard .sq").count()
        pieces = await page.locator("#chessBoard .piece").count()
        print(f"URL: {page.url}")
        print(f"Squares: {squares}, Pieces: {pieces}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
