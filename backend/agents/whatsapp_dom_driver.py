import os
import sys
import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Global driver singleton to keep session active
_DRIVER_INSTANCE = None
_DRIVER_LOCK = threading.Lock()

def get_or_create_driver():
    global _DRIVER_INSTANCE
    with _DRIVER_LOCK:
        if _DRIVER_INSTANCE is not None:
            try:
                # Test if driver is still alive
                _ = _DRIVER_INSTANCE.current_url
                return _DRIVER_INSTANCE
            except Exception:
                _DRIVER_INSTANCE = None

        # Create user profile directory for persistent WhatsApp login
        profile_dir = os.path.join(os.path.expanduser("~"), ".ai_os_whatsapp_profile")
        os.makedirs(profile_dir, exist_ok=True)

        options = Options()
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        _DRIVER_INSTANCE = driver
        return driver

def send_whatsapp_selenium(contact: str, message: str) -> str:
    """
    Automates WhatsApp Web using a controlled Selenium Chrome instance with direct DOM access.
    """
    driver = get_or_create_driver()
    
    # Navigate to WhatsApp Web if not already there
    if "web.whatsapp.com" not in driver.current_url:
        driver.get("https://web.whatsapp.com")

    wait = WebDriverWait(driver, 45)

    # 1. Wait for and find the search box
    search_selectors = [
        '//input[@aria-label="Search or start a new chat"]',
        '//input[@data-tab="3"]',
        '//div[@role="textbox"][@contenteditable="true"]',
        '/html/body/div[1]/div/div/div/div/div[3]/div/div[3]/div/div[1]/div[1]/div/div/div/div/div/div[2]/input',
    ]

    search_box = None
    for xpath in search_selectors:
        try:
            search_box = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            if search_box:
                break
        except Exception:
            continue

    if not search_box:
        raise Exception("Could not find WhatsApp search box. Please ensure you are logged into WhatsApp Web.")

    # 2. Click, clear, and type contact name
    search_box.click()
    time.sleep(0.3)
    search_box.send_keys(Keys.CONTROL, "a")
    search_box.send_keys(Keys.BACKSPACE)
    time.sleep(0.2)
    search_box.send_keys(contact)
    time.sleep(1.5)
    search_box.send_keys(Keys.ENTER)
    time.sleep(1.5)

    # 3. Find message box, type message and send
    msg_selectors = [
        '//footer//div[@contenteditable="true"]',
        '//div[@role="textbox"][@data-tab="10"]',
        '//footer//div[@role="textbox"]',
    ]

    msg_box = None
    for xpath in msg_selectors:
        try:
            msg_box = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            if msg_box:
                break
        except Exception:
            continue

    if not msg_box:
        raise Exception(f"Chat opened for '{contact}', but message composer was not found.")

    msg_box.click()
    time.sleep(0.3)
    msg_box.send_keys(message)
    time.sleep(0.5)
    msg_box.send_keys(Keys.ENTER)

    return f"Successfully sent WhatsApp message to '{contact}': '{message}' via Selenium Automated Window."

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        print(send_whatsapp_selenium(sys.argv[1], sys.argv[2]))
    else:
        print("Ready for automated execution.")
