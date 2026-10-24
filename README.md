# 🚀 AI Operating System (AI OS)
### Intelligent Natural-Language Operating System Orchestrator
**Final Year Engineering Capstone Project | Built by [Rushit Khakhkhar](https://github.com/khakhkharrushit)**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Gemini AI](https://img.shields.io/badge/Google%20Gemini-Pro%20%2F%20Flash-8E75B2?logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Tests](https://img.shields.io/badge/Pytest-9%2F9%20Passing%20(100%25)-success?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🌟 Executive Summary

Traditional operating system interaction requires switching between file explorers, command lines, system diagnostic tools, desktop productivity apps, and web browsers.

The **AI Operating System (AI OS)** is a unified multi-agent orchestrator that enables users to control and monitor their computing environment entirely through **natural language**. Powered by **Google Gemini**, the system autonomously plans, verifies, and executes complex multi-step workflows across the operating system with built-in human-in-the-loop safety interception.

```text
                                 [ User Command ]
             "Open my final report, check laptop battery, and summarize it"
                                       │
                                       ▼
                   ┌───────────────────────────────────────┐
                   │   LLM AI Core (Google Gemini Engine)  │
                   └───────────────────────────────────────┘
                                       │
                                       ▼
                   ┌───────────────────────────────────────┐
                   │    Planner Agent (Decomposition DAG)  │
                   └───────────────────────────────────────┘
                                       │
         ┌──────────────┬──────────────┼──────────────┬──────────────┐
         ▼              ▼              ▼              ▼              ▼
   [SystemAgent]  [DocumentAgent] [BrowserAgent] [MemoryAgent]  [VisionAgent]
   - Hardware     - Word .docx    - Live Weather - SQLite DB    - Screen OCR
   - Battery/CPU  - PDF Reader    - Web Search   - Preferences  - Mouse/Keys
   - Native Apps  - Markdown      - Research     - Workflows    - Screenshot
         │              │              │              │              │
         └──────────────┴──────────────┼──────────────┴──────────────┘
                                       │
                                       ▼
                   ┌───────────────────────────────────────┐
                   │      Safety & Validation Layer        │
                   │    (Intercepts High-Risk Actions)     │
                   └───────────────────────────────────────┘
                                       │
                                       ▼
                   ┌───────────────────────────────────────┐
                   │        Operating System Actions       │
                   └───────────────────────────────────────┘
```

---

## 💎 Key Features & Technical Highlights

### 1. 🧠 Multi-Agent Autonomous Architecture
- **Planner Agent**: Parses complex natural language instructions into a directed acyclic graph (DAG) of executable tool calls using strict JSON schemas.
- **System Agent**: Real-time hardware telemetry (CPU, RAM, Disk, Battery percentage & charging state), process inspection, and native app launching (Word, Chrome, Explorer, WhatsApp).
- **Browser Agent**: Live search and real-time weather engine (`wttr.in`) with automated geolocation and city-level routing.
- **Document Agent**: Deep inspection, extraction, and generation of PDF (`pypdf`) and Microsoft Word (`python-docx`) files.
- **Memory Agent**: Persistent long-term memory via SQLite (`ai_os_memory.db`) storing user preferences, facts, and workflow routines.
- **Email & Calendar Agents**: In-app SMTP sending, draft management, and calendar scheduling.
- **Vision Agent**: Screen capture analysis and coordinate-based mouse/keyboard automation via PyAutoGUI.

### 2. 🛡️ Human-in-the-Loop Safety Interception
- Execution of potentially destructive operations (`delete_file`, `system_command`, `send_email`, `delete_calendar_event`) is intercepted before execution.
- Prompts an interactive confirmation modal with complete argument inspection, requiring explicit user approval before execution resumes.

### 3. ⚡ Modern Glassmorphic Dashboard
- Built with **Next.js 15**, **React**, and **Tailwind CSS**.
- Real-time hardware gauges for CPU, Memory, and Disk utilization.
- Interactive multi-agent execution step visualizer.
- Speech-to-Text (STT) voice input and SpeechSynthesis Text-to-Speech (TTS) audio output.

---

## 🚀 Quick Start Guide

### Option 1: 1-Click Launch (Recommended for Full Desktop OS Control)

The AI OS comes with a cross-platform 1-click launcher script `run.py`:

```bash
# Clone the repository
git clone https://github.com/khakhkharrushit/AI-OS.git
cd AI-OS

# Run the 1-click launcher
python run.py
```

`run.py` automatically:
1. Validates your environment and creates `backend/.env` from `.env.example` if needed.
2. Spawns the **FastAPI Backend** on `http://127.0.0.1:8000`.
3. Spawns the **Next.js Frontend** on `http://localhost:3000`.
4. Opens your web browser directly to the dashboard.

---

### Option 2: Manual Step-by-Step Setup

#### 1. Backend Setup
```bash
cd backend

# Create and activate virtual environment (optional but recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment Variables
cp .env.example .env
# Open .env and add your GEMINI_API_KEY (from https://aistudio.google.com/)

# Start FastAPI server
python -m uvicorn main:app --reload --port 8000
```
- API Endpoint: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

#### 2. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```
- Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Automated Test Suite (100% Pass Rate)

To verify all agents, database connections, and safety interception mechanisms:

```bash
python -m pytest backend/tests/ -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1
collected 9 items

backend/tests/test_ai_os.py::test_agents_registry PASSED                 [ 11%]
backend/tests/test_ai_os.py::test_file_agent_lifecycle PASSED            [ 22%]
backend/tests/test_ai_os.py::test_system_agent_info_and_process PASSED   [ 33%]
backend/tests/test_ai_os.py::test_memory_agent_and_db PASSED             [ 44%]
backend/tests/test_ai_os.py::test_calendar_agent PASSED                  [ 55%]
backend/tests/test_ai_os.py::test_email_agent PASSED                     [ 66%]
backend/tests/test_ai_os.py::test_document_agent PASSED                  [ 77%]
backend/tests/test_ai_os.py::test_safety_interception PASSED             [ 88%]
backend/tests/test_ai_os.py::test_executor_plan_and_safety_halt PASSED   [100%]

======================== 9 passed in 7.26s ====================================
```

---

## ☁️ Cloud Deployment (Render Blueprint)

This project includes a ready-to-use [`render.yaml`](render.yaml) blueprint:

1. Push this repository to your GitHub account.
2. In the **[Render Dashboard](https://dashboard.render.com/)**, click **New +** -> **Blueprint**.
3. Select your repository. Render will automatically configure:
   - **Backend Web Service**: FastAPI on Python 3.11.
   - **Frontend Web Service**: Next.js 15 on Node.js 20.
4. Set your `GEMINI_API_KEY` in the environment settings and click **Apply**.

> **Note on Cloud vs. Local Modes**:
> - **Local Execution (`python run.py`)**: Has full access to your physical machine (Word, WhatsApp desktop, battery levels, local C:\ drive).
> - **Cloud Deployment (Render)**: Runs the conversational AI, real-time weather, web research, calendar, and notes database. Desktop automation runs in sandbox/simulated mode.

---

## 📂 Project Directory Structure

```text
AI-OS/
├── backend/
│   ├── agents/               # 8 Specialized Agent implementations
│   │   ├── browser_agent.py  # DuckDuckGo search & wttr.in live weather
│   │   ├── system_agent.py   # Telemetry, app launcher, process management
│   │   ├── document_agent.py # Word docx & PDF parser/summarizer
│   │   ├── memory_agent.py   # Long-term recall & preferences
│   │   ├── vision_agent.py   # Screenshot capture & PyAutoGUI
│   │   ├── email_agent.py    # SMTP email sender & drafting
│   │   ├── calendar_agent.py # Event scheduler & ICS generator
│   │   └── registry.py       # Agent discovery & lifecycle registry
│   ├── memory/
│   │   ├── db.py             # SQLite persistence layer
│   │   └── ai_os_memory.db   # Local memory database
│   ├── tests/
│   │   └── test_ai_os.py     # Comprehensive automated test suite
│   ├── ai_core.py            # Gemini LLM client with exponential retry
│   ├── executor.py           # Multi-step DAG executor with safety guards
│   ├── main.py               # FastAPI application & WebSocket handlers
│   ├── planner_agent.py      # Natural language plan decomposition
│   ├── requirements.txt      # Python dependencies
│   └── Procfile              # Cloud process declaration
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx      # Main glassmorphic dashboard & terminal UI
│   │       ├── layout.tsx    # App root layout & SEO metadata
│   │       └── globals.css   # Modern dark-mode styling
│   ├── package.json          # Node dependencies & Next.js scripts
│   └── next.config.ts        # Turbopack & Next.js configuration
├── run.py                    # Cross-platform 1-click startup script
├── render.yaml               # Render Cloud Blueprint infrastructure file
├── AI_OS_Dissertation_Final.pdf # Full Capstone Dissertation & Academic Report
└── README.md                 # Project documentation
```

---

## 👨‍💻 Author

**Rushit Khakhkhar**  
- Final Year Computer Science & Engineering Undergraduate  
- GitHub: [@khakhkharrushit](https://github.com/khakhkharrushit)  
- Email: khakhkharrushit@gmail.com

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
