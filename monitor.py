#!/usr/bin/env python3
import os, time, threading, logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PORT            = int(os.getenv("PORT",           "8000"))
PUSH_KEY        = os.getenv("PUSHOVER_USER_KEY")
PUSH_TOKEN      = os.getenv("PUSHOVER_API_TOKEN")
PRODUCT_URLS    = [u.strip() for u in os.getenv("PRODUCT_URLS","").split(",") if u.strip()]

# Default XPath: match ANY element containing “add to bag” (case-insensitive)
STOCK_SELECTOR = os.getenv("STOCK_SELECTOR",
    "//*[contains(translate(normalize-space(.),"
    " 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
    " 'add to bag')]"
)

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL","60"))  # seconds between cycles
PAGE_TIMEOUT   = int(os.getenv("PAGE_TIMEOUT","15"))    # max seconds to load page
WAIT_BEFORE    = 3    # seconds after load for JS & overlays

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ─── HEALTH CHECK ──────────────────────────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200); self.end_headers()

def start_health_server():
    srv = HTTPServer(("", PORT), HealthHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    logging.info(f"Health check listening on port {PORT}")

# ─── PUSHOVER ──────────────────────────────────────────────────────────────────
def send_pushover(msg: str):
    if not (PUSH_KEY and PUSH_TOKEN):
        logging.warning("Missing Pushover keys; skipping alert")
        return
    try:
        r = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={"token":PUSH_TOKEN, "user":PUSH_KEY, "message":msg},
            timeout=10
        )
        r.raise_for_status()
        logging.info("✔️ Pushover sent")
    except Exception as e:
        logging.error("Pushover error: %s", e)

# ─── SINGLE CHECK ──────────────────────────────────────────────────────────────
def check_stock(url: str):
    logging.info(f"→ START {url}")

    opts = Options()
    for a in ("--headless","--no-sandbox","--disable-dev-shm-usage"):
        opts.add_argument(a)
    opts.page_load_strategy = "eager"

    service = Service(os.getenv("CHROMEDRIVER_PATH","/usr/bin/chromedriver"))
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(PAGE_TIMEOUT)

    try:
        # 1) load page
        try:
            driver.get(url)
        except TimeoutException:
            logging.warning(f"⚠️ Page-load timeout; proceeding anyway")

        time.sleep(WAIT_BEFORE)

        # 2) dismiss any overlay
        ov = driver.find_elements(By.XPATH, "//div[contains(@class,'policy_acceptBtn')]")
        if ov:
            ov[0].click()
            logging.info("✓ Accepted overlay")
            time.sleep(1)

        # ── DEBUG #1: raw page_source check
        html = driver.page_source
        lower = html.lower()
        contains = "add to bag" in lower
        logging.info(f"   debug: page_source contains 'add to bag'? {contains}")
        if contains:
            idx = lower.find("add to bag")
            snippet = html[max(0, idx-80): idx+80].replace("\n"," ")
            logging.info(f"   debug snippet: …{snippet}…")

        # ── DEBUG #2: XPath element matches
        elems = driver.find_elements(By.XPATH, STOCK_SELECTOR)
        logging.info(f"   debug: STOCK_SELECTOR={STOCK_SELECTOR!r} matched {len(elems)} element(s)")
        for e in elems:
            logging.info(f"      → tag={e.tag_name!r}, text={e.text!r}")

        # ── alert logic
        if elems:
            msg = f"[{datetime.now():%H:%M}] IN STOCK → {url}"
            logging.info(msg)
            send_pushover(msg)
        else:
            logging.info("   out of stock")

    except Exception:
        logging.exception(f"Error on {url}")
    finally:
        driver.quit()
        logging.info(f"← END   {url}")

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────
def main():
    if not PRODUCT_URLS:
        logging.error("No PRODUCT_URLS set in env"); return

    start_health_server()
    # align start
    time.sleep(CHECK_INTERVAL - (time.time() % CHECK_INTERVAL))

    while True:
        logging.info("🔄 Cycle START")
        for u in PRODUCT_URLS:
            check_stock(u)
        logging.info("✅ Cycle END")
        time.sleep(CHECK_INTERVAL - (time.time() % CHECK_INTERVAL))

if __name__ == "__main__":
    main()
