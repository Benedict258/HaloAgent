from app.services.whatsapp import whatsapp_service
from app.services.agent.core import agent
from app.services.language import language_service
from app.services.analytics import analytics_service
from app.services.loyalty import loyalty_service
from app.db.supabase_client import supabase
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MessageOrchestrator:
    async def process_message(self, phone: str, message: str, message_id: str, channel: str = "meta") -> str:
        """Main message processing logic delegated to AI Agent"""
        
        # Get or create contact (Real DB lookup via loyalty service logic)
        contact_data = await loyalty_service._get_or_create_contact(phone)
        contact_id = contact_data['id'] if contact_data else None
        contact_name = contact_data.get('name') if contact_data else None
        
        # Log message (Incoming)
        await self._log_message(phone, message, message_id, contact_id, direction="IN", channel=channel)
        
        # Detect language
        language = language_service.detect_language(message)
        
        # Track interaction (General)
        if contact_id:
            await analytics_service.track_interaction(contact_id, "message_received", {"language": language, "channel": channel})
        
        # Build Context
        context = f"Customer Name: {contact_name or 'Unknown'}. Language: {language}. Phone: {phone}. Channel: {channel}."
        
        # 🤖 AGENT EXECUTION
        try:
            ai_response = await agent.run(message, phone, context)
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            ai_response = language_service.translate("welcome", language) # Fallback
            
        # Log response (Outgoing) — Bot response usually doesn't have an external ID yet, use 'bot-reply'
        await self._log_message(phone, ai_response, f"reply-{message_id}", contact_id, direction="OUT", is_bot=True, channel=channel)
        
        return ai_response
    
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
                # Schema might need 'channel' column if we want to store it, currently not in provided schema
            }
            # If contact_id is None, we might skip or fail. Schema FK usually requires it.
            if contact_id:
                supabase.table("message_logs").insert(log_data).execute()
        except Exception as e:
            logger.error(f"Failed to log message: {e}")
            
        print(f"[{direction}] {phone}: {content[:50]}...")

orchestrator = MessageOrchestrator()