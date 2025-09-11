# wake.py — robust wake for Streamlit Cloud via Playwright
import os, sys, time, re
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

APP_URL = os.environ.get("APP_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
if not APP_URL:
    raise SystemExit("Set APP_URL env var or pass the app URL as an argument")

WAKE_BUTTON_RE = re.compile(r"(wake|back up|get this app back)", re.I)
READY_SELECTORS = [
    '[data-testid="stAppViewContainer"]',
    '[data-testid="stSidebar"]',
    'text=SylloTips Revenue Journey Simulator',   # your page title
    'canvas[role="img"]',                          # Vega/Altair canvas
]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(APP_URL, wait_until="load", timeout=90_000)

        # Try to wake if sleeping banner is shown
        try:
            page.get_by_role("button", name=WAKE_BUTTON_RE).click(timeout=5_000)
            page.wait_for_load_state("networkidle", timeout=120_000)
        except PWTimeout:
            pass  # no wake button; likely already awake

        # Consider it ready if ANY of the selectors appears
        ready = False
        for sel in READY_SELECTORS:
            try:
                page.wait_for_selector(sel, timeout=30_000)
                ready = True
                break
            except PWTimeout:
                continue

        # Fallback: give it a little more time and try once more after reload
        if not ready:
            page.reload(wait_until="load")
            for sel in READY_SELECTORS:
                try:
                    page.wait_for_selector(sel, timeout=30_000)
                    ready = True
                    break
                except PWTimeout:
                    continue

        # Screenshot for debugging / proof
        time.sleep(2)
        page.screenshot(path="wake_screenshot.png")

        if ready:
            print("✅ App looks awake.")
        else:
            print("⚠️  Did not detect Streamlit container, but visit completed. "
                  "Check the screenshot artifact.")

        browser.close()

if __name__ == "__main__":
    main()