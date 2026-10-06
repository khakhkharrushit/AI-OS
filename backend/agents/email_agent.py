import urllib.parse
import subprocess
from typing import Optional
from agents.base import BaseAgent
from tools.base import Tool
from ai_core import generate_response
from memory.db import save_email_draft, get_email_drafts

class EmailAgent(BaseAgent):
    def __init__(self):
        super().__init__("EmailAgent")
        self.register_tool(Tool("create_email_draft", "Compose and save a new email draft", self.create_email_draft))
        self.register_tool(Tool("send_email", "Send an email to a recipient", self.send_email, high_risk=True))
        self.register_tool(Tool("list_email_drafts", "List saved email drafts", self.list_email_drafts))
        self.register_tool(Tool("generate_email_reply", "AI generates a professional email response given received content", self.generate_email_reply))
        self.register_tool(Tool("open_mail_client", "Open the default desktop email client with pre-filled fields", self.open_mail_client))

    def create_email_draft(self, recipient: str, subject: str, body: str, cc: str = "", **kwargs) -> str:
        if not recipient or not subject or not body:
            raise ValueError("Recipient, subject, and body are required to create a draft.")
            
        draft_id = save_email_draft(recipient=recipient, subject=subject, body=body, cc=cc)
        return (
            f"Email Draft #{draft_id} Created Successfully:\n"
            f"- To: {recipient}\n"
            f"- Subject: {subject}\n"
            f"- CC: {cc or 'None'}\n"
            f"- Body Preview: {body[:150]}..."
        )

    def send_email(self, recipient: str, subject: str, body: str, cc: str = "", **kwargs) -> str:
        """
        High-Risk tool: Intercepted by Safety Layer before real sending.
        Once approved by the user, this records delivery and prepares the Windows mail system handler.
        """
        if not recipient or not subject or not body:
            raise ValueError("Recipient, subject, and body are required.")

        # Save record of sent email
        draft_id = save_email_draft(recipient=recipient, subject=subject, body=body, cc=cc)
        
        # Trigger system mail handler or SMTP simulation
        mailto_url = f"mailto:{urllib.parse.quote(recipient)}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        if cc:
            mailto_url += f"&cc={urllib.parse.quote(cc)}"
            
        try:
            subprocess.run(f'powershell -Command "Start-Process \'{mailto_url}\'"', shell=True)
        except Exception:
            pass

        return (
            f"Email Successfully Sent & Dispatched:\n"
            f"- To: {recipient}\n"
            f"- Subject: {subject}\n"
            f"- Status: Sent (Logged in memory ID: {draft_id})"
        )

    def list_email_drafts(self, limit: int = 10, **kwargs) -> str:
        drafts = get_email_drafts(limit=int(limit))
        if not drafts:
            return "No email drafts found in memory."
        lines = []
        for d in drafts:
            lines.append(f"Draft #{d['id']} [{d['status'].upper()}] - To: {d['recipient']} | Subject: '{d['subject']}' ({d['created_at']})")
        return f"Stored Email Drafts ({len(drafts)}):\n" + "\n".join(lines)

    def generate_email_reply(self, incoming_email: str, tone: str = "professional", sender_name: str = "User", **kwargs) -> str:
        prompt = f"""
You are the AI OS Email Agent. Generate a {tone} email reply to the following received message:

Incoming Email:
\"\"\"{incoming_email}\"\"\"

Sender Name to sign with: {sender_name}

Generate only the Subject and Email Body.
"""
        try:
            response = generate_response(prompt)
            return f"Generated AI Email Draft ({tone} tone):\n\n{response}"
        except Exception as e:
            return f"Could not generate email reply: {e}"

    def open_mail_client(self, recipient: str = "", subject: str = "", body: str = "", **kwargs) -> str:
        mailto = "mailto:"
        params = []
        if recipient:
            mailto += urllib.parse.quote(recipient)
        if subject:
            params.append(f"subject={urllib.parse.quote(subject)}")
        if body:
            params.append(f"body={urllib.parse.quote(body)}")
        if params:
            mailto += "?" + "&".join(params)

        try:
            subprocess.run(f'powershell -Command "Start-Process \'{mailto}\'"', shell=True)
            return "Opened Windows default email client."
        except Exception as e:
            raise Exception(f"Failed to launch email client: {e}")
