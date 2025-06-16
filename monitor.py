#!/usr/bin/env python3
import os
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException

# Version 4: simplified detection

# Pushover credentials from environment
PUSHOVER_USER_KEY   = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_API_TOKEN  = os.getenv("PUSHOVER_API_TOKEN")
CHECK_INTERVAL      = int(os.getenv("CHECK_INTERVAL", "60"))
PRODUCT_URLS = [
    "https://www.jetpens.com/Uni-ball-ZENTO-Gel-Pen-Signature-Model-0.5-mm-Metallic-Black-Body-Black-Ink/pd/45351",
    "https://www.jetpens.com/Uni-ball-ZENTO-Gel-Pen-Signature-Model-0.38-mm-Silver-Body-Black-Ink/pd/45350"
]

if not PUSHOVER_USER_KEY or not PUSHOVER_API_TOKEN:
    print("❌ Missing Pushover credentials. Exiting.")
    exit(1)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_health_server():
    port = int(os.getenv("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"🔗 Health server listening on port {port}")
    server.serve_forever()

def send_pushover_message(msg: str):
    resp = requests.post("https://api.pushover.net/1/messages.json", data={
        "token": PUSHOVER_API_TOKEN,
        "user":  PUSHOVER_USER_KEY,
        "message": msg
    })
    if resp.ok:
        print(f"✅ Alert sent: {msg}")
    else:
        print(f"❌ Pushover error [{resp.status_code}]: {resp.text}")

def is_in_stock(driver, url: str) -> bool:
    # Simplified: in stock if 'Add to Cart' input exists.
    print(f"🔍 Checking {url}")
    driver.get(url)
    time.sleep(5)
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "input.add-to-cart")
        if elements:
            print("🟢 In stock (Add to Cart present)")
            return True
    except NoSuchElementException:
        pass
    print("🔴 Out of stock (Add to Cart missing)")
    return False

def monitor_loop():
    chrome_bin        = os.getenv("CHROME_BIN", "/usr/bin/chromium")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    opts = Options()
    opts.binary_location = chrome_bin
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")

    service = Service(executable_path=chromedriver_path)
    try:
        driver = webdriver.Chrome(service=service, options=opts)
        print("✅ Chrome WebDriver started")
    except WebDriverException as e:
        print(f"❌ WebDriver failed: {e}")
        return

    try:
        while True:
            print(f"🔁 Cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            for url in PRODUCT_URLS:
                try:
                    if is_in_stock(driver, url):
                        send_pushover_message(f"JetPens restocked!\n{url}")
                except Exception as e:
                    print(f"⚠️ Error checking {url}: {e}")
            print(f"⏳ Sleeping {CHECK_INTERVAL}s\n")
            time.sleep(CHECK_INTERVAL)
    finally:
        driver.quit()

if __name__ == "__main__":
    threading.Thread(target=start_health_server, daemon=True).start()
    monitor_loop()
