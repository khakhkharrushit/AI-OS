import time
import sys
import os
import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import pyautogui
import pyperclip

pyautogui.FAILSAFE = False

def send_whatsapp_modal(contact="Ashutosh Vit"):
    """
    Automates selecting the contact in WhatsApp Web's 'Send message to' modal and clicking Send:
    1. Waits for modal to render
    2. Types contact name into the active modal search field
    3. Presses Enter (which checks the contact's checkbox)
    4. Presses Enter / Clicks green Send button to dispatch
    """
    screen_w, screen_h = pyautogui.size()
    print(f"[WhatsApp Modal] Screen resolution: {screen_w}x{screen_h}")

    # Step 1: Wait 3.5 seconds for the modal to be active on screen
    time.sleep(3.5)

    # Step 2: Ensure modal search box is focused (center x: 50%, y: 26.5%)
    search_x = int(screen_w * 0.500)
    search_y = int(screen_h * 0.265)
    pyautogui.click(search_x, search_y)
    time.sleep(0.3)

    # Step 3: Type contact name into the search box
    pyperclip.copy(contact)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.2)

    # Step 4: Press Enter to check the contact checkbox
    pyautogui.press('enter')
    time.sleep(0.8)

    # Step 5: Send message via Enter and green button click (x: 60.6%, y: 88.0%)
    pyautogui.press('enter')
    time.sleep(0.3)
    
    send_btn_x = int(screen_w * 0.606)
    send_btn_y = int(screen_h * 0.880)
    pyautogui.click(send_btn_x, send_btn_y)
    time.sleep(0.2)
    pyautogui.press('enter')
    print("[WhatsApp Modal] Message dispatched successfully!")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Ashutosh Vit"
    send_whatsapp_modal(target)
