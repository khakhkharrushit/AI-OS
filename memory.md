# AI OS Design & Progress Memory

This document tracks our ongoing development progress, technical decisions, and the reasoning behind them.

## Phase 1 (Completed)
- **Decision:** Split into separate Next.js (frontend) and FastAPI (backend) projects.
  - **Why:** Separating concerns makes it easier to scale the complex multi-agent logic in Python while maintaining a modern, snappy, and interactive React UI.
- **Decision:** Used Gemini API (Free Tier) for reasoning.
  - **Why:** Provides powerful reasoning capabilities required for the Planner Agent without upfront costs.
- **Decision:** Implemented `tenacity` for exponential backoff on Gemini API calls.
  - **Why:** To gracefully handle the 15 Requests-Per-Minute (RPM) rate limit on the free tier, ensuring the system retries instead of crashing during heavy multi-agent loops.

## Phase 2 (Completed: Intelligent Planning)
- **Decision:** The Planner Agent returns a structured JSON payload instead of unstructured text.
  - **Why:** JSON parsing allows the new Executor module to programmatically iterate over the steps, determine which Agent handles it, and call the correct tools automatically without relying on brittle regex parsing.
- **Decision:** Display Agent Execution Logs directly in the chat UI.
  - **Why:** The AI OS requires transparency. By showing the user exactly what the Planner decided and how the Executor simulated those steps, the user builds trust in the system.

## Phase 3 (Completed: Multi-Agent System)
- **Decision:** Built a central `Tool` class with a `high_risk` flag.
  - **Why:** This automatically handles the Validation and Safety layer. If an Agent tries to execute a high-risk tool (like `delete_file`), it halts and returns a `needs_confirmation` response.
- **Decision:** Used a dynamic Agent Registry.
  - **Why:** The Executor just calls `get_agent(name)` and dynamically routes the JSON step without needing hardcoded `if/else` statements for every new agent we add.
- **Decision:** Built a native Human Verification UI.
  - **Why:** The backend was successfully halting high-risk commands, but the user needed an interactive way to approve the action. We passed a `pending_action` object back to the UI to render an "Approve Execution" button, which pings the backend to resume bypassing safety.
- **Decision:** Implemented OneDrive Desktop sync normalization in `FileAgent` and `SystemAgent`.
  - **Why:** Windows 11 secretly moves standard folders (like Desktop) to OneDrive paths. The AI predicts standard paths (e.g., `~/Desktop`). Normalization automatically maps these guesses to reality to prevent `FileNotFoundError`s.
- **Decision:** Upgraded `open_application` to use PowerShell `Start-Process` and `.lnk` shortcut scanning.
  - **Why:** `cmd /c start` pops up a blocking Windows GUI error when it fails, which hides the error from Python. PowerShell silently fails, allowing Python to catch it and gracefully fall back to searching the Desktop for game shortcuts (like `VALORANT.lnk`).
- **Decision:** Updated the Planner Agent's JSON schema to include a conversational `response` field.
  - **Why:** When the user said "hello", the AI previously tried to use the `system_command` tool to force the OS to print a reply into the technical execution logs! The new schema allows the AI to leave the steps empty and reply natively.

## Phase 3 Bug Fixes & Tool Extensions (Completed)
- **Decision:** Multi-Step Plan Resumption with Context Passing.
  - **Why:** Previously, approving a high-risk action caused `main.py` to execute only the pending action and terminate, dropping all subsequent steps. We refactored `execute_plan` to accept `start_step_index` and `bypass_first_safety=True`, enabling the executor to resume and complete all remaining steps.
- **Decision:** Integrated Dynamic Replanning on Failure (`replan_after_failure`).
  - **Why:** When tool executions failed, the system previously halted immediately. Now, `executor.py` triggers an automated recovery query to Gemini to find alternative paths (e.g. fallback apps or alternative search directories).
- **Decision:** Expanded `FileAgent` and `SystemAgent` Toolset.
  - **Why:** Integrated `read_file`, `write_file`, `append_file`, `copy_file`, `create_folder`, and `list_directory` into `FileAgent`, and added `get_system_info` (CPU/RAM/Disk metrics via `psutil`) and `list_processes` to `SystemAgent`.
- **Decision:** Conversation History Context in `ChatRequest` & `create_plan`.
  - **Why:** Prevents conversational amnesia. Prior turns are included in the Planner prompt so follow-up commands understand references to files and previous actions.
- **Decision:** Added `backend/requirements.txt`.
  - **Why:** To make the backend environment reproducible.

## Phase 4: Web & Desktop Automation (Completed)
- **Decision:** WhatsApp Web & Browser Multi-Step Messaging Pipeline.
  - **Why:** Complex natural language requests like "open whatsapp web and message Ashutosh 'hi'" combine web opening, UI element search, contact selection, and keystroke automation. Added dedicated multi-agent sequencing (`BrowserAgent.open_url` -> `VisionAgent.press_hotkey('ctrl+alt+/')` -> `VisionAgent.type_desktop_text` -> `VisionAgent.press_hotkey('enter')`).
- **Decision:** Prevented CMD Window Popups & Fixed Application Disambiguation.
  - **Why:** SystemAgent's fallback previously invoked `cmd.exe /c start` for unknown tokens (such as human contact names), causing black CMD windows and syntax errors. Added validation via `shutil.which` and `subprocess.CREATE_NO_WINDOW` flags across all agents.
- **Decision:** Upgraded AI Reasoning Model to `gemini-3.5-flash-lite`.
  - **Why:** Replaced deprecated model references with `gemini-3.5-flash-lite`, offering sub-second planning latency and zero rate limit timeouts.
- **Decision:** Windows Desktop Shell (`explorer.exe`) Document Launching.
  - **Why:** Background Python subprocesses calling `WINWORD.EXE` directly can cause Word to start in headless COM mode or remain hidden behind active browser windows. Spawning files through `explorer.exe <filepath>` invokes the native Windows Desktop Shell, opening files with full interactive GUI elevation in the active user session.

## Phase 5 (Upcoming: Memory Architecture & Embeddings)
- **Goal:** Structured SQLite preference storage and vector embeddings for contextual retrieval.

