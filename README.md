# 🚀 AI Operating System (AI OS)
### Intelligent Natural-Language Operating System Orchestrator
**Final Year Engineering Capstone Project | Built by [Rushit Khakhkhar](https://github.com/khakhkharrushit)**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-ai--os--frontend.onrender.com-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://ai-os-frontend.onrender.com)
[![API Docs](https://img.shields.io/badge/FastAPI%20Swagger-ai--os--backend.onrender.com%2Fdocs-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://ai-os-backend.onrender.com/docs)
[![Tests](https://img.shields.io/badge/Pytest-9%2F9%20Passing%20(100%25)-success?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)

---

> 🌐 **Live Cloud Demo**: [https://ai-os-frontend.onrender.com](https://ai-os-frontend.onrender.com)  
> 📖 **Interactive OpenAPI Docs**: [https://ai-os-backend.onrender.com/docs](https://ai-os-backend.onrender.com/docs)  
> 💻 **Full Local Desktop Agent**: Run `python run.py` locally for native access to your PC (Word, WhatsApp desktop, battery, local files).  
> 📄 **Academic Dissertation**: View the full project report at [`AI_OS_Dissertation_Final.pdf`](AI_OS_Dissertation_Final.pdf).

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

## 🌐 Live Cloud Demo vs. Local Desktop Execution

| Feature | 🌐 Live Cloud Demo (Render) | 💻 Local Desktop Mode (`run.py`) |
| :--- | :---: | :---: |
| **URL / Access** | [ai-os-frontend.onrender.com](https://ai-os-frontend.onrender.com) | `http://localhost:3000` |
| **Natural Language AI Chat** | ✅ Active (Gemini 1.5/2.0) | ✅ Active (Gemini 1.5/2.0) |
| **Live Weather & Geolocation** | ✅ Active (`wttr.in`) | ✅ Active (`wttr.in`) |
| **DuckDuckGo Web Research** | ✅ Active | ✅ Active |
| **Calendar & Memory DB** | ✅ Active | ✅ Active |
| **Open Native Word / Chrome / Explorer** | Cloud Sandbox Mode | ✅ Directly Opens on Your Screen |
| **Desktop WhatsApp Automation** | Cloud Sandbox Mode | ✅ Types & Sends in WhatsApp App |
| **Physical Laptop Battery & CPU** | Server VM Telemetry | ✅ Reads Your Machine's Hardware |
| **Local File System Access** | Isolated Cloud Sandbox | ✅ Full Access to Local Hard Drive |

---

## 🚀 Running Locally (1-Click Setup)

To test the full desktop agent with native access to your computer:

```bash
# 1. Clone the repository
git clone https://github.com/khakhkharrushit/AI-OS.git
cd AI-OS

# 2. Run the 1-click launcher
python run.py
```

`run.py` automatically:
1. Validates your Python and Node environments.
2. Initializes `backend/.env` with your `GEMINI_API_KEY`.
3. Launches the FastAPI Backend on `http://127.0.0.1:8000`.
4. Launches the Next.js Frontend on `http://localhost:3000`.
5. Opens your default web browser to the dashboard.

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
│   └── Procfile              # Render cloud process configuration
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx      # Main glassmorphic dashboard & terminal UI
│   │       ├── layout.tsx    # App root layout & SEO metadata
│   │       └── globals.css   # Modern dark-mode styling
│   ├── package.json          # Node dependencies & Next.js scripts
│   └── next.config.ts        # Turbopack & Next.js configuration
├── run.py                    # Cross-platform 1-click startup script
├── render.yaml               # Render Cloud Infrastructure Blueprint
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
