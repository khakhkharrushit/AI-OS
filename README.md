# AI Operating System (AI OS)

An intelligent natural-language operating system layer running on Windows. Translates high-level natural language instructions into multi-agent system execution plans orchestrated by Google Gemini.

---

## 🚀 Overview

Instead of manually clicking through multiple applications, files, browsers, and terminal windows, the AI OS decomposes commands into structured execution graphs executed by 8 specialized agents with a built-in safety validation layer.

```text
User Command: "Prepare my interview workspace: check system info, find my resume, and open Chrome."
       │
       ▼
   LLM AI Core (Google Gemini Reasoning)
       │
       ▼
   Planner Agent (Task Decomposition & JSON Schema)
       │
       ├──────────────┬──────────────┬──────────────┬──────────────┐
       ▼              ▼              ▼              ▼              ▼
   File Agent    System Agent   Memory Agent   Browser Agent  Document Agent
 (Files/Folders) (Apps & Diag)  (SQLite Recall) (Web Search)   (PDF/Docx/MD)
       │              │              │              │              │
       ├──────────────┴──────────────┼──────────────┴──────────────┘
       ▼                             ▼
  Email Agent                  Calendar Agent                 Vision Agent
 (Drafts/Dispatch)            (Scheduling/ICS)             (Screen/PyAutoGUI)
       │                             │                             │
       └─────────────────────────────┼─────────────────────────────┘
                                     │
                                     ▼
                         Safety & Validation Layer
                     (Intercepts High-Risk Actions)
                                     │
                                     ▼
                          Windows OS Execution
```

---

## 📊 Implementation Status (100% Complete)

| Phase | Component | Status | Description |
| :---: | :--- | :---: | :--- |
| **1** | **Backend & Frontend Foundation** | ✅ **Completed** | FastAPI backend with Gemini API exponential retry backoff + Next.js dashboard. |
| **2** | **Intelligent Planning & Replanning** | ✅ **Completed** | Structured JSON plan generation, step executor, multi-step resumption, and automated LLM replanning. |
| **3** | **8 Specialized Agents** | ✅ **Completed** | File, System, Memory, Browser, Document, Email, Calendar, and Vision agents. |
| **4** | **Memory Architecture** | ✅ **Completed** | Short-term context + Long-term SQLite database for user preferences, facts, and workflow templates. |
| **5** | **Voice & Vision Integration** | ✅ **Completed** | Web Speech STT, SpeechSynthesis TTS, desktop screenshot capture, and Gemini Vision reasoning. |
| **6** | **Desktop OS UI & Live Stepper** | ✅ **Completed** | Modern Glassmorphism dashboard with live CPU/RAM/Disk telemetry, multi-agent stepper, and workspace tabs. |
| **7** | **Safety Interception & Test Suite** | ✅ **Completed** | Human-in-the-loop validation for dangerous actions + automated pytest test suite. |

---

## 🛠️ The 8 Specialized Agents

1. **FileAgent** ([`backend/agents/file_agent.py`](backend/agents/file_agent.py)): Search, create, read, write, append, copy, move, delete (high-risk), list directory with OneDrive normalization.
2. **SystemAgent** ([`backend/agents/system_agent.py`](backend/agents/system_agent.py)): App launcher (`.lnk` and UWP protocols), taskkill, live CPU/RAM/Disk stats, process lists, system command (high-risk).
3. **MemoryAgent** ([`backend/agents/memory_agent.py`](backend/agents/memory_agent.py)): User preferences, learned facts, execution task logging, prompt injection.
4. **BrowserAgent** ([`backend/agents/browser_agent.py`](backend/agents/browser_agent.py)): Live DuckDuckGo internet searches, desktop browser launching with user preference detection, article text extraction.
5. **DocumentAgent** ([`backend/agents/document_agent.py`](backend/agents/document_agent.py)): PDF extraction (`pypdf`), Word `.docx` extraction (`python-docx`), in-document search, AI summarization, Markdown reports.
6. **EmailAgent** ([`backend/agents/email_agent.py`](backend/agents/email_agent.py)): Email draft creation, AI email reply generator, safety-verified sending (high-risk), and Windows mailto integration.
7. **CalendarAgent** ([`backend/agents/calendar_agent.py`](backend/agents/calendar_agent.py)): Event scheduling, upcoming meeting listings, search, cancellation (high-risk), and `.ics` export.
8. **VisionAgent** ([`backend/agents/vision_agent.py`](backend/agents/vision_agent.py)): Desktop screenshot capture, Gemini Vision screen reasoning, coordinate mouse clicks, typing, and keyboard hotkeys.

---

## ⚙️ Quickstart Guide

### 1. Backend Setup
```bash
cd backend
py -3.11 -m pip install -r requirements.txt

# Start backend server
py -3.11 -m uvicorn main:app --reload --port 8000
```
Backend runs at `http://127.0.0.1:8000` (API Docs: `http://127.0.0.1:8000/docs`).

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

### 3. Run Automated Tests
```bash
py -3.11 -m pytest backend/tests/ -v
```

---

## 🛡️ Safety & Validation Layer

The AI OS enforces a strict human-in-the-loop safety model:
1. When an agent attempts a high-risk operation (`delete_file`, `send_email`, `delete_calendar_event`, `system_command`), execution is immediately paused.
2. A security card appears in the chat UI detailing the exact tool and parameters.
3. Once the user clicks **"Approve & Resume Multi-Step Plan"**, the backend executes the approved action and continues subsequent planned steps.
