import json
import os
import re
from typing import Optional, List, Dict, Any
from ai_core import generate_response
from memory.db import format_memory_summary_for_prompt

TOOL_DEFINITIONS = """
AVAILABLE AGENTS AND TOOLS:
1. FileAgent:
   - tool: "search_file", arguments: {"filename": "<name of file>", "directory": "<optional search directory, default .>"}
   - tool: "read_file", arguments: {"filepath": "<path to file>", "max_chars": 5000}
   - tool: "write_file", arguments: {"filepath": "<path to file>", "content": "<text to write>"}
   - tool: "append_file", arguments: {"filepath": "<path to file>", "content": "<text to append>"}
   - tool: "create_file", arguments: {"filepath": "<path to file>"}
   - tool: "copy_file", arguments: {"src": "<source path>", "dest": "<destination path>"}
   - tool: "move_file", arguments: {"src": "<source path>", "dest": "<destination path>"}
   - tool: "delete_file", arguments: {"filepath": "<path to file>"} (HIGH-RISK: requires human approval)
   - tool: "delete_folder", arguments: {"folderpath": "<path to folder>"} (HIGH-RISK: requires human approval)
   - tool: "find_and_delete", arguments: {"target_name": "<name of file or folder to search anywhere on laptop and delete>"} (HIGH-RISK: requires human approval)
   - tool: "create_folder", arguments: {"folderpath": "<path to folder>"}
   - tool: "list_directory", arguments: {"directory": "<path to directory>"}

2. SystemAgent:
   - tool: "open_application", arguments: {"app_name": "<name of application, e.g. chrome, notepad, task manager, telegram, whatsapp, valorant>", "filepath": "<optional file to open>"}
   - tool: "close_application", arguments: {"app_name": "<name of application>"}
   - tool: "send_whatsapp_desktop_message", arguments: {"contact": "<name of contact/person>", "message": "<message text to send>"}
   - tool: "open_whatsapp_desktop_chat", arguments: {"contact": "<name of contact/person>"}
   - tool: "adjust_brightness", arguments: {"action": "<increase|decrease|set>", "level": "<optional 0-100 percentage>"}
   - tool: "adjust_volume", arguments: {"action": "<increase|decrease|mute|unmute>", "steps": 5}
   - tool: "toggle_wifi", arguments: {"state": "<on|off>"}
   - tool: "toggle_airplane_mode", arguments: {"state": "<on|off>"}
   - tool: "toggle_bluetooth", arguments: {"state": "<on|off>"}
   - tool: "toggle_dark_mode", arguments: {"state": "<dark|light>"}
   - tool: "uninstall_application", arguments: {"app_name": "<name of application or software to uninstall/remove>"} (HIGH-RISK: requires human approval)
   - tool: "get_battery_status", arguments: {} (Returns laptop battery level, percentage, power plugged/charging status)
     - tool: "get_system_info", arguments: {} (Returns CPU, RAM, Disk C:, Battery, and OS details)
   - tool: "list_processes", arguments: {"filter_name": "<optional filter string>", "limit": 15}
   - tool: "system_command", arguments: {"command": "<raw command>"} (HIGH-RISK: requires human approval)

3. MemoryAgent:
   - tool: "set_user_preference", arguments: {"key": "<preference key, e.g. default_browser, editor>", "value": "<value>"}
   - tool: "get_user_preferences", arguments: {}
   - tool: "save_memory_fact", arguments: {"topic": "<topic or subject>", "content": "<fact to remember>"}
   - tool: "search_memory_facts", arguments: {"topic": "<search keyword>"}
   - tool: "get_execution_history", arguments: {"limit": 5}

4. BrowserAgent:
   - tool: "search_web", arguments: {"query": "<search query to look up on the internet>", "max_results": 5}
   - tool: "play_youtube_video", arguments: {"query": "<song, video title or search term, e.g. 'shakira video' or 'lofi beats'>"}
   - tool: "open_url", arguments: {"url": "<website URL to open in desktop browser, e.g. https://github.com>"}
   - tool: "send_whatsapp_message", arguments: {"contact": "<name of contact/person>", "message": "<message text to send>"}
   - tool: "open_whatsapp_chat", arguments: {"contact": "<name of contact/person>"}
   - tool: "extract_page_content", arguments: {"url": "<website URL to read text content from>", "max_chars": 3500}

5. DocumentAgent:
   - tool: "open_document", arguments: {"query": "<name of document, e.g. resume, report, notes, or doc type word/ppt/text/pdf>"}
   - tool: "open_latest_document", arguments: {"doc_type": "<docx|pdf|excel|pptx|txt>"}
   - tool: "read_pdf", arguments: {"filepath": "<path to pdf file>", "max_pages": 15}
   - tool: "read_docx", arguments: {"filepath": "<path to word .docx file>", "max_paragraphs": 50}
   - tool: "summarize_document", arguments: {"filepath": "<path to document>", "max_chars": 4000}
   - tool: "search_document_text", arguments: {"filepath": "<path to file>", "query": "<search text>"}
   - tool: "create_markdown_report", arguments: {"filepath": "<path to output .md>", "title": "<report title>", "content": "<markdown content>"}

6. EmailAgent:
   - tool: "create_email_draft", arguments: {"recipient": "<email address>", "subject": "<subject line>", "body": "<body text>", "cc": "<optional cc>"}
   - tool: "send_email", arguments: {"recipient": "<email address>", "subject": "<subject line>", "body": "<body text>", "cc": "<optional cc>"} (HIGH-RISK: requires human approval)
   - tool: "list_email_drafts", arguments: {"limit": 10}
   - tool: "generate_email_reply", arguments: {"incoming_email": "<received text>", "tone": "<professional|friendly|concise>", "sender_name": "<name>"}
   - tool: "open_mail_client", arguments: {"recipient": "<optional>", "subject": "<optional>", "body": "<optional>"}

7. CalendarAgent:
   - tool: "create_calendar_event", arguments: {"title": "<meeting/event title>", "event_date": "<YYYY-MM-DD or date>", "event_time": "<HH:MM AM/PM>", "duration_minutes": 30, "description": "<details>", "location": "<optional location>"}
   - tool: "list_upcoming_events", arguments: {"limit": 15}
   - tool: "search_calendar_events", arguments: {"query": "<search keyword>"}
   - tool: "delete_calendar_event", arguments: {"event_id": <id number>} (HIGH-RISK: requires human approval)
   - tool: "export_calendar_ics", arguments: {"title": "<event title>", "event_date": "<YYYY-MM-DD>", "output_path": "<optional destination path>"}

8. VisionAgent:
   - tool: "capture_screen", arguments: {"save_path": "<optional file destination path>"}
   - tool: "analyze_screen", arguments: {"query": "<what to inspect or check on the screen>"}
   - tool: "click_screen_coordinate", arguments: {"x": <x pixel coordinate>, "y": <y pixel coordinate>, "clicks": 1, "button": "left"}
   - tool: "type_desktop_text", arguments: {"text": "<text string to type into focused app>", "interval": 0.05}
   - tool: "press_hotkey", arguments: {"keys": "<e.g. 'ctrl+c', 'win+d', 'alt+tab'>"}
"""

