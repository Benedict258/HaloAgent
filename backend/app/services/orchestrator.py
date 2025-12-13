from app.services.whatsapp import whatsapp_service
from app.services.agent.core import agent
from app.services.language import language_service
from app.services.analytics import analytics_service
from app.services.loyalty import loyalty_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MessageOrchestrator:
    async def process_message(self, phone: str, message: str, message_id: str):
        """Main message processing logic delegated to AI Agent"""
        # Log message
        await self._log_message(phone, message, message_id)
        
        # Get or create contact (Real DB lookup via loyalty service logic)
        # Note: Loyalty service has logic to find/create contact. Let's reuse it or access DB directly.
        # But 'loyalty_service' returns a dict or None.
        contact_data = await loyalty_service._get_or_create_contact(phone)
        contact_id = contact_data['id'] if contact_data else None
        contact_name = contact_data.get('name') if contact_data else None
        
        # Detect language
        language = language_service.detect_language(message)
        
        # Track interaction (General) - Pass ID not phone!
        if contact_id:
            await analytics_service.track_interaction(contact_id, "message_received", {"language": language})
        
        # Build Context
        context = f"Customer Name: {contact_name or 'Unknown'}. Language: {language}. Phone: {phone}."
        
        # 🤖 AGENT EXECUTION
        try:
            ai_response = await agent.run(message, phone, context)
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            ai_response = language_service.translate("welcome", language) # Fallback
            
        # Send Response
        await whatsapp_service.send_text(phone, ai_response)
        
        # Log response
        await self._log_message(phone, ai_response, "outbound", is_bot=True)
    
    async def _log_message(self, phone: str, content: str, message_id: str, is_bot: bool = False):
        """Log message to database"""
        # TODO: Implement actual database logging or usage message_logs table
        direction = "OUT" if is_bot else "IN"
        print(f"[{direction}] {phone}: {content[:50]}...")

orchestrator = MessageOrchestrator()