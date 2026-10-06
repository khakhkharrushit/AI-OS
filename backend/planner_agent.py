import json
import os
from typing import Optional, List, Dict
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
   - tool: "create_folder", arguments: {"folderpath": "<path to folder>"}
   - tool: "list_directory", arguments: {"directory": "<path to directory>"}

2. SystemAgent:
   - tool: "open_application", arguments: {"app_name": "<name of application, e.g. chrome, notepad, brave, valorant>"}
   - tool: "close_application", arguments: {"app_name": "<name of application>"}
   - tool: "get_system_info", arguments: {} (Returns CPU, RAM, Disk C: and OS details)
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
   - tool: "open_url", arguments: {"url": "<website URL to open in desktop browser, e.g. https://github.com>"}
   - tool: "extract_page_content", arguments: {"url": "<website URL to read text content from>", "max_chars": 3500}

5. DocumentAgent:
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
    """Helper to strip markdown backticks from LLM output."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

def create_plan(user_input: str, history: Optional[List[Dict[str, str]]] = None) -> dict:
    """
    Uses the LLM to break down a high-level user request into a structured JSON plan,
    incorporating previous conversation context and long-term memory.
    """
    home_dir = os.path.expanduser("~")
    
    history_context = ""
    if history:
        history_lines = []
        for msg in history[-8:]:  # Keep recent history
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
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON plan: {e}")
        return {
            "response": f"I had trouble structuring a plan for: '{user_input}'.",
            "steps": []
        }
    except Exception as e:
        raise Exception(f"Planner Agent Error: {str(e)}")

def replan_after_failure(user_instruction: str, failed_step: dict, error_message: str) -> dict:
    """
    Asks the LLM for a recovery plan when a step fails.
    """
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
For example:
- If opening Chrome failed, try opening Brave or Edge.
- If finding a file at a specific path failed, try searching for the file name.

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
