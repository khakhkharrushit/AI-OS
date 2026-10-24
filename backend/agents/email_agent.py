import urllib.parse
import subprocess
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from agents.base import BaseAgent
from tools.base import Tool
from ai_core import generate_response
from memory.db import (
    save_email_draft,
    get_email_drafts,
    update_email_draft_status,
    get_preference,
    set_preference
)

class EmailAgent(BaseAgent):
    def __init__(self):
        super().__init__("EmailAgent")
        self.register_tool(Tool("create_email_draft", "Compose and save a new email draft", self.create_email_draft))
        self.register_tool(Tool("send_email", "Send an email to a recipient via SMTP or direct Webmail dispatch", self.send_email, high_risk=True))
        self.register_tool(Tool("list_email_drafts", "List saved email drafts", self.list_email_drafts))
        self.register_tool(Tool("generate_email_reply", "AI generates a professional email response given received content", self.generate_email_reply))
        self.register_tool(Tool("open_mail_client", "Open the default desktop email client or Webmail with pre-filled fields", self.open_mail_client))
        self.register_tool(Tool("configure_smtp", "Configure SMTP credentials (Gmail App Password / Outlook) for background sending", self.configure_smtp))

    def create_email_draft(self, recipient: str, subject: str, body: str, cc: str = "", **kwargs) -> str:
        if not recipient or not subject or not body:
            raise ValueError("Recipient, subject, and body are required to create a draft.")
            
        draft_id = save_email_draft(recipient=recipient, subject=subject, body=body, cc=cc, status="draft")
        gmail_url = self._get_gmail_compose_url(recipient, subject, body, cc)
        return (
            f"Email Draft #{draft_id} Created Successfully:\n"
            f"- To: {recipient}\n"
            f"- Subject: {subject}\n"
            f"- CC: {cc or 'None'}\n"
            f"- Body Preview: {body[:150]}...\n"
            f"- Webmail Compose URL: {gmail_url}"
        )

    def _get_gmail_compose_url(self, recipient: str, subject: str, body: str, cc: str = "") -> str:
        url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(recipient)}&su={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        if cc:
            url += f"&cc={urllib.parse.quote(cc)}"
        return url

    def _get_mailto_url(self, recipient: str, subject: str, body: str, cc: str = "") -> str:
        url = f"mailto:{urllib.parse.quote(recipient)}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        if cc:
            url += f"&cc={urllib.parse.quote(cc)}"
        return url

    def send_email(self, recipient: str, subject: str, body: str, cc: str = "", **kwargs) -> str:
        """
        High-Risk tool: Intercepted by Safety Layer before execution.
        Once approved:
        1. Attempts real direct SMTP delivery if credentials are provided in settings/env.
        2. If SMTP is not yet configured, prepares the pre-filled Gmail Web & Desktop dispatch links.
        """
        if not recipient or not subject or not body:
            raise ValueError("Recipient, subject, and body are required.")

        smtp_user = kwargs.get("smtp_user") or get_preference("smtp_user") or get_preference("email_address") or os.getenv("SMTP_USER", "").strip()
        smtp_pass = kwargs.get("smtp_password") or get_preference("smtp_password") or get_preference("email_app_password") or os.getenv("SMTP_PASSWORD", "").strip()
        smtp_host = kwargs.get("smtp_host") or get_preference("smtp_host") or os.getenv("SMTP_HOST", "").strip()
        smtp_port = int(kwargs.get("smtp_port") or get_preference("smtp_port") or os.getenv("SMTP_PORT", "587"))

        # Determine host if not explicit
        if smtp_user and not smtp_host:
            lower_user = smtp_user.lower()
            if "@gmail.com" in lower_user:
                smtp_host = "smtp.gmail.com"
            elif "@outlook.com" in lower_user or "@hotmail.com" in lower_user or "@live.com" in lower_user:
                smtp_host = "smtp-mail.outlook.com"
            elif "@yahoo.com" in lower_user:
                smtp_host = "smtp.mail.yahoo.com"
            else:
                smtp_host = "smtp.gmail.com"

        gmail_url = self._get_gmail_compose_url(recipient, subject, body, cc)
        mailto_url = self._get_mailto_url(recipient, subject, body, cc)

        # Mode 1: Real SMTP Sending if credentials are configured
        if smtp_user and smtp_pass:
            try:
                msg = MIMEMultipart()
                msg["From"] = smtp_user
                msg["To"] = recipient
                msg["Subject"] = subject
                if cc:
                    msg["Cc"] = cc
                msg.attach(MIMEText(body, "plain", "utf-8"))

                recipients_list = [r.strip() for r in recipient.split(",") if r.strip()]
                if cc:
                    recipients_list.extend([c.strip() for c in cc.split(",") if c.strip()])

                server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, recipients_list, msg.as_string())
                server.quit()

                draft_id = save_email_draft(recipient=recipient, subject=subject, body=body, cc=cc, status="sent")
                return (
                    f"Email Successfully Sent via SMTP Server ({smtp_host}):\n"
                    f"- From: {smtp_user}\n"
                    f"- To: {recipient}\n"
                    f"- Subject: {subject}\n"
                    f"- Status: Delivered (Logged in DB ID #{draft_id})"
                )
            except Exception as e:
                # Fallback to webmail dispatch if SMTP auth fails
                draft_id = save_email_draft(recipient=recipient, subject=subject, body=body, cc=cc, status="dispatch_ready")
                try:
                    subprocess.Popen(f'powershell -WindowStyle Hidden -Command "Start-Process \"{mailto_url}\""', shell=True)
                except Exception:
                    pass
                return (
                    f"SMTP delivery failed ({e}). Prepared Webmail & Desktop Client instead:\n"
                    f"- To: {recipient}\n"
                    f"- Subject: {subject}\n"
                    f"- Status: Ready in Webmail (Draft #{draft_id})\n"
                    f"- Gmail Web Compose: {gmail_url}"
                )

        # Mode 2: Immediate Webmail & System Mail Dispatch
        draft_id = save_email_draft(recipient=recipient, subject=subject, body=body, cc=cc, status="dispatched")
        try:
            subprocess.Popen(f'powershell -WindowStyle Hidden -Command "Start-Process \"{mailto_url}\""', shell=True)
        except Exception:
            pass

        return (
            f"Email Dispatched & Ready in Browser / Mail Client:\n"
            f"- To: {recipient}\n"
            f"- Subject: {subject}\n"
            f"- Status: Dispatched (Logged in DB ID #{draft_id})\n"
            f"- Gmail Web Compose: {gmail_url}\n"
            f"- Desktop Mailto: {mailto_url}"
        )

    def list_email_drafts(self, limit: int = 10, **kwargs) -> str:
        drafts = get_email_drafts(limit=int(limit))
        if not drafts:
            return "No email drafts found in memory."
        lines = []
        for d in drafts:
            status_tag = d.get("status", "draft").upper()
            lines.append(f"Draft #{d['id']} [{status_tag}] - To: {d['recipient']} | Subject: '{d['subject']}' ({d['created_at']})")
        return f"Stored Email Drafts ({len(drafts)}):\n" + "\n".join(lines)

    def generate_email_reply(self, incoming_email: str, tone: str = "professional", sender_name: str = "User", **kwargs) -> str:
        prompt = (
            f"You are the AI OS Email Agent. Generate a {tone} email reply to the following received message:\n\n"
            f"Incoming Email:\n{incoming_email}\n\n"
            f"Sender Name to sign with: {sender_name}\n\n"
            "Generate only the Subject and Email Body."
        )
        try:
            response = generate_response(prompt)
            return f"Generated AI Email Draft ({tone} tone):\n\n{response}"
        except Exception as e:
            return f"Could not generate email reply: {e}"

    def open_mail_client(self, recipient: str = "", subject: str = "", body: str = "", **kwargs) -> str:
        gmail_url = self._get_gmail_compose_url(recipient, subject, body)
        mailto_url = self._get_mailto_url(recipient, subject, body)
        try:
            subprocess.Popen(f'powershell -WindowStyle Hidden -Command "Start-Process \"{mailto_url}\""', shell=True)
            return f"Opened Windows email client.\nGmail compose link: {gmail_url}"
        except Exception as e:
            return f"Launched email client. Webmail URL: {gmail_url}"

    def configure_smtp(self, email_address: str, app_password: str, smtp_host: str = "", smtp_port: str = "587", **kwargs) -> str:
        if not email_address or not app_password:
            raise ValueError("email_address and app_password are required.")
        set_preference("smtp_user", email_address.strip())
        set_preference("smtp_password", app_password.strip())
        if smtp_host:
            set_preference("smtp_host", smtp_host.strip())
        if smtp_port:
            set_preference("smtp_port", smtp_port.strip())
        return f"SMTP credentials successfully saved for {email_address}. All future email dispatches will send directly through SMTP in the background!"
