import os
import httpx
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from agenticai_sdk.db.database import get_session
from agenticai_sdk.db.models import IntegrationConnection
from langchain_core.tools import tool, StructuredTool

logger = logging.getLogger("agenticai_sdk.integration_registry")

class IntegrationRegistry:
    """Central registry managing authentication, state, and execution interfaces
    for third-party integrations (Slack, Teams, Outlook, WhatsApp).
    """

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id

    def get_connection(self, integration_type: str) -> Optional[Dict[str, Any]]:
        db = next(get_session())
        try:
            conn_id = f"{self.workspace_id}:{integration_type}"
            conn = db.query(IntegrationConnection).filter(
                IntegrationConnection.id == conn_id,
                IntegrationConnection.is_active == 1
            ).first()
            if not conn:
                return None
            return {
                "id": conn.id,
                "workspace_id": conn.workspace_id,
                "integration_type": conn.integration_type,
                "name": conn.name,
                "auth_state": conn.auth_state,
                "rate_limits": conn.rate_limits
            }
        finally:
            db.close()

    def register_connection(self, integration_type: str, name: str, auth_state: Dict[str, Any], rate_limits: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if integration_type not in ("slack", "outlook", "teams", "whatsapp"):
            raise ValueError(f"Unsupported integration type: {integration_type}")
        
        db = next(get_session())
        try:
            conn_id = f"{self.workspace_id}:{integration_type}"
            conn = db.query(IntegrationConnection).filter(IntegrationConnection.id == conn_id).first()
            if conn:
                conn.name = name
                conn.auth_state = auth_state
                conn.rate_limits = rate_limits
                conn.is_active = 1
            else:
                conn = IntegrationConnection(
                    id=conn_id,
                    workspace_id=self.workspace_id,
                    integration_type=integration_type,
                    name=name,
                    auth_state=auth_state,
                    rate_limits=rate_limits,
                    is_active=1
                )
                db.add(conn)
            
            db.commit()
            logger.info(f"Registered integration connection: {conn_id}")
            return {
                "id": conn.id,
                "workspace_id": conn.workspace_id,
                "integration_type": conn.integration_type,
                "name": conn.name,
                "auth_state": conn.auth_state
            }
        finally:
            db.close()

    def get_tools(self) -> List[StructuredTool]:
        """Exposes standard LangChain tools constructed dynamically from active integration parameters."""
        tools = []
        
        # 1. Slack Connector Tool
        slack_conn = self.get_connection("slack")
        if slack_conn:
            tools.append(self._build_slack_tool(slack_conn))

        # 2. MS Teams Connector Tool
        teams_conn = self.get_connection("teams")
        if teams_conn:
            tools.append(self._build_teams_tool(teams_conn))

        # 3. Outlook Connector Tool
        outlook_conn = self.get_connection("outlook")
        if outlook_conn:
            tools.append(self._build_outlook_tool(outlook_conn))

        # 4. WhatsApp Connector Tool
        whatsapp_conn = self.get_connection("whatsapp")
        if whatsapp_conn:
            tools.append(self._build_whatsapp_tool(whatsapp_conn))

        return tools

    def _build_slack_tool(self, connection: Dict[str, Any]) -> StructuredTool:
        auth = connection["auth_state"]
        webhook_url = auth.get("webhook_url") or os.getenv("SLACK_WEBHOOK_URL")

        async def send_slack_message(channel: str, text: str) -> str:
            """Sends a message to a specific Slack channel via webhook or API token."""
            payload = {"channel": channel, "text": text}
            if webhook_url:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(webhook_url, json={"text": f"[{channel}] {text}"})
                    if resp.status_code == 200:
                        return f"Message sent successfully to Slack channel {channel}"
                    return f"Slack webhook returned error: {resp.text}"
            token = auth.get("access_token")
            if token:
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                async with httpx.AsyncClient() as client:
                    resp = await client.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload)
                    res_json = resp.json()
                    if res_json.get("ok"):
                        return f"Message sent successfully to Slack channel {channel}"
                    return f"Slack API error: {res_json.get('error')}"
            return "[Mock] Slack connection found, but no valid webhook or OAuth token. Message would be: " + text

        return StructuredTool.from_function(
            coroutine=send_slack_message,
            name="send_slack_message",
            description="Send notifications or messages to a Slack channel."
        )

    def _build_teams_tool(self, connection: Dict[str, Any]) -> StructuredTool:
        auth = connection["auth_state"]
        webhook_url = auth.get("webhook_url") or os.getenv("TEAMS_WEBHOOK_URL")

        async def send_teams_message(text: str) -> str:
            """Sends a message to an MS Teams channel via Office 365 Connector Webhook."""
            if webhook_url:
                payload = {"text": text}
                async with httpx.AsyncClient() as client:
                    resp = await client.post(webhook_url, json=payload)
                    if resp.status_code in (200, 201, 202):
                        return "Message posted to MS Teams successfully."
                    return f"Teams webhook returned error: {resp.text}"
            return "[Mock] MS Teams connection verified. Message would be: " + text

        return StructuredTool.from_function(
            coroutine=send_teams_message,
            name="send_teams_message",
            description="Send high-priority notification cards to MS Teams channels."
        )

    def _build_outlook_tool(self, connection: Dict[str, Any]) -> StructuredTool:
        auth = connection["auth_state"]

        async def send_outlook_email(to_email: str, subject: str, body: str) -> str:
            """Sends an email via Microsoft Graph API on behalf of the authorized user account."""
            token = auth.get("access_token")
            if token:
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                payload = {
                    "message": {
                        "subject": subject,
                        "body": {"contentType": "HTML", "content": body},
                        "toRecipients": [{"emailAddress": {"address": to_email}}]
                    }
                }
                async with httpx.AsyncClient() as client:
                    resp = await client.post("https://graph.microsoft.com/v1.0/me/sendMail", headers=headers, json=payload)
                    if resp.status_code == 202:
                        return f"Email sent successfully via Outlook to {to_email}"
                    return f"Outlook API returned status {resp.status_code}: {resp.text}"
            return f"[Mock] Outlook connection active. Email mock sent to {to_email} with subject: {subject}"

        return StructuredTool.from_function(
            coroutine=send_outlook_email,
            name="send_outlook_email",
            description="Draft and send custom emails via Outlook Graph API."
        )

    def _build_whatsapp_tool(self, connection: Dict[str, Any]) -> StructuredTool:
        auth = connection["auth_state"]

        async def send_whatsapp_message(to_number: str, message: str) -> str:
            """Sends a WhatsApp text message using Meta Cloud API or Twilio credentials."""
            phone_number_id = auth.get("phone_number_id")
            token = auth.get("access_token")
            if phone_number_id and token:
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to_number,
                    "type": "text",
                    "text": {"body": message}
                }
                url = f"https://graph.facebook.com/v15.0/{phone_number_id}/messages"
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        return f"WhatsApp message successfully sent to {to_number}"
                    return f"WhatsApp Graph API error: {resp.text}"
            return f"[Mock] WhatsApp message successfully dispatched to {to_number}. Payload: {message}"

        return StructuredTool.from_function(
            coroutine=send_whatsapp_message,
            name="send_whatsapp_message",
            description="Send direct text alerts to registered client phone numbers via WhatsApp API."
        )
