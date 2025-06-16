
import os
import time
import requests
from bs4 import BeautifulSoup

PRODUCT_URLS = [
    "https://www.jetpens.com/Uni-ball-ZENTO-Gel-Pen-Signature-Model-0.5-mm-Metallic-Black-Body-Black-Ink/pd/45351",
    "https://www.jetpens.com/Uni-ball-ZENTO-Gel-Pen-Signature-Model-0.38-mm-Silver-Body-Black-Ink/pd/45350"
]

PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def is_in_stock(url):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    return not soup.find("button", string="Get Restock Notification")

def send_pushover_message(message):
    data = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "message": message
    }
    requests.post("https://api.pushover.net/1/messages.json", data=data)

def main():
    print("🔍 Starting JetPens monitor...")
    while True:
        for url in PRODUCT_URLS:
            try:
                if is_in_stock(url):
                    print(f"✅ In stock: {url}")
                    send_pushover_message(f"🛍 JetPens item restocked!\n{url}")
                else:
                    print(f"❌ Still out of stock: {url}")
            except Exception as e:
                print(f"⚠️ Error checking {url}: {e}")
        time.sleep(300)  # wait 5 minutes between checks

if __name__ == "__main__":
    main()
