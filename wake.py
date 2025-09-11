# wake.py — uses Playwright to visit and "wake" a Streamlit app
import os, sys, time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

APP_URL = os.environ.get("APP_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
if not APP_URL:
    raise SystemExit("Set APP_URL env var or pass the app URL as an argument")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(APP_URL, wait_until="load", timeout=90_000)

        # If sleeping page shows up, click the wake button
        try:
            page.get_by_role("button", name="Yes, get this app back up!").click(timeout=5_000)
            # Give the app a moment to boot
            page.wait_for_load_state("networkidle", timeout=120_000)
        except PWTimeout:
            pass  # No sleeping banner—already awake

        # Basic sanity: wait for main app container to render
        try:
            page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=120_000)
        except PWTimeout:
            print("Warning: App container not detected—check logs.")

        # Keep it open a few seconds so Streamlit registers the visit
        time.sleep(5)
        # Optional: save a screenshot into CI artifacts
        page.screenshot(path="wake_screenshot.png")
        browser.close()

if __name__ == "__main__":
    main()