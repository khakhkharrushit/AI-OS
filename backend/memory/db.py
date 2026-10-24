import sqlite3
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "ai_os_memory.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    """Initializes the SQLite schema for user preferences, execution history, memory facts, calendar events, email drafts, and workflow templates."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Preferences Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Task History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_query TEXT NOT NULL,
                plan_json TEXT,
                status TEXT NOT NULL,
                logs_json TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Memory Facts / Workflow Notes Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 4. Calendar Events Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_time TEXT NOT NULL,
                duration_minutes INTEGER DEFAULT 30,
                description TEXT DEFAULT '',
                location TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 5. Email Drafts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                cc TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 6. Workflow Templates (Semantic / Reusable Plans)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                tags TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Populate default preferences if empty
        cursor.execute("SELECT COUNT(*) FROM preferences;")
        if cursor.fetchone()[0] == 0:
            default_prefs = [
                ("default_browser", "chrome", "Preferred web browser (chrome, brave, edge, firefox)"),
                ("editor", "code", "Preferred text editor command (e.g. code, notepad)"),
                ("user_name", "User", "User display name"),
                ("voice_enabled", "true", "Enable voice response TTS")
            ]
            cursor.executemany(
                "INSERT INTO preferences (key, value, description) VALUES (?, ?, ?);", 
                default_prefs
            )

        # Seed initial standard workflows if empty
        cursor.execute("SELECT COUNT(*) FROM workflows;")
        if cursor.fetchone()[0] == 0:
            default_workflows = [
                (
                    "Interview Workspace", 
                    "Prepares development tools, checks system health, and opens preparation notes",
                    json.dumps({
                        "response": "Preparing your interview workspace...",
                        "steps": [
                            {"step_number": 1, "description": "Check system metrics", "target_agent": "SystemAgent", "tool": "get_system_info", "arguments": {}},
                            {"step_number": 2, "description": "Search for resume", "target_agent": "FileAgent", "tool": "search_file", "arguments": {"filename": "resume"}},
                            {"step_number": 3, "description": "Open Chrome browser", "target_agent": "SystemAgent", "tool": "open_application", "arguments": {"app_name": "chrome"}}
                        ]
                    }),
                    "workspace, interview, setup"
                ),
                (
                    "System Health Diagnostic",
                    "Checks CPU, RAM, Disk and lists top memory consuming processes",
                    json.dumps({
                        "response": "Running complete system diagnostics...",
                        "steps": [
                            {"step_number": 1, "description": "Get system utilization", "target_agent": "SystemAgent", "tool": "get_system_info", "arguments": {}},
                            {"step_number": 2, "description": "List top running processes", "target_agent": "SystemAgent", "tool": "list_processes", "arguments": {"limit": 10}}
                        ]
                    }),
                    "system, health, diagnostics, processes"
                )
            ]
            cursor.executemany(
                "INSERT INTO workflows (title, description, plan_json, tags) VALUES (?, ?, ?, ?);",
                default_workflows
            )
        conn.commit()

# --- Preference Operations ---

