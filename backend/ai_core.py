import os
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini API
api_key = os.getenv("GEMINI_API_KEY", "").strip()
has_valid_key = bool(api_key and api_key != "your_gemini_api_key_here")

if has_valid_key:
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")

# Supported model
MODEL_NAME = 'gemini-3.5-flash-lite'
try:
    model = genai.GenerativeModel(MODEL_NAME)
except Exception:
    model = None

def _get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key and key != "your_gemini_api_key_here":
        return key
    try:
        from memory.db import get_all_preferences
        prefs = get_all_preferences()
        db_key = prefs.get("GEMINI_API_KEY") or prefs.get("gemini_api_key") or prefs.get("api_key")
        if db_key and db_key.strip():
            return db_key.strip()
    except Exception:
        pass
    return ""

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=3),
    reraise=True
)
def generate_response(prompt: str) -> str:
    """
    Generate a response from the Gemini model, with light exponential backoff.
    If no API key is provided, raises ValueError to trigger intelligent local planner.
    """
    current_key = _get_api_key()
    if not current_key or current_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY not configured. Falling back to local reasoning engine.")

    try:
        genai.configure(api_key=current_key)
        active_model = genai.GenerativeModel(MODEL_NAME)
        response = active_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        raise
