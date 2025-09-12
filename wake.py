from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import os, re, time

URL = os.environ["APP_URL"].rstrip("/") + "/?embed=true"

SLEEP_TEXT = re.compile(
    r"(?:\bzzzz\b|gone\s+to\s+sleep|wake\s+it\s+back\s+up|get\s+this\s+app\s+back\s+up|riattiva|torna\s+online)",
    re.I,
)
APP_READY_SELECTOR = '[data-testid="stAppViewContainer"], [data-testid^="stapp"]'

WAKE_BUTTON_SELECTORS = [
    'role=button[name=/get this app back up/i]',
    'text=/get this app back up/i',
    'role=button[name=/riattiva|torna online/i]',
    'text=/riattiva|torna online/i',
]

def wake():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 2200}, user_agent="CI-waker")
        page = ctx.new_page()

        # 1) Load
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

        # 2) If we can already see the app container, just screenshot and exit
        try:
            page.wait_for_selector(APP_READY_SELECTOR, timeout=3_000)
            page.screenshot(path="wake_screenshot.png", full_page=True)
            ctx.close(); browser.close()
            return
        except PWTimeout:
            pass

        # 3) If sleep page is there, click the wake button (be generous with selectors)
        try:
            # quick text sniff of the DOM
            dom_text = page.content().lower()
            sleeping = bool(SLEEP_TEXT.search(dom_text))

            if sleeping:
                clicked = False
                for sel in WAKE_BUTTON_SELECTORS:
                    loc = page.locator(sel)
                    if loc.count() > 0:
                        try:
                            loc.first.click(timeout=10_000)
                            clicked = True
                            break
                        except Exception:
                            pass
                if not clicked:
                    # fallback: click any visible primary button (sleep page has a single one)
                    page.locator("button").first.click(timeout=10_000)

            # 4) Wait for the app container to appear (cold start can take a bit)
            page.wait_for_selector(APP_READY_SELECTOR, timeout=120_000)
        except Exception:
            # Even if something goes wrong, take whatever we have for debugging
            pass
        finally:
            # Always save a screenshot for inspection
            try:
                page.screenshot(path="wake_screenshot.png", full_page=True)
            except Exception:
                pass
            ctx.close(); browser.close()

if __name__ == "__main__":
    wake()