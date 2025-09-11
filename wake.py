# Wake the Streamlit app by visiting the URL and clicking the wake button if present.
# Saves a screenshot to wake_screenshot.png either way.

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

APP_URL = os.environ.get("APP_URL", "").strip()
if not APP_URL:
    print("ERROR: APP_URL environment variable not set.", file=sys.stderr)
    sys.exit(1)

URL = APP_URL.rstrip("/") + "/?embed=true"
SCREENSHOT = Path("wake_screenshot.png")

WAKE_BUTTON_TEXTS = [
    "Wake this app up",
    "Wake up",
    "Get this app back",
    "Back up",
    "Riattiva",  # Italian banner variant
]

SLEEP_TEXT_SNIPPETS = [
    "gone to sleep", "wake up", "riattiva", "get this app back", "back up"
]


def maybe_click_wake(page):
    # If sleep banner exists, click wake button (try a few variants)
    banner_present = False
    try:
        html = page.content().lower()
        banner_present = any(snippet in html for snippet in SLEEP_TEXT_SNIPPETS)
    except Exception:
        pass

    if not banner_present:
        return False

    for txt in WAKE_BUTTON_TEXTS:
        btn = page.get_by_role("button", name=txt)
        if btn and btn.count() > 0:
            try:
                btn.first.click(timeout=5000)
                return True
            except Exception:
                pass

    # Fallback: click any button in the banner region
    try:
        page.locator("button").first.click(timeout=5000)
        return True
    except Exception:
        return False


def wait_for_streamlit(page, timeout_ms=120_000):
    # Wait for Streamlit root or any well-known element to appear
    try:
        page.wait_for_selector('[data-testid="stApp"], .main, text=/streamlit/i', timeout=timeout_ms)
        return True
    except PWTimeout:
        return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 2000},
            user_agent="CI-waker",
        )
        page = context.new_page()
        status = "unknown"

        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

            clicked = maybe_click_wake(page)
            if clicked:
                # Give the app time to boot
                page.wait_for_load_state("networkidle", timeout=120_000)

            ready = wait_for_streamlit(page, timeout_ms=120_000 if clicked else 30_000)
            status = "awake" if ready else "not_ready"

            # Always try to capture something
            page.screenshot(path=str(SCREENSHOT), full_page=True)
        except Exception as e:
            status = f"error: {e}"
            # Best-effort partial screenshot
            try:
                page.screenshot(path=str(SCREENSHOT))
            except Exception:
                pass
        finally:
            context.close()
            browser.close()

        print(f"STATUS: {status}")


if __name__ == "__main__":
    main()