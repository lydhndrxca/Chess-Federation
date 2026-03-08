"""Visit live Chess Federation site and capture screenshots."""
import asyncio
import os

try:
    from playwright.async_api import async_playwright
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "playwright"])
    subprocess.check_call(["playwright", "install", "chromium"])
    from playwright.async_api import async_playwright

BASE_URL = "https://thechessfederation.pythonanywhere.com"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "screenshots", "live")
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        # 1. Home page
        await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "01_home.png"))
        print("1. Screenshot: 01_home.png")

        # 2. Register TestPlayer (click "Join the Federation")
        await page.click("text=Join the Federation")
        await page.wait_for_load_state("networkidle")
        await page.fill('input[name="username"]', "TestPlayer")
        await page.fill('input[name="password"]', "test1234")
        await page.click('button:has-text("Create Account")')
        await page.wait_for_load_state("networkidle")

        # Check if we got "already taken" - if so, login instead
        if "register" in page.url.lower() or await page.locator("text=already taken").count() > 0:
            await page.goto(BASE_URL + "/login", wait_until="networkidle")
            await page.fill('input[name="username"]', "TestPlayer")
            await page.fill('input[name="password"]', "test1234")
            await page.click('button:has-text("Sign In")')
            await page.wait_for_load_state("networkidle")

        # 3. Dashboard (TestPlayer)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "02_dashboard_testplayer.png"))
        print("3. Screenshot: 02_dashboard_testplayer.png")

        # 4. Log out, register Rival
        await page.click("text=Logout")
        await page.wait_for_load_state("networkidle")
        await page.click("text=Join the Federation")
        await page.wait_for_load_state("networkidle")
        await page.fill('input[name="username"]', "Rival")
        await page.fill('input[name="password"]', "test1234")
        await page.click('button:has-text("Create Account")')
        await page.wait_for_load_state("networkidle")

        if "register" in page.url.lower() or await page.locator("text=already taken").count() > 0:
            await page.goto(BASE_URL + "/login", wait_until="networkidle")
            await page.fill('input[name="username"]', "Rival")
            await page.fill('input[name="password"]', "test1234")
            await page.click('button:has-text("Sign In")')
            await page.wait_for_load_state("networkidle")

        # 5. Log out, log in as TestPlayer
        await page.click("text=Logout")
        await page.wait_for_load_state("networkidle")
        await page.click("text=Sign In")
        await page.wait_for_load_state("networkidle")
        await page.fill('input[name="username"]', "TestPlayer")
        await page.fill('input[name="password"]', "test1234")
        await page.click('button:has-text("Sign In")')
        await page.wait_for_load_state("networkidle")

        # 6. Generate Weekly Pairings
        gen_btn = page.locator('button:has-text("Generate Weekly Pairings")')
        if await gen_btn.count() > 0:
            await gen_btn.click()
            await page.wait_for_load_state("networkidle")
        else:
            print("Note: Generate Weekly Pairings button not found")

        # 7. Dashboard with matchup
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "03_dashboard_matchup.png"))
        print("7. Screenshot: 03_dashboard_matchup.png")

        # 8. Click Play - get game URL first to ensure we go to the right place
        play_link = page.locator('a:has-text("Play")')
        game_href = None
        if await play_link.count() > 0:
            game_href = await play_link.first.get_attribute("href")
        if not game_href:
            view_link = page.locator('a[href*="/game/"]').first
            if await view_link.count() > 0:
                game_href = await view_link.get_attribute("href")
        if game_href:
            full_url = game_href if game_href.startswith("http") else BASE_URL + game_href
            await page.goto(full_url, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # 9. Chess board screenshot
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "04_chess_board.png"))
        print("9. Screenshot: 04_chess_board.png")

        # Board analysis
        board_squares = await page.locator("#chessBoard .sq").count()
        board_pieces = await page.locator("#chessBoard .piece").count()
        page_url = page.url
        print(f"\nFinal URL: {page_url}")
        print(f"Board squares: {board_squares}, pieces: {board_pieces}")

        await browser.close()
        print(f"\nScreenshots saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
