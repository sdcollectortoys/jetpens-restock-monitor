#!/usr/bin/env python3
import os
import sys
import time
import logging
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask, Response

# ─── Configuration ────────────────────────────────────────────────────────────

# comma-separated list in your Render env
PRODUCT_URLS = os.getenv("PRODUCT_URLS", "").split(",")

PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
PUSHOVER_USER_KEY   = os.getenv("PUSHOVER_USER_KEY")

SLEEP_INTERVAL = 60  # seconds

# ─── Validation ────────────────────────────────────────────────────────────────

if not PRODUCT_URLS or PRODUCT_URLS == [""]:
    logging.error("No PRODUCT_URLS set in env")
    sys.exit(1)
if not (PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY):
    logging.error("PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY must both be set")
    sys.exit(1)

PRODUCT_URLS = [u.strip() for u in PRODUCT_URLS if u.strip()]

# ─── Flask health check ───────────────────────────────────────────────────────

app = Flask(__name__)

@app.route("/health")
def health() -> Response:
    return Response("OK", status=200)

def start_health_server():
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)

# ─── Pushover ─────────────────────────────────────────────────────────────────

def send_push(title: str, message: str) -> None:
    payload = {
        "token": PUSHOVER_API_TOKEN,
        "user":  PUSHOVER_USER_KEY,
        "title": title,
        "message": message,
    }
    try:
        r = requests.post(
            "https://api.pushover.net/1/messages.json",
            data=payload,
            timeout=10
        )
        r.raise_for_status()
        logging.info(f"✅ Push sent: {title}")
    except Exception as e:
        logging.error(f"❌ Push error: {e}")

# ─── Stock check ──────────────────────────────────────────────────────────────

session = requests.Session()

COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.jetpens.com/",
    "Origin":  "https://www.jetpens.com",
}

def check_stock(url: str) -> bool:
    """
    Checks whether an "Add to Cart" button is present.
    Returns True if so, False otherwise.
    """
    try:
        r = session.get(url, headers=COMMON_HEADERS, timeout=20)
        if r.status_code == 403:
            logging.warning(f"[{url}] 403 Forbidden – likely bot‐blocked")
            return False
        r.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"[{url}] Error fetching page: {e}")
        return False

    soup = BeautifulSoup(r.text, "html.parser")
    btn = soup.find(
        "input",
        {"class": "add-to-cart", "type": "submit", "value": "Add to Cart"}
    )
    return bool(btn)

# ─── Monitor loop ────────────────────────────────────────────────────────────

def monitor_loop():
    last_state = {url: False for url in PRODUCT_URLS}
    # align to top of minute
    time.sleep(SLEEP_INTERVAL - (time.time() % SLEEP_INTERVAL))

    while True:
        logging.info("🔄 Cycle START")
        for url in PRODUCT_URLS:
            logging.info(f"→ START {url}")
            in_stock = check_stock(url)

            # on False→True only
            if in_stock and not last_state[url]:
                send_push("In Stock!", url)

            # log transition to out‐of‐stock
            if not in_stock and last_state[url]:
                logging.info(f"[{url}] went out of stock")

            last_state[url] = in_stock
            status = "in stock" if in_stock else "out of stock"
            logging.info(f"[{url}] {status}")
            logging.info(f"← END   {url}")

        logging.info("✅ Cycle END")
        time.sleep(SLEEP_INTERVAL - (time.time() % SLEEP_INTERVAL))

# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # start health check
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()

    # run monitor
    monitor_loop()
