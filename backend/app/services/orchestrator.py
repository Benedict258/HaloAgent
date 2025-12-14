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
        Process message using the AI Agent - handles tool calls silently and returns natural responses.
        """
        
        # 1. Get contact info
        state = await state_service.get_state(phone)
        contact_id = state.get("contact_id")
        contact_name = state.get("name")
        
        # Log incoming
        await self._log_message(phone, message, message_id, contact_id, direction="IN", channel=channel)
        
        # 2. Build context for agent
        context = f"Phone: {phone}"
        if contact_name:
            context += f", Name: {contact_name}"
            
        # 3. Run agent (handles tool calls internally)
        try:
            from app.services.agent.core import agent
            response_text = await agent.run(message, phone, context)
            
            # Clean up any leaked technical language
            response_text = self._sanitize_response(response_text)
            
        except Exception as e:
            logger.error(f"Agent error: {e}")
            response_text = "I'm having a little trouble right now. Give me a moment and try again!"

        # 4. Update state
        await state_service.update_state(phone, {"last_message_ts": datetime.utcnow().isoformat()})

        # Log outgoing
        await self._log_message(phone, response_text, f"reply-{message_id}", contact_id, direction="OUT", is_bot=True, channel=channel)
        
        return response_text
    
    def _sanitize_response(self, text: str) -> str:
        """Remove any technical language that leaked into user response"""
        # Remove common technical phrases
        bad_phrases = [
            "I will classify",
            "intent_classifier",
            "tool_call",
            "parameters",
            "action",
            "final_answer",
            "Let me process",
            "Processing your request"
        ]
        
        for phrase in bad_phrases:
            if phrase.lower() in text.lower():
                # If technical language detected, return friendly fallback
                return "Got it! Let me help you with that."
        
        return text

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