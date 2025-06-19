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
PORT           = int(os.getenv("PORT", "8000"))
PUSH_KEY       = os.getenv("PUSHOVER_USER_KEY")
PUSH_TOKEN     = os.getenv("PUSHOVER_API_TOKEN")
PRODUCT_URLS   = [u.strip() for u in os.getenv("PRODUCT_URLS","").split(",") if u.strip()]
# XPath or CSS for “add to bag” (case-insensitive)
STOCK_SELECTOR = os.getenv("STOCK_SELECTOR",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
    " 'abcdefghijklmnopqrstuvwxyz'), 'add to bag')]"
).strip()
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL","60"))  # seconds
PAGE_TIMEOUT   = int(os.getenv("PAGE_TIMEOUT","15"))    # seconds

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
    logging.info(f"Health check on port {PORT}")

# ─── PUSHOVER ──────────────────────────────────────────────────────────────────
def send_pushover(msg: str):
    if not (PUSH_KEY and PUSH_TOKEN):
        logging.warning("Pushover keys missing; skipping")
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

# ─── STOCK CHECK ───────────────────────────────────────────────────────────────
def check_stock(url: str):
    logging.info(f"→ START {url}")
    chrome_opts = Options()
    chrome_opts.add_argument("--headless")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.page_load_strategy = "eager"

    service = Service(os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
    driver  = webdriver.Chrome(service=service, options=chrome_opts)
    driver.set_page_load_timeout(PAGE_TIMEOUT)

    try:
        try:
            driver.get(url)
        except TimeoutException:
            logging.warning(f"⚠️  Page-load timeout, continuing: {url}")

        time.sleep(3)  # allow JS & overlay to appear

        # dismiss T&C overlay if present
        overlays = driver.find_elements(
            By.XPATH, "//div[contains(@class,'policy_acceptBtn')]"
        )
        if overlays:
            overlays[0].click()
            logging.info("✓ Accepted T&C overlay")
            time.sleep(1)

        # look for “add to bag”
        if STOCK_SELECTOR.startswith("//"):
            elems = driver.find_elements(By.XPATH, STOCK_SELECTOR)
        else:
            elems = driver.find_elements(By.CSS_SELECTOR, STOCK_SELECTOR)

        if elems:
            msg = f"[{datetime.now():%H:%M}] IN STOCK → {url}"
            logging.info(msg)
            send_pushover(msg)
        else:
            logging.info("   out of stock")

    except Exception as e:
        logging.error("Error on %s: %s", url, e)
    finally:
        driver.quit()
        logging.info(f"← END   {url}")

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────
def main():
    if not PRODUCT_URLS:
        logging.error("No PRODUCT_URLS set in env")
        return

    start_health_server()
    # align to next minute boundary
    time.sleep(CHECK_INTERVAL - (time.time() % CHECK_INTERVAL))

    while True:
        logging.info("🔄 Cycle START")
        for u in PRODUCT_URLS:
            check_stock(u)
        logging.info("✅ Cycle END")
        time.sleep(CHECK_INTERVAL - (time.time() % CHECK_INTERVAL))

if __name__ == "__main__":
    main()
