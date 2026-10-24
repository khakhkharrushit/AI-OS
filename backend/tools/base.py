from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel

class ToolResponse(BaseModel):
    result: str
    error: Optional[str] = None
    needs_confirmation: bool = False

class Tool:
    def __init__(self, name: str, description: str, func: Callable, high_risk: bool = False):
        self.name = name
        self.description = description
        self.func = func
        self.high_risk = high_risk

    def execute(self, bypass_safety: bool = False, **kwargs) -> ToolResponse:
        """
        Execute the tool function. Integrates the Safety Validator Layer.
        """
        if self.high_risk and not bypass_safety:
            target_info = kwargs.get("target_name") or kwargs.get("filepath") or kwargs.get("folderpath") or kwargs.get("app_name") or kwargs.get("command") or ""
            target_desc = f" for '{target_info}'" if target_info else ""
            return ToolResponse(
                result=f"Security Alert: Execution of high-risk operation '{self.name}'{target_desc} requires human confirmation before proceeding.",
                needs_confirmation=True
            )
        try:
            result = self.func(**kwargs)
            return ToolResponse(result=str(result))
        except Exception as e:
            return ToolResponse(result="", error=str(e))
