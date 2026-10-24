import os
import time
import io
import base64
from typing import Optional
from agents.base import BaseAgent
from tools.base import Tool
from ai_core import model

class VisionAgent(BaseAgent):
    def __init__(self):
        super().__init__("VisionAgent")
        self.register_tool(Tool("capture_screen", "Capture a screenshot of the Windows desktop and save it", self.capture_screen))
        self.register_tool(Tool("analyze_screen", "Capture the desktop screen and analyze its contents using AI Vision", self.analyze_screen))
        self.register_tool(Tool("click_screen_coordinate", "Click the mouse at specific (X, Y) pixel coordinates", self.click_screen_coordinate))
        self.register_tool(Tool("type_desktop_text", "Type a string of text into the active focused desktop application", self.type_desktop_text))
        self.register_tool(Tool("press_hotkey", "Press a combination of keyboard keys (e.g. 'ctrl+c', 'win+d', 'alt+tab')", self.press_hotkey))

    def _get_screenshot_image(self):
        """Captures a screenshot using Pillow ImageGrab or PyAutoGUI."""
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            return img
        except Exception:
            try:
                import pyautogui
                return pyautogui.screenshot()
            except Exception as e:
                raise Exception(f"Failed to capture desktop screenshot: {e}")

    def capture_screen(self, save_path: Optional[str] = None, **kwargs) -> str:
        home = os.path.expanduser("~")
        dest = save_path or os.path.join(home, "Desktop", f"screenshot_{int(time.time())}.png")
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)

        img = self._get_screenshot_image()
        img.save(dest)
        return f"Desktop screenshot captured and saved to '{dest}' (Resolution: {img.width}x{img.height})."

    def analyze_screen(self, query: str = "Describe what is currently visible on the screen and identify any active apps or error messages.", **kwargs) -> str:
        img = self._get_screenshot_image()
        
        # Resize if large to optimize for Vision API
        if img.width > 1920:
            img.thumbnail((1920, 1080))
            
        try:
            # Send PIL Image directly to Gemini
            prompt = f"""
You are the AI OS Vision Agent running on Windows.
The user is asking: "{query}"

Analyze this desktop screenshot carefully:
1. Identify the active foreground application and open windows.
2. Note any important text, buttons, alerts, or error dialogues.
3. Provide a clear, actionable answer to the user's question.
"""
            response = model.generate_content([prompt, img])
            return f"Screen Vision Analysis:\n\n{response.text}"
        except Exception as e:
            return f"Desktop screenshot captured ({img.width}x{img.height}), but Vision API returned: {e}"

    def click_screen_coordinate(self, x: int, y: int, clicks: int = 1, button: str = "left", **kwargs) -> str:
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            time.sleep(0.3)
            pyautogui.click(x=int(x), y=int(y), clicks=int(clicks), button=button)
            return f"Clicked mouse {button} button at ({x}, {y}) {clicks} time(s)."
        except ImportError:
            raise Exception("pyautogui is required for GUI mouse automation.")
        except Exception as e:
            raise Exception(f"Mouse click failed at ({x}, {y}): {e}")

    def type_desktop_text(self, text: str, interval: float = 0.05, press_enter: bool = False, **kwargs) -> str:
        if not text:
            raise ValueError("Text string is required.")
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            time.sleep(0.6)  # Allow target application window to gain focus
            pyautogui.write(text, interval=float(interval))
            if press_enter or text.endswith("="):
                time.sleep(0.3)
                pyautogui.press("enter")
            return f"Successfully typed '{text}' into the active application."
        except ImportError:
            raise Exception("pyautogui is required for typing automation.")
        except Exception as e:
            raise Exception(f"Failed to type text: {e}")

    def press_hotkey(self, keys: str, **kwargs) -> str:
        if not keys:
            raise ValueError("Keys string is required (e.g. 'ctrl+c', 'win+d', 'alt+tab', 'enter').")
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            time.sleep(0.4)
            normalized = keys.replace('+', ',').replace(' ', '')
            key_list = [k.strip().lower() for k in normalized.split(',') if k.strip()]
            if len(key_list) == 1:
                pyautogui.press(key_list[0])
            else:
                pyautogui.hotkey(*key_list)
            return f"Pressed keyboard key(s): {'+'.join(key_list)}"
        except ImportError:
            raise Exception("pyautogui is required for hotkey automation.")
        except Exception as e:
            raise Exception(f"Failed to trigger hotkey '{keys}': {e}")
