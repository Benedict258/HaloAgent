from app.services.whatsapp import whatsapp_service
from app.services.business import business_service
from app.services.contact import contact_service
from app.services.state import state_service
from app.services.meta_ai import meta_ai_service
from app.db.supabase_client import supabase
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class MessageOrchestrator:
    async def process_message(self, phone: str, message: str, message_id: str, to_number: str, channel: str = "whatsapp") -> str:
        """
        Process message with business resolution and auto-contact creation.
        
        Flow:
        1. Resolve business from to_number (WhatsApp number)
        2. Get or create contact (phone = contact ID)
        3. Check consent status
        4. Route to AI agent
        """
        
        # 1. Resolve business
        business = await business_service.get_business_by_whatsapp(to_number)
        if not business:
            logger.error(f"No business found for WhatsApp number: {to_number}")
            return "Service unavailable. Please contact support."
        
        business_id = business["business_id"]
        
        # 2. Get or create contact (phone = contact ID)
        contact = await contact_service.get_or_create_contact(phone, business_id)
        if not contact:
            return "Unable to process your message. Please try again."
        
        contact_id = contact["id"]
        contact_name = contact.get("name")
        opt_in = contact.get("opt_in", False)
        
        # Log incoming
        await self._log_message(phone, message, message_id, contact_id, direction="IN", channel=channel)
        
        # 3. Build context for agent
        context = f"Phone: {phone}, Business ID: {business_id}, Business Name: {business['business_name']}, Opt-in: {opt_in}, Channel: {channel}"
        if contact_name:
            context += f", Name: {contact_name}"
        
        # Add business inventory to context
        inventory = business.get("inventory", [])
        if inventory:
            context += f", Products: {json.dumps(inventory)}"
        
        # CRITICAL: Store business_id for agent to use in tool calls
        context += f"\n\nIMPORTANT: When calling tools, use business_id='{business_id}'"
            
        # 4. Run agent (handles tool calls internally)
        try:
            from app.services.agent.core import agent
            response_text = await agent.run(
                message,
                phone,
                context,
                business_id=business_id,
                channel=channel,
            )
            
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