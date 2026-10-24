from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio
import psutil
import platform
from planner_agent import create_plan
from executor import execute_plan
from agents.registry import get_agent, get_all_agents
from memory.db import (
    log_task,
    get_all_preferences,
    set_preference,
    delete_preference,
    get_memory_facts,
    add_memory_fact,
    get_recent_tasks,
    get_calendar_events,
    add_calendar_event,
    delete_calendar_event,
    get_email_drafts,
    save_email_draft,
    get_workflows
)

app = FastAPI(title="AI OS Backend", version="1.0.0", description="Intelligent Natural-Language Operating System Layer")

# Allow CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = None
    pending_action_approved: Optional[Dict[str, Any]] = None

class PreferenceRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = ""

class FactRequest(BaseModel):
    topic: str
    content: str

class CalendarEventRequest(BaseModel):
    title: str
    event_date: str
    event_time: str = "10:00 AM"
    duration_minutes: int = 30
    description: Optional[str] = ""
    location: Optional[str] = ""

class EmailDraftRequest(BaseModel):
    recipient: str
    subject: str
    body: str
    cc: Optional[str] = ""

class EmailSendRequest(BaseModel):
    recipient: str
    subject: str
    body: str
    cc: Optional[str] = ""

class SMTPConfigRequest(BaseModel):
    email_address: str
    app_password: str
    smtp_host: Optional[str] = ""
    smtp_port: Optional[str] = "587" 

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US"

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    logs = []
    try:
        # Route 1: Resuming an approved action (with multi-step plan continuity)
        if request.pending_action_approved:
            action = request.pending_action_approved
            plan = action.get("plan")
            step_index = action.get("step_index", 0)
            user_query = action.get("user_query", "")
            
            if plan and "steps" in plan:
                logs, pending_action = await asyncio.to_thread(
                    execute_plan,
                    plan=plan,
                    user_query=user_query,
                    start_step_index=step_index,
                    bypass_first_safety=True
                )
                status = "awaiting_approval" if pending_action else "completed"
                log_task(user_query=f"[Approved Step {action.get('step_number')}] {user_query}", plan=plan, status=status, logs=logs)
                
                status_suffix = " (Subsequent action requires confirmation)." if pending_action else " Successfully finished all steps."
                reply = f"Resumed execution from Step {action.get('step_number', step_index + 1)}.{status_suffix}"
                return {
                    "reply": reply,
                    "agent_logs": logs,
                    "pending_action": pending_action
                }
            else:
                # Standalone action execution fallback
                logs = [f"Resuming execution: User approved Step {action.get('step_number')}"]
                agent = get_agent(action["agent_name"])
                if not agent:
                    logs.append(f"-> Error: Agent {action['agent_name']} not found.")
                    return {"reply": "Execution failed.", "agent_logs": logs, "pending_action": None}
                    
                response = await asyncio.to_thread(
                    agent.execute_tool,
                    action["tool_name"],
                    bypass_safety=True,
                    **action.get("arguments", {})
                )
                if response.error:
                    logs.append(f"-> Error executing tool: {response.error}")
                else:
                    logs.append(f"-> Success: {response.result}")
                logs.append("Plan execution completed.")
                log_task(user_query=f"[Approved Standalone] {action['tool_name']}", status="completed", logs=logs)
                return {"reply": "Execution resumed and completed.", "agent_logs": logs, "pending_action": None}

        # Route 2: Standard user message request
        plan = await asyncio.to_thread(create_plan, request.message, request.history)
        logs, pending_action = await asyncio.to_thread(execute_plan, plan, request.message)
        
        status = "awaiting_approval" if pending_action else "completed"
        log_task(user_query=request.message, plan=plan, status=status, logs=logs)
        
        # Collect meaningful success outputs from executed tools
        tool_results = []
        for l in logs:
            if l.startswith("-> Success:"):
                clean_res = l.replace("-> Success:", "").strip()
                if clean_res and not clean_res.startswith("Plan execution completed"):
                    tool_results.append(clean_res)

        base_reply = plan.get("response", "I have processed your request.")
        steps_list = plan.get("steps", []) if plan else []
        first_tool = steps_list[0].get("tool", "") if steps_list else ""

        if tool_results:
            last_result = tool_results[-1]
            if first_tool in ["get_weather", "get_battery_status", "get_system_info", "search_web", "list_processes"]:
                reply = last_result
            else:
                reply = f"{last_result}\n\n{base_reply}"
        else:
            reply = base_reply

        if steps_list:
            steps_text = "\n".join([f"- Step {s.get('step_number', idx+1)}: {s.get('description', '')} (Agent: {s.get('target_agent')})" for idx, s in enumerate(steps_list)])
            reply += f"\n\nPlanned Steps:\n{steps_text}"

        return {
            "reply": reply,
            "plan": plan,
            "agent_logs": logs,
            "pending_action": pending_action
        }
    except Exception as e:
        logs.append(f"Fatal error encountered: {str(e)}")
        log_task(user_query=request.message or "Unknown", status="failed", logs=logs)
        raise HTTPException(status_code=500, detail={"error": str(e), "logs": logs})

