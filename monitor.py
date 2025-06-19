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
PORT            = int(os.getenv("PORT", "8000"))
PUSH_KEY        = os.getenv("PUSHOVER_USER_KEY")
PUSH_TOKEN      = os.getenv("PUSHOVER_API_TOKEN")
PRODUCT_URLS    = [u.strip() for u in os.getenv("PRODUCT_URLS","").split(",") if u.strip()]

# If you’ve removed STOCK_SELECTOR from env, this default will be used:
STOCK_SELECTOR = os.getenv("STOCK_SELECTOR",
    "//*[contains(translate(normalize-space(.),"
    " 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
    " 'add to bag')]"
)

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL","60"))  # secs
PAGE_TIMEOUT   = int(os.getenv("PAGE_TIMEOUT","15"))    # secs to load page

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
        logging.warning("Missing Pushover keys; skipping")
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
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.page_load_strategy = "eager"

    service = Service(os.getenv("CHROMEDRIVER_PATH","/usr/bin/chromedriver"))
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(PAGE_TIMEOUT)

    try:
        # 1) load the page
        try:
            driver.get(url)
        except TimeoutException:
            logging.warning(f"⚠️  Page-load timeout; proceeding: {url}")

        # 2) wait a moment for JS & overlays
        time.sleep(3)

        # 3) dismiss any “Notify me” overlay
        overlay = driver.find_elements(By.XPATH, "//div[contains(@class,'policy_acceptBtn')]")
        if overlay:
            overlay[0].click()
            logging.info("✓ Accepted T&C overlay")
            time.sleep(1)

        # 4) DEBUG: find all matches for STOCK_SELECTOR
        elems = driver.find_elements(By.XPATH, STOCK_SELECTOR)
        logging.info(f"   debug: STOCK_SELECTOR={STOCK_SELECTOR!r} matched {len(elems)} element(s)")
        for e in elems:
            logging.info(f"      → tag={e.tag_name!r}, text={e.text!r}")

        # 5) alert if any found
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
        logging.error("No PRODUCT_URLS set in env")
        return

    start_health_server()
    # align to next minute
    time.sleep(CHECK_INTERVAL - (time.time() % CHECK_INTERVAL))

    while True:
        logging.info("🔄 Cycle START")
        for u in PRODUCT_URLS:
            check_stock(u)
        logging.info("✅ Cycle END")
        time.sleep(CHECK_INTERVAL - (time.time() % CHECK_INTERVAL))

if __name__ == "__main__":
    main()
