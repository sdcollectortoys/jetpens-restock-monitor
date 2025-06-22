#!/usr/bin/env python3
import os
import sys
import time
import threading
import logging
import requests
from bs4 import BeautifulSoup
from flask import Flask, Response

# ----------------------
# Logging configuration
# ----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ----------------------
# Load Pushover creds
# ----------------------
PUSHOVER_API_TOKEN = os.environ.get("PUSHOVER_API_TOKEN")
PUSHOVER_USER_KEY   = os.environ.get("PUSHOVER_USER_KEY")

if not PUSHOVER_API_TOKEN or not PUSHOVER_USER_KEY:
    logging.error("Missing PUSHOVER_API_TOKEN or PUSHOVER_USER_KEY in environment; exiting.")
    sys.exit(1)

# ----------------------
# Load product URLs
# ----------------------
raw = os.environ.get("PRODUCT_URLS", "").strip()
if raw:
    PRODUCT_URLS = [u.strip() for u in raw.split(",") if u.strip()]
else:
    logging.warning("No PRODUCT_URLS set in env; falling back to built-in URLs")
    PRODUCT_URLS = [
        "https://www.jetpens.com/Uni-ball-ZENTO-Gel-Pen-Signature-Model-0.5-mm-Metallic-Black-Body-Black-Ink/pd/45351",
        "https://www.jetpens.com/Uni-ball-ZENTO-Gel-Pen-Signature-Model-0.38-mm-Silver-Body-Black-Ink/pd/45350"
    ]

if not PRODUCT_URLS:
    logging.error("No URLs to monitor (neither PRODUCT_URLS nor defaults present). Exiting.")
    sys.exit(1)

logging.info("→ Monitoring these URLs:\n  " + "\n  ".join(PRODUCT_URLS))

# ----------------------
# Pushover helper
# ----------------------
def send_notification(title: str, message: str):
    payload = {
        "token":   PUSHOVER_API_TOKEN,
        "user":    PUSHOVER_USER_KEY,
        "title":   title,
        "message": message
    }
    try:
        r = requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=10)
        r.raise_for_status()
        logging.info("Pushover notification sent")
    except Exception as e:
        logging.error(f"Failed to send Pushover notification: {e}")

# ----------------------
# Stock checker
# ----------------------
def check_stock(url: str) -> bool:
    """Return True if the page shows an 'Add to Cart' button, else False."""
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
    except Exception as e:
        logging.error(f"[{url}] Error fetching page: {e}")
        return False

    soup = BeautifulSoup(r.text, "html.parser")
    # JetPens uses <input class="add-to-cart" value="Add to Cart">
    btn = soup.find("input", {
        "class": "add-to-cart",
        "type":  "submit",
        "value": "Add to Cart"
    })
    return bool(btn)

# ----------------------
# Monitor loop
# ----------------------
last_status = {}  # url -> bool

def monitor_cycle():
    logging.info("🔄 Cycle START")
    for url in PRODUCT_URLS:
        logging.info(f"→ START {url}")
        in_stock = check_stock(url)
        prev = last_status.get(url, False)

        if in_stock:
            logging.info(f"[{url}] in stock")
            if not prev:
                # only notify when it newly comes in-stock
                send_notification("🔔 Back in stock!", url)
        else:
            logging.info(f"[{url}] out of stock")

        last_status[url] = in_stock

    logging.info("✅ Cycle END")

def scheduler():
    # run one immediately
    monitor_cycle()
    while True:
        # sleep until the top of the next minute
        now = time.time()
        delay = 60 - (now % 60)
        time.sleep(delay)
        monitor_cycle()

# ----------------------
# Flask health check
# ----------------------
app = Flask(__name__)

@app.route("/health")
def health():
    return Response("OK", status=200)

if __name__ == "__main__":
    # spawn the monitor thread
    t = threading.Thread(target=scheduler, daemon=True)
    t.start()

    logging.info("Health server listening on 0.0.0.0:8000/health")
    # Note: Flask's built-in server is fine for this; UptimeRobot will ping /health.
    app.run(host="0.0.0.0", port=8000)