# --- System Diagnostics Endpoints ---

@app.get("/api/system/stats")
async def get_system_stats():
    """Live system metrics for frontend widgets."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        procs_count = len(psutil.pids())
        battery = psutil.sensors_battery()
        return {
            "os": f"{platform.system()} {platform.release()}",
            "cpu_percent": cpu,
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_percent": mem.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "process_count": procs_count,
            "battery_percent": battery.percent if battery else None,
            "power_plugged": battery.power_plugged if battery else None
        }
    except Exception as e:
        return {"error": str(e)}

# --- Agents Manifest Endpoint ---

@app.get("/api/agents")
async def list_agents_manifest():
    agents = get_all_agents()
    manifest = {}
    for name, ag in agents.items():
        manifest[name] = [
            {"name": t.name, "description": t.description, "high_risk": t.high_risk}
            for t in ag.tools.values()
        ]
    return {"agents": manifest}

# --- Workflows Endpoints ---

@app.get("/api/workflows")
async def get_workflows_endpoint():
    return {"workflows": get_workflows()}

# --- Memory Endpoints ---

@app.get("/api/memory/preferences")
async def get_preferences_endpoint():
    return {"preferences": get_all_preferences()}

@app.post("/api/memory/preferences")
async def set_preference_endpoint(req: PreferenceRequest):
    res = set_preference(req.key, req.value, req.description or "")
    return {"status": "ok", "preference": res}

@app.delete("/api/memory/preferences/{key}")
async def delete_preference_endpoint(key: str):
    success = delete_preference(key)
    return {"status": "ok" if success else "not_found"}

@app.get("/api/memory/facts")
async def get_facts_endpoint(topic: Optional[str] = None):
    return {"facts": get_memory_facts(topic)}

@app.post("/api/memory/facts")
async def add_fact_endpoint(req: FactRequest):
    fact_id = add_memory_fact(req.topic, req.content)
    return {"status": "ok", "id": fact_id}

@app.get("/api/memory/history")
async def get_history_endpoint(limit: int = 15):
    return {"history": get_recent_tasks(limit=limit)}

# --- Calendar Endpoints ---

@app.get("/api/calendar/events")
async def get_calendar_endpoint(limit: int = 20):
    return {"events": get_calendar_events(limit=limit)}

@app.post("/api/calendar/events")
async def create_calendar_endpoint(req: CalendarEventRequest):
    event_id = add_calendar_event(
        title=req.title,
        event_date=req.event_date,
        event_time=req.event_time,
        duration_minutes=req.duration_minutes,
        description=req.description or "",
        location=req.location or ""
    )
    return {"status": "ok", "id": event_id}

@app.delete("/api/calendar/events/{event_id}")
async def delete_calendar_endpoint(event_id: int):
    success = delete_calendar_event(event_id)
    return {"status": "ok" if success else "not_found"}

# --- Email Drafts Endpoints ---

@app.get("/api/email/drafts")
async def get_email_drafts_endpoint(limit: int = 15):
    return {"drafts": get_email_drafts(limit=limit)}

@app.post("/api/email/drafts")
async def create_email_draft_endpoint(req: EmailDraftRequest):
    draft_id = save_email_draft(
        recipient=req.recipient,
        subject=req.subject,
        body=req.body,
        cc=req.cc or ""
    )
    return {"status": "ok", "id": draft_id}

@app.post("/api/email/send")
async def send_email_endpoint(req: EmailSendRequest):
    agent = get_agent("EmailAgent")
    res = agent.execute_tool("send_email", bypass_safety=True, recipient=req.recipient, subject=req.subject, body=req.body, cc=req.cc or "")
    return {"status": "ok", "result": res.result, "error": res.error}

@app.post("/api/email/smtp-config")
async def set_smtp_config_endpoint(req: SMTPConfigRequest):
    agent = get_agent("EmailAgent")
    res = agent.execute_tool("configure_smtp", email_address=req.email_address, app_password=req.app_password, smtp_host=req.smtp_host or "", smtp_port=req.smtp_port or "587")
    return {"status": "ok", "message": res.result}

# --- Voice TTS Helper Endpoint ---

@app.post("/api/voice/tts")
async def tts_endpoint(req: TTSRequest):
    return {
        "status": "ready",
        "text": req.text,
        "voice": req.voice
    }

# --- WebSocket Live Streaming ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action_type = payload.get("type")
            
            if action_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif action_type == "system_pulse":
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                await websocket.send_json({
                    "type": "system_pulse",
                    "cpu": cpu,
                    "ram": mem.percent
                })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok", 
        "version": "1.0.0", 
        "agents_count": len(get_all_agents()),
        "agents": list(get_all_agents().keys())
    }

# --- Document Serving & Launch Endpoints ---

class DocumentActionRequest(BaseModel):
    path: str

@app.get("/api/documents/raw")
async def get_raw_document(path: str):
    import os
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    filename = os.path.basename(path)
    ext = os.path.splitext(filename)[1].lower()
    media_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".json": "application/json",
        ".html": "text/html; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    headers = {"Content-Disposition": f"inline; filename=\"{filename}\""}
    return FileResponse(path, media_type=media_type, headers=headers)

@app.post("/api/documents/launch")
async def launch_document_desktop(req: DocumentActionRequest):
    import os, subprocess
    if not req.path or not os.path.exists(req.path):
        raise HTTPException(status_code=404, detail="File not found")
    filepath = os.path.normpath(req.path)
    ext = os.path.splitext(filepath)[1].lower()
    msg = ""
    try:
        if ext in [".docx", ".doc"]:
            winword = r"C:\Program Files\Microsoft Office\Root\Office16\WINWORD.EXE"
            if os.path.exists(winword):
                subprocess.Popen([winword, filepath])
                msg = f"Opened in Microsoft Word: {os.path.basename(filepath)}"
            else:
                subprocess.Popen(f'cmd.exe /c start "" "{filepath}"', shell=True)
                msg = f"Opened with system default: {os.path.basename(filepath)}"
        elif ext in [".pptx", ".ppt"]:
            ppt = r"C:\Program Files\Microsoft Office\Root\Office16\POWERPNT.EXE"
            if os.path.exists(ppt):
                subprocess.Popen([ppt, filepath])
                msg = f"Opened in Microsoft PowerPoint: {os.path.basename(filepath)}"
            else:
                subprocess.Popen(f'cmd.exe /c start "" "{filepath}"', shell=True)
                msg = f"Opened with system default: {os.path.basename(filepath)}"
        elif ext in [".xlsx", ".xls"]:
            excel = r"C:\Program Files\Microsoft Office\Root\Office16\EXCEL.EXE"
            if os.path.exists(excel):
                subprocess.Popen([excel, filepath])
                msg = f"Opened in Microsoft Excel: {os.path.basename(filepath)}"
            else:
                subprocess.Popen(f'cmd.exe /c start "" "{filepath}"', shell=True)
                msg = f"Opened with system default: {os.path.basename(filepath)}"
        elif ext == ".pdf":
            edge = r"C:\Program Files (x86)\Microsoft Edge\Application\msedge.exe"
            chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if os.path.exists(edge):
                subprocess.Popen([edge, filepath])
                msg = f"Opened in Edge PDF Reader: {os.path.basename(filepath)}"
            elif os.path.exists(chrome):
                subprocess.Popen([chrome, filepath])
                msg = f"Opened in Chrome PDF Reader: {os.path.basename(filepath)}"
            else:
                subprocess.Popen(f'cmd.exe /c start "" "{filepath}"', shell=True)
                msg = f"Opened PDF with default app"
        elif ext in [".txt", ".md", ".json", ".log"]:
            subprocess.Popen(["notepad.exe", filepath])
            msg = f"Opened in Notepad: {os.path.basename(filepath)}"
        else:
            subprocess.Popen(f'cmd.exe /c start "" "{filepath}"', shell=True)
            msg = f"Launched {os.path.basename(filepath)}"
    except Exception as e:
        subprocess.Popen(f'explorer.exe /select,"{filepath}"', shell=True)
        msg = f"Revealed in Explorer fallback: {e}"
        
    return {"status": "ok", "result": msg}

@app.post("/api/documents/reveal")
async def reveal_document_explorer(req: DocumentActionRequest):
    import os, subprocess
    if not req.path or not os.path.exists(req.path):
        raise HTTPException(status_code=404, detail="File not found")
    norm_path = os.path.normpath(req.path)
    subprocess.Popen(f'explorer.exe /select,"{norm_path}"', shell=True)
    return {"status": "ok", "message": f"Revealed in Explorer: {norm_path}"}
