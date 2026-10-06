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
                logs, pending_action = execute_plan(
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
                    
                response = agent.execute_tool(action["tool_name"], bypass_safety=True, **action.get("arguments", {}))
                if response.error:
                    logs.append(f"-> Error executing tool: {response.error}")
                else:
                    logs.append(f"-> Success: {response.result}")
                logs.append("Plan execution completed.")
                log_task(user_query=f"[Approved Standalone] {action['tool_name']}", status="completed", logs=logs)
                return {"reply": "Execution resumed and completed.", "agent_logs": logs, "pending_action": None}

        # Route 2: Standard user message request
        plan = create_plan(request.message, history=request.history)
        logs, pending_action = execute_plan(plan, user_query=request.message)
        
        status = "awaiting_approval" if pending_action else "completed"
        log_task(user_query=request.message, plan=plan, status=status, logs=logs)
        
        reply = plan.get("response", "I have processed your request.")
        if plan and plan.get("steps"):
            steps_text = "\n".join([f"- Step {s.get('step_number', idx+1)}: {s.get('description', '')} (Agent: {s.get('target_agent')})" for idx, s in enumerate(plan.get("steps", []))])
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
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        procs_count = len(psutil.pids())
        return {
            "os": f"{platform.system()} {platform.release()}",
            "cpu_percent": cpu,
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_percent": mem.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "process_count": procs_count
        }
    except Exception as e:
        return {"error": str(e)}

# --- Agents Manifest Endpoint ---

@app.get("/api/agents")
async def list_agents_manifest():
    """Returns active agents and their available tools."""
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
    """Returns preset workflow templates."""
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

# --- Voice TTS Helper Endpoint ---

@app.post("/api/voice/tts")
async def tts_endpoint(req: TTSRequest):
    """Provides TTS text normalization or response confirmation."""
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
