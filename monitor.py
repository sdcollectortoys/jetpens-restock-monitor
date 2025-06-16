#!/usr/bin/env python3
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException

# Pushover credentials from environment
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")

if not PUSHOVER_USER_KEY or not PUSHOVER_API_TOKEN:
    print("❌ Missing Pushover credentials. Set PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN.")
    exit(1)

# List your JetPens product URLs here
PRODUCT_URLS = [
    "https://www.jetpens.com/Uni-ball-ZENTO-Gel-Pen-Signature-Model-0.5-mm-Metallic-Black-Body-Black-Ink/pd/45351",
    "https://www.jetpens.com/Uni-ball-ZENTO-Gel-Pen-Signature-Model-0.38-mm-Silver-Body-Black-Ink/pd/45350"
]

# Check interval in seconds (default: 60)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))

def send_pushover_message(message: str):
    """Send a message via Pushover."""
    response = requests.post("https://api.pushover.net/1/messages.json", data={
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "message": message
    })
    if response.status_code == 200:
        print(f"✅ Pushover alert sent: {message}")
    else:
        print(f"❌ Pushover failed [{response.status_code}]: {response.text}")

def is_in_stock(driver, url: str) -> bool:
    """Return True if the 'Get Restock Notification' button is not found (i.e., in stock)."""
    print(f"🔍 Checking URL: {url}")
    driver.get(url)
    time.sleep(5)  # allow page to load fully
    try:
        driver.find_element(By.XPATH, "//button[contains(text(),'Get Restock Notification')]")
        print("🔴 Out of stock (notification button present)")
        return False
    except NoSuchElementException:
        print("🟢 In stock!")
        return True

def main():
    chrome_bin = os.getenv("CHROME_BIN", "/usr/bin/chromium")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

    chrome_options = Options()
    chrome_options.binary_location = chrome_bin
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    service = Service(executable_path=chromedriver_path)
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Chrome WebDriver started")
    except WebDriverException as e:
        print(f"❌ Failed to start Chrome WebDriver: {e}")
        return

    try:
        while True:
            print(f"🔁 Starting check cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            for url in PRODUCT_URLS:
                try:
                    if is_in_stock(driver, url):
                        send_pushover_message(f"🛍 JetPens item restocked!\n{url}")
                except Exception as e:
                    print(f"⚠️ Error checking {url}: {e}")
            print(f"⏳ Sleeping for {CHECK_INTERVAL} seconds\n")
            time.sleep(CHECK_INTERVAL)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
