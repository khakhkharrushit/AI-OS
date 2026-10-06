import os
import sys
import pytest

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.registry import get_agent, get_all_agents
from agents.file_agent import FileAgent
from agents.system_agent import SystemAgent
from agents.memory_agent import MemoryAgent
from agents.browser_agent import BrowserAgent
from agents.document_agent import DocumentAgent
from agents.email_agent import EmailAgent
from agents.calendar_agent import CalendarAgent
from agents.vision_agent import VisionAgent
from executor import execute_plan
from memory.db import (
    init_db,
    set_preference,
    get_preference,
    get_all_preferences,
    add_memory_fact,
    get_memory_facts,
    add_calendar_event,
    get_calendar_events,
    delete_calendar_event,
    save_email_draft,
    get_email_drafts,
    get_workflows
)

def setup_module():
    init_db()

def test_agents_registry():
    all_agents = get_all_agents()
    expected_agents = [
        "FileAgent", "SystemAgent", "MemoryAgent", "BrowserAgent",
        "DocumentAgent", "EmailAgent", "CalendarAgent", "VisionAgent"
    ]
    for name in expected_agents:
        assert name in all_agents
        assert get_agent(name) is not None

def test_file_agent_lifecycle(tmp_path):
    agent = FileAgent()
    test_file = str(tmp_path / "test_doc.txt")
    
    # 1. Create file
    create_res = agent.create_file(test_file)
    assert "Created empty file" in create_res
    assert os.path.exists(test_file)
    
    # 2. Write file
    write_res = agent.write_file(test_file, "Hello AI OS World")
    assert "Successfully wrote" in write_res
    
    # 3. Read file
    read_res = agent.read_file(test_file)
    assert "Hello AI OS World" in read_res
    
    # 4. Append file
    agent.append_file(test_file, "\nSecond Line")
    read_res2 = agent.read_file(test_file)
    assert "Second Line" in read_res2
    
    # 5. Search file
    search_res = agent.search_file("test_doc", directory=str(tmp_path))
    assert "test_doc.txt" in search_res
    
    # 6. Delete file (Direct invocation)
    del_res = agent.delete_file(test_file)
    assert "Deleted" in del_res
    assert not os.path.exists(test_file)

def test_system_agent_info_and_process():
    agent = SystemAgent()
    
    # System info
    info = agent.get_system_info()
    assert "CPU Utilization" in info
    assert "RAM Usage" in info
    
    # Process listing
    procs = agent.list_processes(limit=5)
    assert "Top Running Processes" in procs

def test_memory_agent_and_db():
    agent = MemoryAgent()
    
    # Set preference
    pref_res = agent.set_user_preference("test_key", "test_value", "Testing preference")
    assert "test_value" in pref_res
    assert get_preference("test_key") == "test_value"
    
    # Memory fact
    fact_res = agent.save_memory_fact("pytest", "Testing fact recall")
    assert "Saved memory note" in fact_res
    facts = agent.search_memory_facts(topic="pytest")
    assert "Testing fact recall" in facts

def test_calendar_agent():
    agent = CalendarAgent()
    
    create_res = agent.create_calendar_event(
        title="AI OS Demo Presentation",
        event_date="2026-10-15",
        event_time="02:00 PM",
        duration_minutes=45,
        description="Demonstrating 100% full implementation"
    )
    assert "Scheduled Successfully" in create_res
    
    events = agent.list_upcoming_events()
    assert "AI OS Demo Presentation" in events

def test_email_agent():
    agent = EmailAgent()
    
    draft_res = agent.create_email_draft(
        recipient="team@aios.org",
        subject="Project 1 Completion",
        body="All 7 phases are now fully implemented."
    )
    assert "Created Successfully" in draft_res
    
    drafts = agent.list_email_drafts()
    assert "Project 1 Completion" in drafts

def test_document_agent(tmp_path):
    agent = DocumentAgent()
    md_file = str(tmp_path / "summary.md")
    
    report_res = agent.create_markdown_report(
        filepath=md_file,
        title="Project Report",
        content="This is an automated test report."
    )
    assert "Successfully created Markdown report" in report_res
    assert os.path.exists(md_file)
    
    search_res = agent.search_document_text(md_file, "automated")
    assert "automated" in search_res

def test_safety_interception():
    file_agent = get_agent("FileAgent")
    # Delete tool has high_risk=True
    resp = file_agent.execute_tool("delete_file", bypass_safety=False, filepath="dummy.txt")
    assert resp.needs_confirmation is True
    assert "Blocked" in resp.result

def test_executor_plan_and_safety_halt():
    plan = {
        "response": "Executing multi-step safety test",
        "steps": [
            {
                "step_number": 1,
                "description": "Get system info",
                "target_agent": "SystemAgent",
                "tool": "get_system_info",
                "arguments": {}
            },
            {
                "step_number": 2,
                "description": "Delete temporary file",
                "target_agent": "FileAgent",
                "tool": "delete_file",
                "arguments": {"filepath": "sample.txt"}
            }
        ]
    }
    
    logs, pending = execute_plan(plan, user_query="Test safety")
    assert pending is not None
    assert pending["tool_name"] == "delete_file"
    assert pending["step_number"] == 2
