import time
from agents.registry import get_agent
from planner_agent import replan_after_failure

def execute_plan(
    plan: dict, 
    user_query: str = "", 
    start_step_index: int = 0, 
    bypass_first_safety: bool = False
) -> tuple[list[str], dict | None]:
    """
    Takes a structured JSON plan from the Planner Agent and routes it 
    to the correct Agent to execute the tools. Supports resumption after human approval
    and intelligent replanning upon tool execution errors.
    """
    logs = []
    steps = plan.get("steps", [])
    
    if not steps:
        logs.append("Plan contains no execution steps. Conversational reply only.")
        return logs, None

    step_idx = start_step_index
    total_steps = len(steps)

    while step_idx < total_steps:
        step = steps[step_idx]
        step_num = step.get("step_number", step_idx + 1)
        desc = step.get("description", "Unnamed step")
        agent_name = step.get("target_agent")
        tool_name = step.get("tool")
        kwargs = step.get("arguments", {})
        
        is_first_resumed_step = (step_idx == start_step_index and bypass_first_safety)
        if is_first_resumed_step:
            log_entry = f"Resuming Step {step_num}: {desc} [Approved by User] (Agent: {agent_name}, Tool: {tool_name})"
        else:
            log_entry = f"Executing Step {step_num}: {desc} (Agent: {agent_name}, Tool: {tool_name})"
        logs.append(log_entry)
        
        agent = get_agent(agent_name)
        if not agent:
            logs.append(f"-> Error: Agent '{agent_name}' not found in registry.")
            logs.append(f"-> Halting execution of remaining steps due to missing agent.")
            break
            
        logs.append(f"-> Routing to {agent_name}...")
        
        # Real execution via agent
        response = agent.execute_tool(
            tool_name, 
            bypass_safety=is_first_resumed_step, 
            **kwargs
        )
        
        if response.needs_confirmation:
            logs.append(f"-> SECURITY ALERT: {response.result}")
            logs.append(f"-> Awaiting human verification to proceed with high-risk action.")
            pending = {
                "step_number": step_num,
                "step_index": step_idx,
                "agent_name": agent_name,
                "tool_name": tool_name,
                "arguments": kwargs,
                "plan": plan,
                "user_query": user_query
            }
            return logs, pending
            
        if response.error:
            logs.append(f"-> Error executing tool '{tool_name}': {response.error}")
            logs.append(f"-> Triggering dynamic replanning with LLM...")
            
            # Attempt replanning
            recovery = replan_after_failure(user_query, step, response.error)
            if recovery.get("can_recover") and recovery.get("recovery_steps"):
                explanation = recovery.get("explanation", "Alternative steps formulated.")
                logs.append(f"-> Replanner found recovery path: {explanation}")
                recovery_steps = recovery.get("recovery_steps", [])
                
                # Execute recovery steps
                recovery_failed = False
                for r_step in recovery_steps:
                    r_desc = r_step.get("description", "Recovery step")
                    r_agent_name = r_step.get("target_agent")
                    r_tool_name = r_step.get("tool")
                    r_kwargs = r_step.get("arguments", {})
                    logs.append(f"-> Executing Recovery: {r_desc} (Agent: {r_agent_name}, Tool: {r_tool_name})")
                    r_agent = get_agent(r_agent_name)
                    if not r_agent:
                        logs.append(f"--> Error: Recovery Agent '{r_agent_name}' not found.")
                        recovery_failed = True
                        break
                    r_resp = r_agent.execute_tool(r_tool_name, **r_kwargs)
                    if r_resp.error:
                        logs.append(f"--> Recovery failed on '{r_tool_name}': {r_resp.error}")
                        recovery_failed = True
                        break
                    else:
                        logs.append(f"--> Recovery step success: {r_resp.result}")
                
                if recovery_failed:
                    logs.append("-> Replanning was unsuccessful. Halting remaining steps.")
                    break
                else:
                    logs.append("-> Recovery succeeded! Continuing remaining plan...")
                    step_idx += 1
                    continue
            else:
                reason = recovery.get("explanation", "No viable alternative found.")
                logs.append(f"-> Cannot replan: {reason}")
                logs.append(f"-> Halting execution of remaining steps.")
                break
            
        logs.append(f"-> Success: {response.result}")
        step_idx += 1
        # Dynamic delay between steps — gives apps and webpages time to load before next action
        if step_idx < total_steps:
            if tool_name == "open_url":
                url_arg = str(kwargs.get("url", "")).lower()
                if "whatsapp" in url_arg:
                    time.sleep(7.0)
                else:
                    time.sleep(2.0)
            elif tool_name == "click_screen_coordinate":
                time.sleep(1.0)
            elif tool_name == "type_desktop_text":
                time.sleep(2.2)
            elif tool_name == "open_application":
                time.sleep(2.0)
            else:
                time.sleep(1.0)
            
    logs.append("Plan execution completed.")
    return logs, None
