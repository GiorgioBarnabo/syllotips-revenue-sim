# wake.py — dependency-free probe; only launches Playwright if needed
import os, sys, re, time
from pathlib import Path

APP_URL = os.environ.get("APP_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
if not APP_URL:
    raise SystemExit("Set APP_URL or pass the app URL as an argument")
APP_URL = APP_URL.rstrip("/") + "/?embed=true"

SLEEP_RE = re.compile(r"(gone to sleep|wake up|back up|get this app back|riattiva)", re.I)
AWAKE_HINTS = re.compile(r"(streamlit|data-testid=\"stapp|carry\-in|new arr|active aes)", re.I)

def tiny_png(path="wake_screenshot.png"):
    import base64
    b64 = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBoV0o5AsAAAAASUVORK5CYII="
    Path(path).write_bytes(base64.b64decode(b64))

def http_fetch(url):
    # stdlib HTTP client (no third-party deps)
    import urllib.request, urllib.error
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CI-wake/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            status = r.getcode()
            html = r.read().decode("utf-8", errors="ignore")
        return status, html
    except Exception:
        return 0, ""

def http_probe(url) -> bool:
    status, html = http_fetch(url)
    html_l = html.lower()
    return (
        status == 200
        and not SLEEP_RE.search(html_l)
        and AWAKE_HINTS.search(html_l)
    )

def browser_wake(url):
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="load", timeout=90_000)
        # Click wake/“Back up”/“Riattiva” if present
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
        tiny_png()  # leave a small artifact for the upload step
        return
    print("ℹ️  Probe suggests the app is asleep or ambiguous; opening browser…")
    browser_wake(APP_URL)
    if http_probe(APP_URL):
        print("✅ App is awake.")
    else:
        print("ℹ️  Visit completed; screenshot uploaded.")

if __name__ == "__main__":
    main()