def set_preference(key: str, value: str, description: str = "") -> dict:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO preferences (key, value, description, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                description = CASE WHEN excluded.description != '' THEN excluded.description ELSE preferences.description END,
                updated_at = CURRENT_TIMESTAMP;
        """, (key.strip().lower(), str(value).strip(), description.strip()))
        conn.commit()
    return {"key": key.strip().lower(), "value": value}

def get_preference(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM preferences WHERE key = ?;", (key.strip().lower(),)).fetchone()
        if row:
            return row["value"]
    return default

def get_all_preferences() -> Dict[str, str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM preferences ORDER BY key ASC;").fetchall()
        return {r["key"]: r["value"] for r in rows}

def delete_preference(key: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM preferences WHERE key = ?;", (key.strip().lower(),))
        conn.commit()
        return cursor.rowcount > 0

# --- Task History Operations ---

def log_task(user_query: str, plan: Optional[dict] = None, status: str = "completed", logs: Optional[List[str]] = None) -> int:
    with get_connection() as conn:
        plan_str = json.dumps(plan) if plan else None
        logs_str = json.dumps(logs) if logs else None
        cursor = conn.execute("""
            INSERT INTO task_history (user_query, plan_json, status, logs_json, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, (user_query, plan_str, status, logs_str))
        conn.commit()
        return cursor.lastrowid

def get_recent_tasks(limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, user_query, status, timestamp, plan_json, logs_json
            FROM task_history 
            ORDER BY id DESC 
            LIMIT ?;
        """, (limit,)).fetchall()
        
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "user_query": r["user_query"],
                "status": r["status"],
                "timestamp": r["timestamp"],
                "plan": json.loads(r["plan_json"]) if r["plan_json"] else None,
                "logs": json.loads(r["logs_json"]) if r["logs_json"] else []
            })
        return results

def search_tasks(keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, user_query, status, timestamp 
            FROM task_history 
            WHERE user_query LIKE ? 
            ORDER BY id DESC 
            LIMIT ?;
        """, (f"%{keyword}%", limit)).fetchall()
        return [dict(r) for r in rows]

# --- Memory Facts Operations ---

def add_memory_fact(topic: str, content: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO memory_facts (topic, content, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP);
        """, (topic.strip(), content.strip()))
        conn.commit()
        return cursor.lastrowid

def get_memory_facts(topic: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        if topic:
            rows = conn.execute("SELECT id, topic, content, timestamp FROM memory_facts WHERE topic LIKE ? OR content LIKE ? ORDER BY id DESC;", (f"%{topic}%", f"%{topic}%")).fetchall()
        else:
            rows = conn.execute("SELECT id, topic, content, timestamp FROM memory_facts ORDER BY id DESC LIMIT 20;").fetchall()
        return [dict(r) for r in rows]

# --- Calendar Event Operations ---

def add_calendar_event(title: str, event_date: str, event_time: str, duration_minutes: int = 30, description: str = "", location: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO calendar_events (title, event_date, event_time, duration_minutes, description, location)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (title.strip(), event_date.strip(), event_time.strip(), int(duration_minutes), description.strip(), location.strip()))
        conn.commit()
        return cursor.lastrowid

def get_calendar_events(limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, title, event_date, event_time, duration_minutes, description, location, created_at
            FROM calendar_events
            ORDER BY event_date ASC, event_time ASC
            LIMIT ?;
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

def delete_calendar_event(event_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM calendar_events WHERE id = ?;", (int(event_id),))
        conn.commit()
        return cursor.rowcount > 0

# --- Email Draft Operations ---

def save_email_draft(recipient: str, subject: str, body: str, cc: str = "", status: str = "draft") -> int:
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO email_drafts (recipient, subject, body, cc, status)
            VALUES (?, ?, ?, ?, ?);
        """, (recipient.strip(), subject.strip(), body.strip(), cc.strip(), status.strip()))
        conn.commit()
        return cursor.lastrowid

def update_email_draft_status(draft_id: int, status: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("UPDATE email_drafts SET status = ? WHERE id = ?;", (status.strip(), int(draft_id)))
        conn.commit()
        return cursor.rowcount > 0

def get_email_drafts(limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, recipient, subject, body, cc, status, created_at
            FROM email_drafts
            ORDER BY id DESC
            LIMIT ?;
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

# --- Workflow / Semantic Template Operations ---

def get_workflows() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT id, title, description, plan_json, tags, created_at FROM workflows ORDER BY title ASC;").fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "title": r["title"],
                "description": r["description"],
                "plan": json.loads(r["plan_json"]),
                "tags": r["tags"],
                "created_at": r["created_at"]
            })
        return results

def search_workflow_templates(query: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, title, description, plan_json, tags 
            FROM workflows 
            WHERE title LIKE ? OR description LIKE ? OR tags LIKE ?;
        """, (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "title": r["title"],
                "description": r["description"],
                "plan": json.loads(r["plan_json"]),
                "tags": r["tags"]
            })
        return results

# --- Prompt Context Generator ---

def format_memory_summary_for_prompt() -> str:
    """Generates a concise markdown summary of preferences, learned facts, and calendar for the Planner Agent."""
    try:
        init_db()
        prefs = get_all_preferences()
        facts = get_memory_facts()
        events = get_calendar_events(limit=5)
        
        lines = []
        if prefs:
            lines.append("USER PREFERENCES:")
            for k, v in prefs.items():
                lines.append(f"- {k}: {v}")
                
        if facts:
            lines.append("\nSTORED FACTS & KNOWLEDGE:")
            for f in facts[:6]:
                lines.append(f"- [{f['topic']}]: {f['content']}")
                
        if events:
            lines.append("\nUPCOMING CALENDAR EVENTS:")
            for ev in events:
                lines.append(f"- {ev['event_date']} {ev['event_time']}: {ev['title']} ({ev.get('description', '')})")

        if lines:
            return "\n--- LONG-TERM MEMORY & CONTEXT (PERSISTED) ---\n" + "\n".join(lines) + "\n----------------------------------------------\n"
        return ""
    except Exception as e:
        print(f"Error generating memory summary: {e}")
        return ""

# Auto-initialize DB on import
init_db()
