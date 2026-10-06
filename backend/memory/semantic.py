import json
from typing import List, Dict, Any, Optional
from memory.db import get_workflows, search_workflow_templates, log_task

class SemanticWorkflowMemory:
    """
    Manages semantic and template-based workflow retrieval for common multi-step tasks.
    Enables instant plan formulation for repeated complex commands like:
    - 'Prepare my interview workspace'
    - 'Clean temporary files'
    - 'Daily standup briefing'
    """
    
    @staticmethod
    def find_matching_workflow(query: str) -> Optional[Dict[str, Any]]:
        """
        Searches available workflow templates for an immediate matching plan.
        """
        words = query.lower().split()
        for w in words:
            if len(w) > 3:
                matches = search_workflow_templates(w)
                if matches:
                    return matches[0]
        return None

    @staticmethod
    def get_all_templates() -> List[Dict[str, Any]]:
        return get_workflows()

semantic_memory = SemanticWorkflowMemory()