def clean_json_response(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

def _parse_local_plan(user_input: str) -> Dict[str, Any]:
    """
    Intelligent fallback planner that parses both single and compound multi-step
    natural-language instructions into structured agent steps.
    """
    cmd = user_input.strip()
    cmd_lower = cmd.lower()
    steps = []
    # Web Login & Credential Autofill Workflows (e.g. "https://vtop.vit.ac.in/vtop/login open this and enter username : ... AND PASSWORD: ...")
    m_url = re.search(r'(https?://[^\s]+)', user_input)
    if m_url and ("username" in cmd_lower or "password" in cmd_lower or "login" in cmd_lower):
        target_url = m_url.group(1)
        m_u = re.search(r'username\s*[:=]?\s*([^\s,;]+)', user_input, re.IGNORECASE)
        m_p = re.search(r'password\s*[:=]?\s*([^\s,;]+)', user_input, re.IGNORECASE)
        u_val = m_u.group(1) if m_u else ""
        p_val = m_p.group(1) if m_p else ""
        if u_val or p_val:
            return {
                "response": f"Opening {target_url} and entering login credentials for username '{u_val}'.",
                "steps": [{
                    "step_number": 1,
                    "description": f"Open {target_url} and enter credentials for '{u_val}'",
                    "target_agent": "BrowserAgent",
                    "tool": "autofill_login_credentials",
                    "arguments": {
                        "url": target_url,
                        "username": u_val,
                        "password": p_val
                    }
                }]
            }

    # Weather & Climate Queries (e.g. "what is current weather", "weather in Mumbai", "temperature today")
    if "weather" in cmd_lower or "forecast" in cmd_lower or "temperature" in cmd_lower or "climate" in cmd_lower:
        m_loc = re.search(r'\b(?:in|for|at|of)\s+([a-zA-Z\s]+)', cmd, re.IGNORECASE)
        loc_val = m_loc.group(1).strip() if m_loc else ""
        if loc_val:
            loc_val = re.sub(r'\b(today|tomorrow|now|currently|right now|outside)\b', '', loc_val, flags=re.IGNORECASE).strip()
        return {
            "response": f"Checking current live weather{' for ' + loc_val if loc_val else ''}.",
            "steps": [{
                "step_number": 1,
                "description": f"Fetch live weather forecast{' for ' + loc_val if loc_val else ''}",
                "target_agent": "BrowserAgent",
                "tool": "get_weather",
                "arguments": {"location": loc_val}
            }]
        }

    # Battery & Charging queries (e.g. "what is current charging", "check battery")
    if any(k in cmd_lower for k in ["battery", "charging", "charge level", "power status", "is it charging", "battery percentage", "battery life", "battery status", "current charging"]):
        return {
            "response": "Checking current laptop battery level and charging status.",
            "steps": [{
                "step_number": 1,
                "description": "Check laptop battery percentage and power charging status",
                "target_agent": "SystemAgent",
                "tool": "get_battery_status",
                "arguments": {}
            }]
        }

    # 0. Messaging & WhatsApp Automation Workflows
    # E.g.: "open whatsapp web and then open ashutosh vit and type hi ashutosh and then send it"
    # E.g.: "open whatsapp and send a message to ashutosh saying hi ashutosh"
    # E.g.: "open whatsapp app and send message to Ashutosh Vit hi"
    # E.g.: "open whatsapp web and send message to Ashutosh Vit hi"
    # E.g.: "message Rahul on whatsapp hi how are you"
    if "whatsapp" in cmd_lower or "whats app" in cmd_lower:
        # Check if app or web is requested
        has_app_word = bool(re.search(r'\b(?:app|desktop|application)\b', cmd_lower))
        has_web_word = bool(re.search(r'\b(?:web|browser|chrome)\b', cmd_lower))
        
        if has_web_word and not has_app_word:
            is_web = True
        else:
            is_web = False

        cleaned_cmd = re.sub(r'^(?:open|launch|start|run|go to)\s+(?:whatsapp|whats\s*app)(?:\s+(?:app|web|desktop|application))?\s*(?:and(?:\s+then)?|,)?\s*', '', cmd, flags=re.IGNORECASE).strip()

        contact = None
        message_text = None

        # Pattern 1: explicit delimiters (saying, that, with, content, :, quotes)
        m = re.search(r'^(?:send\s+(?:a\s+)?message\s+to|send\s+to|message|text)\s+[\'"]?([a-zA-Z0-9_\-\s]+?)[\'"]?\s*(?::|->|saying|that|with|content)\s+[\'"]?(.+?)[\'"]?$', cleaned_cmd, flags=re.IGNORECASE)
        if m:
            contact = m.group(1).strip()
            message_text = m.group(2).strip()

        # Pattern 2: "open/search for <contact> and type <message> and send [it]"
        if not contact:
            m = re.search(r'^(?:open|search\s+for|search|find|chat\s+with|select|to)\s+[\'"]?([a-zA-Z0-9_\-\s]+?)[\'"]?\s+(?:and(?:\s+then)?\s+)?(?:type|write|saying|content)\s+[\'"]?(.+?)[\'"]?$', cleaned_cmd, flags=re.IGNORECASE)
            if m:
                contact = m.group(1).strip()
                message_text = m.group(2).strip()

        # Pattern 3: "message/send [a] message to <contact> on whatsapp [web/app] <message>"
        if not contact:
            m = re.search(r'^(?:message|text|send\s+(?:a\s+)?message\s+to|send\s+to)\s+([a-zA-Z0-9_\-\s]+?)\s+on\s+(?:whatsapp|whats\s*app)(?:\s+(?:web|app|desktop))?(?:\s+(?:saying|that|with|:)?\s*(.+))?$', cmd, flags=re.IGNORECASE)
            if m:
                contact = m.group(1).strip()
                if m.group(2):
                    message_text = m.group(2).strip()

        # Pattern 4: "send [a] message to <contact> <message>" without explicit delimiter
        if not contact:
            m = re.search(r'^(?:send\s+(?:a\s+)?message\s+to|send\s+to|message|text)\s+([a-zA-Z0-9_\-\s]+)$', cleaned_cmd, flags=re.IGNORECASE)
            if m:
                raw_body = m.group(1).strip()
                m_split = re.search(r'^(.*?)\s+(hi\b.*|hello\b.*|hey\b.*|good\s+morning.*|good\s+night.*|good\s+evening.*|how\s+are\s+you.*|what.*|why.*|when.*|please.*|call\s+me.*|i\s+am.*|i\'m.*|thanks.*|thank\s+you.*|ok\b.*|yes\b.*|no\b.*)$', raw_body, flags=re.IGNORECASE)
                if m_split:
                    contact = m_split.group(1).strip()
                    message_text = m_split.group(2).strip()
                else:
                    tokens = raw_body.split()
                    if len(tokens) >= 2:
                        contact = " ".join(tokens[:-1])
                        message_text = tokens[-1]
                    else:
                        contact = raw_body

        # Pattern 5: "open/search for <contact>"
        if not contact and cleaned_cmd:
            m = re.search(r'^(?:open|search\s+for|search|find|chat\s+with|to)\s+[\'"]?([a-zA-Z0-9_\-\s]+?)[\'"]?$', cleaned_cmd, flags=re.IGNORECASE)
            if m:
                c = m.group(1).strip()
                if c.lower() not in ["whatsapp", "whatsapp web", "whatsapp app", "web", "app", "the app"]:
                    contact = c

        # Clean up message and contact
        if contact:
            contact = re.sub(r'^(?:a\s+message\s+to|message\s+to|to)\s+', '', contact, flags=re.IGNORECASE).strip()
            contact = re.sub(r'\s+on\s+whatsapp(?:\s+web|\s+app)?$', '', contact, flags=re.IGNORECASE).strip()
            if contact.lower() in ["whatsapp", "whatsapp web", "whatsapp app", "web", "app", "the app"]:
                contact = None

        if message_text:
            message_text = re.sub(r'\s+and\s+(?:then\s+)?send(?:\s+it)?$', '', message_text, flags=re.IGNORECASE).strip()
            message_text = message_text.strip("'\"")

        if contact and message_text:
            if is_web:
                return {
                    "response": f"Opening WhatsApp Web, searching for '{contact}', and sending message: '{message_text}'.",
                    "steps": [{
                        "step_number": 1,
                        "description": f"Send WhatsApp Web message to '{contact}': '{message_text}'",
                        "target_agent": "BrowserAgent",
                        "tool": "send_whatsapp_message",
                        "arguments": {
                            "contact": contact,
                            "message": message_text
                        }
                    }]
                }
            else:
                return {
                    "response": f"Opening WhatsApp Desktop application, searching for '{contact}', and sending message: '{message_text}'.",
                    "steps": [{
                        "step_number": 1,
                        "description": f"Send WhatsApp Desktop message to '{contact}': '{message_text}'",
                        "target_agent": "SystemAgent",
                        "tool": "send_whatsapp_desktop_message",
                        "arguments": {
                            "contact": contact,
                            "message": message_text
                        }
                    }]
                }
        elif contact:
            if is_web:
                return {
                    "response": f"Opening WhatsApp Web and opening chat with '{contact}'.",
                    "steps": [{
                        "step_number": 1,
                        "description": f"Open WhatsApp Web chat with '{contact}'",
                        "target_agent": "BrowserAgent",
                        "tool": "open_whatsapp_chat",
                        "arguments": {
                            "contact": contact
                        }
                    }]
                }
            else:
                return {
                    "response": f"Opening WhatsApp Desktop application and opening chat with '{contact}'.",
                    "steps": [{
                        "step_number": 1,
                        "description": f"Open WhatsApp Desktop chat with '{contact}'",
                        "target_agent": "SystemAgent",
                        "tool": "open_whatsapp_desktop_chat",
                        "arguments": {
                            "contact": contact
                        }
                    }]
                }
        else:
            if is_web:
                return {
                    "response": "Opening WhatsApp Web in your browser.",
                    "steps": [{
                        "step_number": 1,
                        "description": "Open WhatsApp Web in browser",
                        "target_agent": "BrowserAgent",
                        "tool": "open_url",
                        "arguments": {"url": "https://web.whatsapp.com"}
                    }]
                }
            else:
                return {
                    "response": "Opening WhatsApp Desktop application installed on your computer.",
                    "steps": [{
                        "step_number": 1,
                        "description": "Launch WhatsApp Desktop Application",
                        "target_agent": "SystemAgent",
                        "tool": "open_application",
                        "arguments": {"app_name": "whatsapp"}
                    }]
                }

    # 0.2. YouTube Search & Video Playback Workflows
    # E.g.: "open youtube and play sakira video", "open youtube and seachr funni video", "play shakira on youtube"
    if "youtube" in cmd_lower or (cmd_lower.startswith("play ") and not any(k in cmd_lower for k in ["game", "valorant", "minecraft", "sound", "audio", "with", "offline"])):
        cleaned_yt = re.sub(r'^(?:open|launch|go to)\s+(?:the\s+)?youtube(?:\.com)?\s*(?:and(?:\s+then)?|,)?\s*', '', cmd, flags=re.IGNORECASE).strip()

        # Strip search/play action words (including common typos: seachr, serach, seach, etc.)
        yt_query = re.sub(r'^(?:search\s+for|search|seachr\s+for|seachr|serach\s+for|serach|seach\s+for|seach|play|watch|find|look\s+for|listen\s+to|type|in\s+it)\s+', '', cleaned_yt, flags=re.IGNORECASE).strip()
        
        # Remove trailing 'on youtube' if present
        yt_query = re.sub(r'\s+on\s+youtube(?:\.com)?$', '', yt_query, flags=re.IGNORECASE).strip()
        yt_query = yt_query.strip("'\"")

        if yt_query.lower() in ["youtube", "youtube.com", ""]:
            yt_query = None

        if yt_query:
            return {
                "response": f"Opening YouTube in a new browser tab and searching for '{yt_query}'.",
                "steps": [{
                    "step_number": 1,
                    "description": f"Search and play '{yt_query}' on YouTube",
                    "target_agent": "BrowserAgent",
                    "tool": "play_youtube_video",
                    "arguments": {"query": yt_query}
                }]
            }
        else:
            return {
                "response": "Opening YouTube in a new browser tab.",
                "steps": [{
                    "step_number": 1,
                    "description": "Open YouTube in browser",
                    "target_agent": "BrowserAgent",
                    "tool": "open_url",
                    "arguments": {"url": "https://youtube.com"}
                }]
            }


    # 0.5. Universal File / Folder / Application Deletion

    # E.g.: "delete rk.txt", "delete file notes.txt", "delete folder backup", "delete app valorant", "uninstall chrome", "remove document.docx"
    if any(cmd_lower.startswith(prefix) for prefix in ["delete ", "remove ", "erase ", "destroy ", "uninstall "]) or ("delete" in cmd_lower and any(w in cmd_lower for w in ["file", "folder", "app", "application", "document", "directory"])):
        cleaned_target = re.sub(r"^(?:please\s+)?(?:delete|remove|erase|destroy|uninstall)\s+(?:the\s+)?(?:file|folder|directory|app|application|doc|document)?\s*", "", cmd, flags=re.IGNORECASE).strip()
        cleaned_target = cleaned_target.strip("'\"")
        
        is_app = any(k in cmd_lower for k in ["app", "application", "uninstall", "program", "software"]) and not any(ext in cleaned_target.lower() for ext in [".txt", ".docx", ".pdf", ".py", ".json", ".md", ".png", ".jpg"])
        
        if is_app:
            return {
                "response": f"I will search for application '{cleaned_target}' across your system and ask for your confirmation before deletion.",
                "steps": [{
                    "step_number": 1,
                    "description": f"Find and uninstall application: {cleaned_target}",
                    "target_agent": "SystemAgent",
                    "tool": "uninstall_application",
                    "arguments": {"app_name": cleaned_target}
                }]
            }
        else:
            return {
                "response": f"I will locate '{cleaned_target}' anywhere on your laptop and request your confirmation before deleting it.",
                "steps": [{
                    "step_number": 1,
                    "description": f"Find and delete file or folder: {cleaned_target}",
                    "target_agent": "FileAgent",
                    "tool": "find_and_delete",
                    "arguments": {"target_name": cleaned_target}
                }]
            }

    # 1. Compound File Creation & Writing Workflows
    # E.g.: "open notepad and create a file name rk and then write my name is rk in it and save it on desktop"
    # E.g.: "one notepad and create a file name initiate and write my name is"
    # E.g.: "create a file named notes.txt on desktop and write hello world"
    if any(k in cmd_lower for k in ["create a file", "create file", "write", "save it on desktop", "save on desktop", "make a file", "file name", "file named"]):
        # Extract filename (e.g. 'initiate', 'rk', 'notes.txt', 'test')
        m_filename = re.search(r"(?:file\s+named|file\s+name|named|called|file)\s+['\"]?([a-zA-Z0-9_\-\.]+)(?:\.txt)?['\"]?", cmd, flags=re.IGNORECASE)
        filename = m_filename.group(1).strip() if m_filename else "document"
        if not filename.endswith(".txt") and "." not in filename:
            filename = f"{filename}.txt"

        # Determine path - default to Desktop so the user immediately sees it
        dest_dir = "Desktop"
        desktop_base = os.path.join(os.path.expanduser("~"), "Desktop")
        onedrive_desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if os.path.exists(onedrive_desktop):
            desktop_base = onedrive_desktop
        filepath = os.path.normpath(os.path.join(desktop_base, filename))

        # Extract content to write (e.g. "my name is", "my name is rk")
        content = "Created by AI OS."
        m_content = re.search(r"(?:write|put|type|content)\s+['\"]?(.*?)(?:['\"]?\s+in\s+it|['\"]?\s+and\s+save|['\"]?\s+on\s+desktop|$)", cmd, flags=re.IGNORECASE)
        if m_content and m_content.group(1).strip():
            content = m_content.group(1).strip()

        # Step 1: Write file to Desktop
        steps.append({
            "step_number": len(steps) + 1,
            "description": f"Create and write '{content}' to '{filename}' on Desktop",
            "target_agent": "FileAgent",
            "tool": "write_file",
            "arguments": {
                "filepath": filepath,
                "content": content
            }
        })

        # Step 2: Open in application if requested or implied (notepad / editor)
        if any(w in cmd_lower for w in ["notepad", "open", "one notepad", "editor", "view"]):
            steps.append({
                "step_number": len(steps) + 1,
                "description": f"Open '{filename}' in Notepad",
                "target_agent": "SystemAgent",
                "tool": "open_application",
                "arguments": {
                    "app_name": "notepad",
                    "filepath": filepath
                }
            })

        return {
            "response": f"Creating file '{filename}' on your Desktop with content '{content}' and opening it in Notepad.",
            "steps": steps
        }

    # 2. Calculator & Arithmetic Automation Workflows
    # E.g.: "open calculator and do 5 plus 5 in it", "calculate 25 * 4", "open calc"
    if any(k in cmd_lower for k in ["calculator", "calc"]) or ("open" in cmd_lower and any(op in cmd_lower for op in ["plus", "minus", "multiply", "divide", "+", "-", "*", "/"])):
        # Normalize math expression (e.g. "5 plus 5" -> "5+5=")
        expr_raw = cmd_lower
        for w, sym in [("plus", "+"), ("add", "+"), ("minus", "-"), ("subtract", "-"), ("multiplied by", "*"), ("times", "*"), ("multiply", "*"), ("divided by", "/"), ("divide", "/")]:
            expr_raw = expr_raw.replace(w, sym)
        m_math = re.search(r"(\d+\s*[\+\-\*\/]\s*\d+(?:\s*[\+\-\*\/]\s*\d+)*)", expr_raw)
        math_str = m_math.group(1).replace(" ", "") + "=" if m_math else ""

        steps.append({
            "step_number": 1,
            "description": "Launch Windows Calculator",
            "target_agent": "SystemAgent",
            "tool": "open_application",
            "arguments": {"app_name": "calc"}
        })
        if math_str:
            steps.append({
                "step_number": 2,
                "description": f"Type arithmetic keystrokes '{math_str}' into Calculator",
                "target_agent": "VisionAgent",
                "tool": "type_desktop_text",
                "arguments": {"text": math_str, "interval": 0.1}
            })
            return {
                "response": f"Opening Windows Calculator and calculating '{math_str[:-1]}'.",
                "steps": steps
            }
        return {
            "response": "Opening Windows Calculator on your desktop.",
            "steps": steps
        }

    # 3. Web Shortcuts & Compound App / Browser Workflows
    # E.g.: "open chrome and open gmail", "open youtube", "open github"
    WEB_SHORTCUTS = {
        "gmail": "https://mail.google.com",
        "google mail": "https://mail.google.com",
        "mail": "https://mail.google.com",
        "youtube": "https://youtube.com",
        "github": "https://github.com",
        "google": "https://google.com",
        "chatgpt": "https://chatgpt.com",
        "twitter": "https://x.com",
        "x": "https://x.com",
        "reddit": "https://reddit.com",
        "linkedin": "https://linkedin.com",
        "whatsapp web": "https://web.whatsapp.com",
        "instagram": "https://instagram.com",
        "facebook": "https://facebook.com",
        "netflix": "https://netflix.com",
        "spotify web": "https://open.spotify.com",
        "amazon": "https://amazon.com"
    }

    # Split compound "and / then / also" commands
    parts = re.split(r"\s+(?:and(?:\s+then)?|then|also)\s+", cmd, flags=re.IGNORECASE)
    if len(parts) > 1 and any(re.search(r"^(?:open|launch|start|run)\s+", p.strip(), re.IGNORECASE) for p in parts):
        # Check if any part is a web URL/shortcut — if so, we just open that directly
        # (avoid launching bare "chrome" then URL as two steps with timing issue)
        BARE_BROWSERS = {"chrome", "google chrome", "firefox", "mozilla firefox", "edge", "microsoft edge", "brave", "opera"}
        
        for p in parts:
            p_clean = re.sub(r"^(?:open|launch|start|run)\s+(?:the\s+)?", "", p.strip(), flags=re.IGNORECASE).strip().lower()
            if not p_clean:
                continue
            # Skip bare browser name — URL step will handle launching
            if p_clean in BARE_BROWSERS:
                continue
            if p_clean in WEB_SHORTCUTS or any(p_clean.endswith(k) for k in WEB_SHORTCUTS):
                url = WEB_SHORTCUTS.get(p_clean, f"https://{p_clean}.com")
                steps.append({
                    "step_number": len(steps) + 1,
                    "description": f"Open web application: {url}",
                    "target_agent": "BrowserAgent",
                    "tool": "open_url",
                    "arguments": {"url": url}
                })
            elif p_clean.startswith("http://") or p_clean.startswith("https://") or p_clean.startswith("www."):
                steps.append({
                    "step_number": len(steps) + 1,
                    "description": f"Open website URL: {p_clean}",
                    "target_agent": "BrowserAgent",
                    "tool": "open_url",
                    "arguments": {"url": p_clean}
                })
            else:
                steps.append({
                    "step_number": len(steps) + 1,
                    "description": f"Launch application: {p_clean}",
                    "target_agent": "SystemAgent",
                    "tool": "open_application",
                    "arguments": {"app_name": p_clean}
                })
        if steps:
            return {
                "response": f"Executing compound multi-app workflow ({len(steps)} steps).",
                "steps": steps
            }

    # 3.5 & 4. Unified Open Router (Documents, Office, Apps, Web)
    m_open = re.match(r"^(?:open|launch|start|run|show|display)\s+(?:the\s+)?(.+)$", cmd_lower)
    if m_open:
        target = m_open.group(1).strip()

        # A. Web Shortcuts & URLs
        if target in WEB_SHORTCUTS:
            url = WEB_SHORTCUTS[target]
            return {
                "response": f"Opening {target.title()} in your preferred browser.",
                "steps": [{
                    "step_number": 1,
                    "description": f"Open {target.title()} ({url})",
                    "target_agent": "BrowserAgent",
                    "tool": "open_url",
                    "arguments": {"url": url}
                }]
            }
        if target.startswith("http://") or target.startswith("https://") or target.startswith("www."):
            return {
                "response": f"Opening website '{target}' in your preferred browser.",
                "steps": [{
                    "step_number": 1,
                    "description": f"Open URL {target}",
                    "target_agent": "BrowserAgent",
                    "tool": "open_url",
                    "arguments": {"url": target}
                }]
            }

        # B. Direct Office Applications (Opening blank apps)
        if target in ["word", "winword", "microsoft word", "ms word"]:
            return {
                "response": "Opening Microsoft Word on your desktop.",
                "steps": [{
                    "step_number": 1,
                    "description": "Launch Microsoft Word",
                    "target_agent": "SystemAgent",
                    "tool": "open_application",
                    "arguments": {"app_name": "winword"}
                }]
            }
        if target in ["powerpoint", "ppt", "powerpnt", "microsoft powerpoint", "ms powerpoint"]:
            return {
                "response": "Opening Microsoft PowerPoint on your desktop.",
                "steps": [{
                    "step_number": 1,
                    "description": "Launch Microsoft PowerPoint",
                    "target_agent": "SystemAgent",
                    "tool": "open_application",
                    "arguments": {"app_name": "powerpnt"}
                }]
            }
        if target in ["excel", "microsoftexcel", "microsoft excel", "ms excel"]:
            return {
                "response": "Opening Microsoft Excel on your desktop.",
                "steps": [{
                    "step_number": 1,
                    "description": "Launch Microsoft Excel",
                    "target_agent": "SystemAgent",
                    "tool": "open_application",
                    "arguments": {"app_name": "excel"}
                }]
            }
        if target in ["notepad", "notes app", "text editor"]:
            return {
                "response": "Opening Notepad on your desktop.",
                "steps": [{
                    "step_number": 1,
                    "description": "Launch Notepad",
                    "target_agent": "SystemAgent",
                    "tool": "open_application",
                    "arguments": {"app_name": "notepad"}
                }]
            }

        # C. Document, File, Presentation, Resume, Report, or Text requests
        doc_keywords = ["document", "doc", "docx", "word document", "word doc", "pdf", "file", 
                        "sheet", "excel", "report", "presentation", "slide", "slides", "ppt", "pptx", 
                        "text", "txt", "note", "notes", "resume", "cv", "dissertation", "bitmap", "image"]
        
        is_doc_request = any(k in target for k in doc_keywords) or any(target.endswith(ext) for ext in [".docx", ".pdf", ".txt", ".pptx", ".xlsx", ".doc", ".ppt", ".md", ".csv"])

        if is_doc_request:
            return {
                "response": f"Finding and opening document '{target}' for you.",
                "steps": [{
                    "step_number": 1,
                    "description": f"Open document: {target}",
                    "target_agent": "DocumentAgent",
                    "tool": "open_document",
                    "arguments": {"query": target}
                }]
            }

        # D. General Application launch fallback
        return {
            "response": f"Opening application '{target}' on your desktop.",
            "steps": [{
                "step_number": 1,
                "description": f"Launch application: {target}",
                "target_agent": "SystemAgent",
                "tool": "open_application",
                "arguments": {"app_name": target}
            }]
        }

    # 2.5. Hardware & Quick Settings Controls (Brightness, Volume/Sound, Wi-Fi, Airplane Mode, Bluetooth, Dark Mode)
    # E.g.: "increase brightness", "increase brightness to 80%", "decrease sound", "mute audio", "turn on wifi", "turn on airplane mode"
    if "brightness" in cmd_lower:
        m_level = re.search(r"(\d+)\s*%", cmd_lower) or re.search(r"(?:to|at|set)\s+(\d+)", cmd_lower)
        level_val = int(m_level.group(1)) if m_level else None
        action_val = "set" if level_val is not None else ("decrease" if any(w in cmd_lower for w in ["decrease", "down", "lower", "dim", "less", "min", "reduce"]) else "increase")
        return {
            "response": f"Adjusting display brightness ({action_val}{f' to {level_val}%' if level_val is not None else ''}).",
            "steps": [{
                "step_number": 1,
                "description": f"Adjust screen brightness ({action_val})",
                "target_agent": "SystemAgent",
                "tool": "adjust_brightness",
                "arguments": {"action": action_val, "level": level_val}
            }]
        }

    if any(w in cmd_lower for w in ["volume", "sound", "audio", "mute", "unmute"]) and any(w in cmd_lower for w in ["increase", "decrease", "up", "down", "lower", "raise", "mute", "unmute", "turn", "set", "reduce", "boost"]):
        action_val = "mute" if ("mute" in cmd_lower and "unmute" not in cmd_lower) else ("decrease" if any(w in cmd_lower for w in ["decrease", "down", "lower", "reduce", "less", "softer"]) else "increase")
        return {
            "response": f"Adjusting system sound volume ({action_val}).",
            "steps": [{
                "step_number": 1,
                "description": f"Adjust audio volume ({action_val})",
                "target_agent": "SystemAgent",
                "tool": "adjust_volume",
                "arguments": {"action": action_val, "steps": 6}
            }]
        }

    if "wifi" in cmd_lower or "wi-fi" in cmd_lower or ("network" in cmd_lower and any(w in cmd_lower for w in ["on", "off", "enable", "disable"])):
        if any(w in cmd_lower for w in ["turn on", "enable", "activate", "switch on", "on"]):
            state_val = "on"
        elif any(w in cmd_lower for w in ["turn off", "disable", "deactivate", "switch off", "off"]):
            state_val = "off"
        else:
            state_val = "on"
        return {
            "response": f"Configuring Wi-Fi network state to '{state_val}'.",
            "steps": [{
                "step_number": 1,
                "description": f"Toggle Wi-Fi ({state_val})",
                "target_agent": "SystemAgent",
                "tool": "toggle_wifi",
                "arguments": {"state": state_val}
            }]
        }

    if "airplane" in cmd_lower or "aeroplane" in cmd_lower or "flight mode" in cmd_lower:
        state_val = "off" if any(w in cmd_lower for w in ["off", "disable", "deactivate"]) else "on"
        return {
            "response": f"Toggling Airplane Mode ({state_val}).",
            "steps": [{
                "step_number": 1,
                "description": f"Toggle Airplane Mode ({state_val})",
                "target_agent": "SystemAgent",
                "tool": "toggle_airplane_mode",
                "arguments": {"state": state_val}
            }]
        }

    if "bluetooth" in cmd_lower:
        state_val = "off" if any(w in cmd_lower for w in ["off", "disable", "deactivate"]) else "on"
        return {
            "response": f"Toggling Bluetooth ({state_val}).",
            "steps": [{
                "step_number": 1,
                "description": f"Toggle Bluetooth ({state_val})",
                "target_agent": "SystemAgent",
                "tool": "toggle_bluetooth",
                "arguments": {"state": state_val}
            }]
        }

    if any(k in cmd_lower for k in ["dark mode", "light mode", "dark theme", "light theme"]):
        state_val = "dark" if "dark" in cmd_lower else "light"
        return {
            "response": f"Switching Windows theme to {state_val.title()} Mode.",
            "steps": [{
                "step_number": 1,
                "description": f"Switch Windows theme to {state_val.title()} Mode",
                "target_agent": "SystemAgent",
                "tool": "toggle_dark_mode",
                "arguments": {"state": state_val}
            }]
        }

    # 3. System: Close Application
    m_close = re.match(r"^(?:close|quit|kill|stop|terminate)\s+(?:the\s+)?(.+)$", cmd_lower)
    if m_close:
        target = m_close.group(1).strip()
        return {
            "response": f"Closing application '{target}'.",
            "steps": [{
                "step_number": 1,
                "description": f"Close application: {target}",
                "target_agent": "SystemAgent",
                "tool": "close_application",
                "arguments": {"app_name": target}
            }]
        }

    # 4. System: System Info / Diagnostics
    if any(k in cmd_lower for k in ["cpu", "system info", "ram usage", "disk space", "hardware", "diagnostics", "system health"]):
        return {
            "response": "Fetching real-time system metrics and hardware diagnostics.",
            "steps": [
                {
                    "step_number": 1,
                    "description": "Fetch live CPU, RAM, and Disk metrics",
                    "target_agent": "SystemAgent",
                    "tool": "get_system_info",
                    "arguments": {}
                },
                {
                    "step_number": 2,
                    "description": "List active processes",
                    "target_agent": "SystemAgent",
                    "tool": "list_processes",
                    "arguments": {"limit": 10}
                }
            ]
        }

    # 5. System: List processes
    if "process" in cmd_lower or "running task" in cmd_lower or "task list" in cmd_lower:
        return {
            "response": "Retrieving top running system processes.",
            "steps": [{
                "step_number": 1,
                "description": "List top running processes",
                "target_agent": "SystemAgent",
                "tool": "list_processes",
                "arguments": {"limit": 15}
            }]
        }

    # 6. Browser: Web Search
    if any(cmd_lower.startswith(prefix) for prefix in ["search web", "google", "search the web", "look up", "search internet", "search online"]):
        query = re.sub(r"^(?:search\s+(?:the\s+)?(?:web|internet|online)(?:\s+for)?|google|look\s+up)\s+", "", cmd, flags=re.IGNORECASE).strip()
        return {
            "response": f"Searching the web for '{query}'.",
            "steps": [{
                "step_number": 1,
                "description": f"Search web for: {query}",
                "target_agent": "BrowserAgent",
                "tool": "search_web",
                "arguments": {"query": query, "max_results": 5}
            }]
        }

    # 7. File: Search / Find file
    m_find = re.match(r"^(?:find|search|locate)\s+(?:file|files|document)?\s*(?:named|for)?\s*(.+)$", cmd, flags=re.IGNORECASE)
    if m_find:
        target = m_find.group(1).strip()
        return {
            "response": f"Searching your filesystem for files matching '{target}'.",
            "steps": [{
                "step_number": 1,
                "description": f"Search for file: {target}",
                "target_agent": "FileAgent",
                "tool": "search_file",
                "arguments": {"filename": target, "directory": "."}
            }]
        }

    # 8. Vision: Screenshot / Screen analysis
    if "screenshot" in cmd_lower or "screen" in cmd_lower or "capture" in cmd_lower:
        return {
            "response": "Capturing desktop screenshot for visual analysis.",
            "steps": [{
                "step_number": 1,
                "description": "Capture desktop screen",
                "target_agent": "VisionAgent",
                "tool": "capture_screen",
                "arguments": {}
            }]
        }

    # 9. Calendar: Schedule / Events
    if ("calendar" in cmd_lower or "schedule" in cmd_lower or "meeting" in cmd_lower or "event" in cmd_lower) and not ("email" in cmd_lower or "mail" in cmd_lower or "@" in cmd_lower):
        if "list" in cmd_lower or "show" in cmd_lower or "upcoming" in cmd_lower:
            return {
                "response": "Listing upcoming calendar events.",
                "steps": [{
                    "step_number": 1,
                    "description": "List upcoming events",
                    "target_agent": "CalendarAgent",
                    "tool": "list_upcoming_events",
                    "arguments": {"limit": 10}
                }]
            }
        return {
            "response": "Scheduling calendar event.",
            "steps": [{
                "step_number": 1,
                "description": f"Schedule event: {cmd}",
                "target_agent": "CalendarAgent",
                "tool": "create_calendar_event",
                "arguments": {"title": cmd, "event_date": "Tomorrow", "event_time": "10:00 AM"}
            }]
        }

    # 10. Email: Draft, send, or list
    if "email" in cmd_lower or "draft" in cmd_lower or "mail" in cmd_lower or cmd_lower in ["send it now", "send it", "send this email", "send this draft"]:
        if "list" in cmd_lower or "show" in cmd_lower:
            return {
                "response": "Retrieving stored email drafts.",
                "steps": [{
                    "step_number": 1,
                    "description": "List email drafts",
                    "target_agent": "EmailAgent",
                    "tool": "list_email_drafts",
                    "arguments": {"limit": 10}
                }]
            }

        # Check if user is referencing the latest draft (e.g. "send it now")
        from memory.db import get_email_drafts
        latest_drafts = get_email_drafts(limit=1)
        latest_draft = latest_drafts[0] if latest_drafts else None

        email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', cmd)
        recipient = email_match.group(0) if email_match else ""
        if not recipient:
            to_m = re.search(r'\bto\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|[a-zA-Z0-9_.-]+(?:\s+[a-zA-Z0-9_.-]+)*?)(?:\s+(?:with|subject|body|message|saying)|$)', cmd, re.IGNORECASE)
            if to_m:
                recipient = to_m.group(1).strip()
            elif latest_draft and cmd_lower in ["send it now", "send it", "send this email", "send this draft", "send email now"]:
                recipient = latest_draft.get("recipient", "")

        subject = ""
        sub_m = re.search(r'\bsubject\s+(?:is\s+)?(.*?)(?:\s+(?:and\s+)?(?:body|message|saying|content)|$)', cmd, re.IGNORECASE)
        if sub_m:
            subject = sub_m.group(1).strip().strip('"\'')
        elif "about " in cmd_lower:
            sub_m2 = re.search(r"\babout\s+(?:the\s+)?([^.,;]+)", cmd, re.IGNORECASE)
            if sub_m2:
                subject = sub_m2.group(1).strip()
        elif latest_draft and not recipient and cmd_lower in ["send it now", "send it", "send this email"]:
            subject = latest_draft.get("subject", "")

        body = ""
        body_m = re.search(r'\b(?:body|message|saying|content)\s+(?:is\s+)?(.*)', cmd, re.IGNORECASE)
        if body_m:
            body = body_m.group(1).strip().strip('"\'')
        elif latest_draft and cmd_lower in ["send it now", "send it", "send this email", "send this draft"]:
            body = latest_draft.get("body", "")
        else:
            body = cmd

        is_send = any(w in cmd_lower for w in ["send", "dispatch", "deliver", "transmit"])
        target_tool = "send_email" if is_send else "create_email_draft"
        action_verb = "Sending" if is_send else "Creating draft for"

        return {
            "response": f"{action_verb} email to {recipient or 'recipient'}.",
            "steps": [{
                "step_number": 1,
                "description": f"{action_verb} email to {recipient or 'recipient'} with subject '{subject or 'AI OS Notification'}'",
                "target_agent": "EmailAgent",
                "tool": target_tool,
                "arguments": {
                    "recipient": recipient or "recipient@example.com",
                    "subject": subject or "AI OS Notification",
                    "body": body or cmd
                }
            }]
        }

    # 11. Memory: Remember / Preferences
    if cmd_lower.startswith("remember") or cmd_lower.startswith("save fact") or cmd_lower.startswith("note that"):
        content = re.sub(r"^(?:remember(?:\s+that)?|save\s+fact|note\s+that)\s+", "", cmd, flags=re.IGNORECASE).strip()
        return {
            "response": f"Recording memory note: '{content}'",
            "steps": [{
                "step_number": 1,
                "description": f"Save memory fact: {content}",
                "target_agent": "MemoryAgent",
                "tool": "save_memory_fact",
                "arguments": {"topic": "user_note", "content": content}
            }]
        }

    # Default friendly conversational reply
    return {
        "response": f"I received your request: '{user_input}'. Formulating execution strategy...",
        "steps": []
    }

def create_plan(user_input: str, history: Optional[List[Dict[str, str]]] = None) -> dict:
    """
    Uses the LLM to break down a high-level user request into a structured JSON plan,
    """
    # Deterministic high-precision routing for critical workflows (Logins, Battery, etc.)
    local_p = _parse_local_plan(user_input)
    if local_p and local_p.get("steps"):
        first_tool = local_p["steps"][0].get("tool")
        if first_tool in ["autofill_login_credentials", "get_battery_status", "get_weather"]:
            return local_p
    home_dir = os.path.expanduser("~")
    
    history_context = ""
    if history:
        history_lines = []
        for msg in history[-8:]:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            history_lines.append(f"{role}: {content}")
        if history_lines:
            history_context = "\nRECENT CONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n"

    memory_context = format_memory_summary_for_prompt()

    prompt = f"""
You are the AI OS Planner Agent running on a Windows system.
The user's home directory is: {home_dir}
Your job is to break down the user's instruction into a sequential execution plan across the 8 specialized agents.
You must return your plan as a valid JSON object. Do not include markdown formatting like ```json.
{TOOL_DEFINITIONS}
{memory_context}
{history_context}

RULES & COMMON PATTERNS:
1. NEVER pass human names, contacts, or search terms into `SystemAgent.open_application`. That tool is ONLY for actual software apps installed on Windows (like 'notepad', 'calc', 'chrome').
2. For WhatsApp:
   - If user asks for "whatsapp web" or mentions "web": BrowserAgent: send_whatsapp_message {{"contact": "<contact_name>", "message": "<message_text>"}} (or BrowserAgent: open_url {{"url": "https://web.whatsapp.com"}})
   - If user asks for "whatsapp app", "whatsapp desktop", or sends a message without specifying web: SystemAgent: send_whatsapp_desktop_message {{"contact": "<contact_name>", "message": "<message_text>"}} (or SystemAgent: open_application {{"app_name": "whatsapp"}})
3. For Calculator and math: SystemAgent: open_application {{"app_name": "calc"}} -> VisionAgent: type_desktop_text {{"text": "<math_expression>="}}
4. For Creating Files on Desktop: FileAgent: write_file -> SystemAgent: open_application {{"app_name": "notepad", "filepath": "..."}}
5. For YouTube video/music playback & search (e.g. "open youtube and play sakira video", "play shakira on youtube", "search lofi beats on youtube"): BrowserAgent: play_youtube_video {{"query": "<song_or_video_name>"}} (or BrowserAgent: open_url {{"url": "https://youtube.com"}} if just opening YouTube).
6. For Web browsing: Use BrowserAgent: open_url with full https URL.
7. For Opening Recent/Latest Files (e.g. "open latest bitmap image", "open latest ppt", "open latest word document", "open recent excel"): DocumentAgent: open_latest_document {{"doc_type": "<docx|pdf|excel|pptx|bitmap|txt>"}}

7. For Deleting Files, Folders, or Applications (e.g. "delete rk.txt", "delete folder notes", "delete app valorant", "uninstall discord", "delete sample"):
   - For files or folders: FileAgent: find_and_delete {{"target_name": "<name>"}}
   - For applications/programs: SystemAgent: uninstall_application {{"app_name": "<name>"}}
8. For Hardware & Quick Settings (e.g. "increase brightness", "decrease sound", "mute volume", "turn on wifi", "turn on airplane mode", "turn on dark mode"):
   - Brightness: SystemAgent: adjust_brightness {{"action": "<increase|decrease|set>", "level": <optional level>}}
   - Volume / Sound: SystemAgent: adjust_volume {{"action": "<increase|decrease|mute|unmute>"}}
   - Wi-Fi: SystemAgent: toggle_wifi {{"state": "<on|off>"}}
   - Airplane Mode: SystemAgent: toggle_airplane_mode {{"state": "<on|off>"}}
   - Bluetooth: SystemAgent: toggle_bluetooth {{"state": "<on|off>"}}
   - Dark/Light Theme: SystemAgent: toggle_dark_mode {{"state": "<dark|light>"}}
9. For Website Login & Credential Entry (e.g. "open <url> and enter username <user> and password <pass>"): Use BrowserAgent: autofill_login_credentials {{"url": "<url>", "username": "<user>", "password": "<pass>"}}. NEVER omit the username and password from the plan!

User instruction: "{user_input}"

Respond ONLY with a JSON object matching this schema:
{{
  "response": "A friendly conversational reply to the user explaining what you will do. If they are just chatting (e.g. 'hello'), reply here.",
  "steps": [
    {{
      "step_number": 1,
      "description": "A clear description of what this step does",
      "target_agent": "FileAgent | SystemAgent | MemoryAgent | BrowserAgent | DocumentAgent | EmailAgent | CalendarAgent | VisionAgent",
      "tool": "The specific tool to use",
      "arguments": {{
          "arg1": "value1"
      }}
    }}
  ]
}}
Note: If the user is just chatting or asking a general question not requiring OS action, leave 'steps' as an empty array [].
"""
    try:
        response_text = generate_response(prompt)
        cleaned = clean_json_response(response_text)
        plan = json.loads(cleaned)
        return plan
    except Exception as e:
        print(f"LLM planner unavailable/failed ({e}). Using local heuristic planner.")
        return _parse_local_plan(user_input)

def replan_after_failure(user_instruction: str, failed_step: dict, error_message: str) -> dict:
    prompt = f"""
You are the AI OS Planner Agent running on a Windows system.
The user's original goal was: "{user_instruction}"

Step {failed_step.get('step_number')} failed:
Description: {failed_step.get('description')}
Agent: {failed_step.get('target_agent')}
Tool: {failed_step.get('tool')}
Arguments: {failed_step.get('arguments')}
Error encountered: {error_message}

{TOOL_DEFINITIONS}

Analyze this failure and determine if there is an alternative recovery step or tool call to accomplish the user's intent.

Respond ONLY with a JSON object matching this schema:
{{
  "can_recover": true or false,
  "explanation": "Why this recovery is being attempted, or why it is impossible to recover",
  "recovery_steps": [
    {{
      "step_number": 1,
      "description": "Clear description of recovery action",
      "target_agent": "FileAgent | SystemAgent | MemoryAgent | BrowserAgent | DocumentAgent | EmailAgent | CalendarAgent | VisionAgent",
      "tool": "The specific tool to use",
      "arguments": {{}}
    }}
  ]
}}
"""
    try:
        response_text = generate_response(prompt)
        cleaned = clean_json_response(response_text)
        recovery_plan = json.loads(cleaned)
        return recovery_plan
    except Exception as e:
        print(f"Replanning error: {e}")
        return {"can_recover": False, "explanation": str(e), "recovery_steps": []}
