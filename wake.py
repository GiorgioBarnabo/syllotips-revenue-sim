# wake.py  — fast probe first; only open a browser if the app is asleep
import os, sys, re, time
from pathlib import Path

APP_URL = os.environ.get("APP_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
if not APP_URL:
    raise SystemExit("Set APP_URL or pass the app URL as an argument")
APP_URL = APP_URL.rstrip("/") + "/?embed=true"

SLEEP_RE = re.compile(r"(gone to sleep|wake up|back up|get this app back|riattiva)", re.I)
AWAKE_HINTS = re.compile(r"(streamlit|data-testid=\"stapp|carry\-in|new arr|active aes)", re.I)

def tiny_png(path="wake_screenshot.png"):
    # 1x1 PNG to satisfy the artifact step without Playwright
    import base64
    b64 = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBoV0o5AsAAAAASUVORK5CYII="
    Path(path).write_bytes(base64.b64decode(b64))

def http_probe(url) -> bool:
    try:
        import requests
        r = requests.get(url, timeout=30, headers={"User-Agent": "CI-wake/1.0"})
        html = r.text.lower()
        if r.status_code == 200 and not SLEEP_RE.search(html) and AWAKE_HINTS.search(html):
            return True
    except Exception:
        pass
    return False

def browser_wake(url):
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="load", timeout=90_000)
        # try clicking a wake button if shown (multi-language)
        try:
            page.get_by_role("button", name=re.compile(r"(wake|back up|riattiva)", re.I)).click(timeout=4000)
            page.wait_for_load_state("domcontentloaded", timeout=120_000)
        except PWTimeout:
            pass
        time.sleep(1.5)
        page.screenshot(path="wake_screenshot.png")
        browser.close()

def main():
    if http_probe(APP_URL):
        print("✅ App already awake — skipping browser.")
        tiny_png()  # create a small artifact so the workflow step succeeds
        return

    print("ℹ️  Probe suggests the app is asleep or ambiguous; opening browser…")
    browser_wake(APP_URL)
    # Final soft probe (no warning noise)
    if http_probe(APP_URL):
        print("✅ App is awake.")
    else:
        print("ℹ️  Visit completed; screenshot uploaded.")

if __name__ == "__main__":
    main()