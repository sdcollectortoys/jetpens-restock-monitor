
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException

PRODUCT_URLS = [
    "https://www.jetpens.com/Uni-ball-ZENTO-Gel-Pen-Signature-Model-0.5-mm-Metallic-Black-Body-Black-Ink/pd/45351",
    "https://www.jetpens.com/Uni-ball-ZENTO-Gel-Pen-Signature-Model-0.38-mm-Silver-Body-Black-Ink/pd/45350"
]

PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")

def send_pushover_message(message):
    try:
        data = {
            "token": PUSHOVER_API_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "message": message
        }
        response = requests.post("https://api.pushover.net/1/messages.json", data=data)
        print(f"📤 Sent Pushover alert: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to send Pushover alert: {e}")

def is_in_stock(driver, url):
    try:
        print(f"🔍 Checking: {url}")
        driver.get(url)
        time.sleep(3)
        driver.find_element(By.XPATH, "//button[contains(text(), 'Get Restock Notification')]")
        print("❌ Still out of stock.")
        return False
    except NoSuchElementException:
        print("✅ In stock!")
        return True
    except WebDriverException as e:
        print(f"⚠️ WebDriver error: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Unexpected error checking stock: {e}")
        return False

def main():
    print("🟢 JetPens Selenium Monitor started...")

    try:
        chrome_options = Options()
        chrome_options.binary_location = "/usr/bin/chromium"
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"❌ Failed to start Chrome WebDriver: {e}")
        return

    while True:
        for url in PRODUCT_URLS:
            try:
                if is_in_stock(driver, url):
                    send_pushover_message(f"🛍 JetPens item restocked!\n{url}")
            except Exception as e:
                print(f"⚠️ Loop error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    main()
