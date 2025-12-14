from app.services.whatsapp import whatsapp_service
from app.services.intent import intent_service
from app.services.state import state_service
from app.services.meta_ai import meta_ai_service
from app.services.language import language_service
from app.services.analytics import analytics_service
from app.services.loyalty import loyalty_service
from app.db.supabase_client import supabase
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class MessageOrchestrator:
    async def process_message(self, phone: str, message: str, message_id: str, channel: str = "meta") -> str:
        """
        Process message using the AI Agent for natural interaction.
        """
        
        # 1. State Retrieval
        state = await state_service.get_state(phone)
        contact_id = state.get("contact_id")
        contact_name = state.get("name") # If available in state or need fetch
        if not contact_name and contact_id:
             # Ideally fetch name from DB if not in lightweight state
             pass

        # Log Incoming
        await self._log_message(phone, message, message_id, contact_id, direction="IN", channel=channel)
        
        # 2. Context Building
        # We pass minimal context to the Agent so it knows who it's talking to
        context = f"User Phone: {phone}. Channel: {channel}."
        if contact_name:
            context += f" Name: {contact_name}."
            
        # 3. AI Agent Execution
        # The Agent uses the System Prompt to decide: Greeting, Tool Call, or Clarification.
        try:
            from app.services.agent.core import agent
            response_text = await agent.run(message, phone, context)
        except Exception as e:
            logger.error(f"Agent flow failed: {e}")
            response_text = "I'm having a little trouble connecting right now. Please try again in a moment!"

        # 4. State Update (Minimal)
        # We update interaction time. Harder to track 'stage' without explicit signals from Agent, 
        # unless Agent returns it. For now, we rely on Conversation History in Agent Core.
        await state_service.update_state(phone, {"last_intent": "AGENT_PROCESSED"}) # simplified

        # Log Outgoing
        await self._log_message(phone, response_text, f"reply-{message_id}", contact_id, direction="OUT", is_bot=True, channel=channel)
        
        return response_text

    async def _log_message(self, phone: str, content: str, message_id: str, contact_id: int = None, direction: str = "IN", is_bot: bool = False, channel: str = "meta"):
        """Log message to database"""
        try:
            log_data = {
                "contact_id": contact_id,
                "message_id": message_id,
                "direction": direction,
                "message_type": "text",
                "content": content,
                "status": "sent" if is_bot else "received",
                "created_at": datetime.utcnow().isoformat()
            }
            if contact_id:
                supabase.table("message_logs").insert(log_data).execute()
        except Exception as e:
            logger.error(f"Failed to log message: {e}")
        print(f"[{direction}] {phone}: {content[:50]}...")

orchestrator = MessageOrchestrator()