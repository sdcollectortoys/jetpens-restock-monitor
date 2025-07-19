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

# commas-separated list in your Render env
PRODUCT_URLS = os.getenv("PRODUCT_URLS", "").split(",")

PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
PUSHOVER_USER_KEY   = os.getenv("PUSHOVER_USER_KEY")

# Poll at top of every minute
SLEEP_INTERVAL = 60

# ─── Validation ────────────────────────────────────────────────────────────────

if not PRODUCT_URLS or PRODUCT_URLS == [""]:
    logging.error("No PRODUCT_URLS set in env")
    sys.exit(1)

if not (PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY):
    logging.error("PUSHOVER_API_TOKEN and PUSHOVER_USER_KEY must both be set")
    sys.exit(1)

# strip whitespace
PRODUCT_URLS = [u.strip() for u in PRODUCT_URLS if u.strip()]

# ─── Flask health check ───────────────────────────────────────────────────────

app = Flask(__name__)

@app.route("/health")
def health() -> Response:
    return Response("OK", status=200)

def start_health_server():
    # turn off Flask's reloader & debugging
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)

# ─── Push notification ────────────────────────────────────────────────────────

def send_push(title: str, message: str) -> None:
    """Send a Pushover notification."""
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
        logging.info(f"✅ Push sent: {title} → {message}")
    except Exception as e:
        logging.error(f"❌ Push error: {e}")

# ─── Stock checking ──────────────────────────────────────────────────────────

def check_stock(url: str) -> bool:
    """
    Returns True if the page contains an "Add to Cart" button,
    False otherwise (including on any fetch error).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/115.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:
        logging.error(f"[{url}] Error fetching page: {e}")
        return False

    soup = BeautifulSoup(r.text, "html.parser")
    btn = soup.find(
        "input",
        {
            "class": "add-to-cart",
            "type":  "submit",
            "value": "Add to Cart"
        }
    )
    return bool(btn)

# ─── Main monitor loop ────────────────────────────────────────────────────────

def monitor_loop():
    # track last-seen state so we only alert on transitions
    last_state = {url: False for url in PRODUCT_URLS}

    # wait until the top of the next minute
    time.sleep(SLEEP_INTERVAL - (time.time() % SLEEP_INTERVAL))

    while True:
        logging.info("🔄 Cycle START")
        for url in PRODUCT_URLS:
            logging.info(f"→ START {url}")
            in_stock = check_stock(url)

            # just came into stock?
            if in_stock and not last_state[url]:
                send_push("In Stock!", url)
            # just went out of stock? (we can log but not push)
            elif not in_stock and last_state[url]:
                logging.info(f"[{url}] went out of stock")

            last_state[url] = in_stock
            status = "in stock" if in_stock else "out of stock"
            logging.info(f"[{url}] {status}")
            logging.info(f"← END   {url}")

        logging.info("✅ Cycle END")
        # sleep until the top of the next minute
        time.sleep(SLEEP_INTERVAL - (time.time() % SLEEP_INTERVAL))

# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # standard logging format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # start health endpoint in background
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()

    # begin monitoring
    monitor_loop()
