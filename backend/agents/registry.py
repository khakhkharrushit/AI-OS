from agents.file_agent import FileAgent
from agents.system_agent import SystemAgent
from agents.memory_agent import MemoryAgent
from agents.browser_agent import BrowserAgent
from agents.document_agent import DocumentAgent
from agents.email_agent import EmailAgent
from agents.calendar_agent import CalendarAgent
from agents.vision_agent import VisionAgent

# Initialize and register all 8 specialized agents
agents_registry = {
    "FileAgent": FileAgent(),
    "SystemAgent": SystemAgent(),
    "MemoryAgent": MemoryAgent(),
    "BrowserAgent": BrowserAgent(),
    "DocumentAgent": DocumentAgent(),
    "EmailAgent": EmailAgent(),
    "CalendarAgent": CalendarAgent(),
    "VisionAgent": VisionAgent()
}

def get_agent(agent_name: str):
    return agents_registry.get(agent_name)

def get_all_agents():
    return agents_registry
