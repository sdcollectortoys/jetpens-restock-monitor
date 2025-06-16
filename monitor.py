
import os
import time
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
    import requests
    data = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "message": message
    }
    requests.post("https://api.pushover.net/1/messages.json", data=data)

def is_in_stock(driver, url):
    try:
        driver.get(url)
        time.sleep(3)  # Allow JS to load
        driver.find_element(By.XPATH, "//button[contains(text(), 'Get Restock Notification')]")
        return False
    except NoSuchElementException:
        return True
    except WebDriverException as e:
        print(f"WebDriver error on {url}: {e}")
        return False

def main():
    print("🚀 Starting Selenium-based JetPens monitor...")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    while True:
        for url in PRODUCT_URLS:
            try:
                if is_in_stock(driver, url):
                    print(f"✅ In stock: {url}")
                    send_pushover_message(f"🛍 JetPens item restocked!\n{url}")
                else:
                    print(f"❌ Still out of stock: {url}")
            except Exception as e:
                print(f"⚠️ Error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    main()
