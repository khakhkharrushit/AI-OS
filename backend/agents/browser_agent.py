import webbrowser
import subprocess
import requests
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from agents.base import BaseAgent
from tools.base import Tool
from memory.db import get_preference

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pass

try:
    import pyperclip
except Exception:
    pass

class BrowserAgent(BaseAgent):
    def __init__(self):
        super().__init__("BrowserAgent")
        self.register_tool(Tool(
            "search_web", 
            "Search the internet for real-time information, documentation, news, or answers", 
            self.search_web
        ))
        self.register_tool(Tool(
            "open_url", 
            "Open a specific URL in the user's preferred desktop web browser (e.g. Chrome, Brave, Edge)", 
            self.open_url
        ))
        self.register_tool(Tool(
            "send_whatsapp_message",
            "Open WhatsApp Web, wait for connection, search for contact, and type and send a message",
            self.send_whatsapp_message
        ))
        self.register_tool(Tool(
            "open_whatsapp_chat",
            "Open WhatsApp Web and open chat with a specific contact or person",
            self.open_whatsapp_chat
        ))
        self.register_tool(Tool(
            "play_youtube_video",
            "Search and play a video or song on YouTube in your browser (e.g. query='shakira video' or 'lofi hip hop')",
            self.play_youtube_video
        ))
        self.register_tool(Tool(
            "extract_page_content", 
            "Fetch and extract readable text content and title from a webpage URL", 
            self.extract_page_content
        ))
        self.register_tool(Tool(
            "autofill_login_credentials",
            "Open a website login page and enter username and password credentials into the form fields",
            self.autofill_login_credentials
        ))
        self.register_tool(Tool(
            "get_weather",
            "Get real-time live current weather forecast and temperature for any city or user location",
            self.get_weather
        ))


    def search_web(self, query: str, max_results: int = 5, **kwargs) -> str:
        """Searches the web via DuckDuckGo and returns title, snippet, and link."""
        if not query:
            raise ValueError("Missing 'query' argument for web search.")

        results = []
        if HAS_DDGS:
            try:
                with DDGS() as ddgs:
                    raw_results = list(ddgs.text(query, max_results=int(max_results)))
                    for r in raw_results:
                        results.append({
                            "title": r.get("title", "No Title"),
                            "snippet": r.get("body", ""),
                            "url": r.get("href", "")
                        })
            except Exception as e:
                # Fallback to direct HTML search if DDGS throws an exception
                results = self._fallback_html_search(query, int(max_results))
        else:
            results = self._fallback_html_search(query, int(max_results))

        if not results:
            return f"No web search results found for query: '{query}'."

        lines = [f"Web Search Results for '{query}':"]
        for i, item in enumerate(results, 1):
            lines.append(f"{i}. {item['title']}\n   URL: {item['url']}\n   Snippet: {item['snippet']}")
        return "\n\n".join(lines)

    def _fallback_html_search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Fallback search query parser using DuckDuckGo HTML endpoint."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}", headers=headers, timeout=8)
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for result in soup.find_all("div", class_="result")[:max_results]:
                title_tag = result.find("a", class_="result__a")
                snippet_tag = result.find("a", class_="result__snippet")
                if title_tag:
                    results.append({
                        "title": title_tag.get_text(strip=True),
                        "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                        "url": title_tag.get("href", "")
                    })
            return results
        except Exception:
            return []

    def _get_chrome_path(self) -> Optional[str]:
        """Finds the absolute path to Chrome executable on Windows."""
        import os
        import shutil
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            shutil.which("chrome"),
            shutil.which("google-chrome")
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return c
        return None

    def open_url(self, url: str, browser: Optional[str] = None, **kwargs) -> str:
        """Opens a URL in a new tab in the user's active desktop web browser."""
        import os
        import subprocess
        import ctypes
        import webbrowser

        if not url:
            raise ValueError("Missing 'url' argument.")

        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"https://{url}"

        # 1. Native Windows ShellExecuteW (Direct Win32 API to active browser)
        try:
            res = ctypes.windll.shell32.ShellExecuteW(None, "open", url, None, None, 1)
            if res > 32:
                return f"Opened '{url}' in a new tab in your browser."
        except Exception:
            pass

        # 2. Native Windows ShellExecute (os.startfile)
        try:
            os.startfile(url)
            return f"Opened '{url}' in a new tab in your browser."
        except Exception:
            pass

        # 3. Python webbrowser
        try:
            webbrowser.open_new_tab(url)
            return f"Opened '{url}' in your browser."
        except Exception:
            pass

        # 4. Windows rundll32 URL handler fallback
        try:
            subprocess.Popen(["rundll32.exe", "url.dll,FileProtocolHandler", url])
            return f"Opened '{url}' in your browser."
        except Exception:
            pass

        return f"Opened '{url}'"




    def send_whatsapp_message(self, contact: str, message: str, **kwargs) -> str:
        """
        Opens WhatsApp Web modal and automatically selects the contact checkbox & clicks Send.
        """
        import subprocess
        import sys
        import os
        import urllib.parse
        import re

        if not contact:
            raise ValueError("Missing 'contact' argument.")
        if not message:
            raise ValueError("Missing 'message' argument.")

        clean_phone = re.sub(r'[^0-9]', '', contact)
        if len(clean_phone) >= 10:
            wa_url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={urllib.parse.quote_plus(message)}"
            self.open_url(wa_url)
            return f"Opened WhatsApp Web directly to chat +{clean_phone} with prefilled message."

        # Open the WhatsApp modal with prefilled message attached
        wa_url = f"https://web.whatsapp.com/send?text={urllib.parse.quote_plus(message)}"
        self.open_url(wa_url)

        # Launch background auto-selector to check contact and click Send button
        sender_script = os.path.join(os.path.dirname(__file__), "whatsapp_sender.py")
        subprocess.Popen([sys.executable, sender_script, contact], shell=False)

        return f"Opened WhatsApp Web. Auto-selecting '{contact}' and clicking Send for: '{message}'"











    def open_whatsapp_chat(self, contact: str, **kwargs) -> str:
        """Opens WhatsApp Web and opens chat with a contact using keyboard shortcuts."""
        import time
        import urllib.parse
        import re

        if not contact:
            raise ValueError("Missing 'contact' argument.")

        try:
            import pyautogui
            import pyperclip
            pyautogui.FAILSAFE = False
        except ImportError:
            raise Exception("pyautogui and pyperclip are required for desktop automation.")

        clean_phone = re.sub(r'[^0-9]', '', contact)
        if len(clean_phone) >= 10:
            wa_url = f"https://web.whatsapp.com/send?phone={clean_phone}"
        else:
            wa_url = "https://web.whatsapp.com"

        self.open_url(wa_url)
        time.sleep(5.0)

        if len(clean_phone) < 10:
            pyautogui.hotkey('ctrl', 'alt', '/')
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'alt', 'n')
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.2)

            pyperclip.copy(contact)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1.5)
            pyautogui.press('enter')

        return f"Successfully opened WhatsApp Web chat for '{contact}'"


    def extract_page_content(self, url: str, max_chars: int = 3500, **kwargs) -> str:

        """Fetches a webpage, cleans the HTML, and returns the readable text and title."""
        if not url:
            raise ValueError("Missing 'url' argument.")
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"https://{url}"

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove scripts, styles, forms, and navigation
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
                tag.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"

            # Extract main text
            text_blocks = []
            for p in soup.find_all(["p", "h1", "h2", "h3", "li"]):
                clean_t = p.get_text(separator=" ", strip=True)
                if len(clean_t) > 20:
                    text_blocks.append(clean_t)

            full_text = "\n\n".join(text_blocks)
            if not full_text:
                full_text = soup.get_text(separator=" ", strip=True)

            truncated = full_text[:int(max_chars)]
            suffix = f"\n\n[Content truncated at {max_chars} characters. Total length: {len(full_text)}]" if len(full_text) > int(max_chars) else ""

            return f"Page Title: {title}\nURL: {url}\n\nContent:\n{truncated}{suffix}"
        except Exception as e:
            raise Exception(f"Failed to fetch content from '{url}': {e}")

    def play_youtube_video(self, query: str, **kwargs) -> str:
        """Opens YouTube in the user's browser, searches for the requested song/video, and displays playback results."""
        import urllib.parse

        if not query:
            raise ValueError("Missing 'query' argument for YouTube search.")

        query_clean = query.strip()
        encoded_query = urllib.parse.quote_plus(query_clean)
        search_url = f"https://www.youtube.com/results?search_query={encoded_query}"

        self.open_url(search_url)
        return f"Successfully opened YouTube in a new tab and searched for '{query_clean}': {search_url}"




    def autofill_login_credentials(self, url: str, username: str = "", password: str = "", **kwargs) -> str:
        """
        Opens a target login URL in the browser and enters username and password credentials.
        Also copies credentials to clipboard for seamless login access.
        """
        import time, threading
        if not url:
            raise ValueError("URL is required.")

        # Open the URL in the browser
        self.open_url(url)

        def worker():
            import time
            try:
                import pyautogui, pyperclip
                pyautogui.FAILSAFE = False
                
                # Wait for browser and webpage to load
                time.sleep(3.5)
                
                # Check if it's VTOP
                if "vtop" in url.lower():
                    time.sleep(1.0)
                
                # Paste username into focused field
                if username:
                    pyperclip.copy(username)
                    time.sleep(0.3)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.5)
                
                # Press Tab to move to password field
                pyautogui.press('tab')
                time.sleep(0.4)
                
                # Paste password into password field
                if password:
                    pyperclip.copy(password)
                    time.sleep(0.3)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.4)
                    # Press tab to move to captcha box
                    pyautogui.press('tab')
            except Exception as e:
                print(f"Notice: Credential autofill background worker error: {e}")

        threading.Thread(target=worker, daemon=True).start()

        return (
            f"Successfully opened '{url}' and initiated credential entry for username '{username}'.\n"
            f"Credentials prepared on clipboard. If CAPTCHA is required (such as on VTOP), please solve the visual CAPTCHA to complete sign in."
        )

    def get_weather(self, location: str = "", **kwargs) -> str:
        """Fetches real-time live weather conditions and temperature."""
        import requests
        try:
            loc = (location or "").strip()
            url = f"https://wttr.in/{requests.utils.quote(loc)}?format=j1" if loc else "https://wttr.in/?format=j1"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(url, headers=headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                cur = data['current_condition'][0]
                area = data['nearest_area'][0]
                city = area.get('areaName', [{}])[0].get('value', 'Your Location')
                region = area.get('region', [{}])[0].get('value', '')
                country = area.get('country', [{}])[0].get('value', '')
                desc = cur.get('weatherDesc', [{}])[0].get('value', 'Clear').strip()
                temp_c = cur.get('temp_C', 'N/A')
                feels_c = cur.get('FeelsLikeC', temp_c)
                humidity = cur.get('humidity', 'N/A')
                wind = cur.get('windspeedKmph', 'N/A')
                
                place = f"{city}, {region}" if region else f"{city}, {country}" if country else city
                return (
                    f"Current Weather in {place}: {desc}, {temp_c} deg C (Feels like {feels_c} deg C) | "
                    f"Humidity: {humidity}% | Wind: {wind} km/h"
                )
            else:
                return f"Could not fetch weather data from weather service (Status {resp.status_code})."
        except Exception as e:
            return f"Weather service unavailable: {e}"
