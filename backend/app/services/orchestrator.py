from app.services.whatsapp import whatsapp_service
from app.services.meta_ai import meta_ai_service
from app.services.language import language_service
from app.services.loyalty import loyalty_service
from app.services.analytics import analytics_service
from app.services.compliance import compliance_service
import re
from datetime import datetime

class MessageOrchestrator:
    def __init__(self):
        self.order_keywords = ["order", "buy", "purchase", "want", "need", "price"]
        self.complaint_keywords = ["problem", "issue", "complaint", "wrong", "bad", "terrible"]
        self.privacy_keywords = ["privacy", "delete", "data", "gdpr", "ndpa", "consent"]
    
    async def process_message(self, phone: str, message: str, message_id: str):
        """Main message processing logic"""
        # Log message
        await self._log_message(phone, message, message_id)
        
        # Get or create contact
        contact = await self._get_or_create_contact(phone)
        
        # Detect language
        language = language_service.detect_language(message)
        
        # Determine intent
        intent = self._classify_intent(message)
        
        # Handle privacy/compliance requests first
        if intent == "privacy":
            await self._handle_privacy_request(phone, message, language)
            return
        
        # Track interaction
        await analytics_service.track_interaction(phone, intent, {"language": language})
        
        # Generate context-aware response
        context = f"Customer: {contact.name or 'Unknown'}, Intent: {intent}, Language: {language}"
        ai_response = await meta_ai_service.generate_response(message, context)
        
        # Handle specific intents
        if intent == "order":
            await self._handle_order_intent(phone, message, ai_response, language)
        elif intent == "complaint":
            await self._handle_complaint_intent(phone, message, ai_response, language)
        else:
            # Use localized response if available
            localized_response = language_service.translate("welcome", language)
            await whatsapp_service.send_text(phone, ai_response or localized_response)
        
        # Log response
        await self._log_message(phone, ai_response, "outbound", is_bot=True)
    
    def _classify_intent(self, message: str) -> str:
        """Simple intent classification"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in self.privacy_keywords):
            return "privacy"
        elif any(keyword in message_lower for keyword in self.order_keywords):
            return "order"
        elif any(keyword in message_lower for keyword in self.complaint_keywords):
            return "complaint"
        else:
            return "general"
    
    async def _handle_order_intent(self, phone: str, message: str, ai_response: str, language: str = "en"):
        """Handle order-related messages"""
        # Create order record
        # For now, just send AI response with localized confirmation
        confirmation = language_service.translate("order_received", language)
        await whatsapp_service.send_text(phone, f"{ai_response}\n\n{confirmation}")
        
        # Award loyalty points (placeholder amount)
        await loyalty_service.award_points(phone, 1000.0, "order")
    
    async def _handle_complaint_intent(self, phone: str, message: str, ai_response: str, language: str = "en"):
        """Handle complaint messages"""
        # Log as feedback for later processing
        acknowledgment = language_service.translate("complaint_acknowledged", language)
        await whatsapp_service.send_text(phone, f"{acknowledgment}\n\n{ai_response}")
        
        # Track complaint for analytics
        await analytics_service.track_interaction(phone, "complaint", {"message": message})
    
    async def _handle_privacy_request(self, phone: str, message: str, language: str = "en"):
        """Handle privacy and data requests"""
        message_lower = message.lower()
        
        if "delete" in message_lower or "remove" in message_lower:
            response = await compliance_service.handle_data_deletion_request(phone)
            await whatsapp_service.send_text(phone, response)
        elif "privacy" in message_lower or "policy" in message_lower:
            consent_msg = await compliance_service.request_consent(phone, "customer service")
            await whatsapp_service.send_text(phone, consent_msg)
        elif message_lower in ['yes', 'y', 'no', 'n']:
            consent_granted = await compliance_service.process_consent_response(phone, message)
            if consent_granted is True:
                await whatsapp_service.send_text(phone, "✅ Thank you for your consent. We'll process your data responsibly.")
            elif consent_granted is False:
                await whatsapp_service.send_text(phone, "❌ Consent declined. We won't process your personal data.")
        else:
            await whatsapp_service.send_text(phone, "For privacy requests, type: DELETE (remove data) or PRIVACY (view policy)")
    
    async def _get_or_create_contact(self, phone: str):
        """Get existing contact or create new one"""
        # Simplified - would use actual DB session
        # For now return a mock contact object
        class MockContact:
            def __init__(self, phone):
                self.phone = phone
                self.name = None
                self.created_at = datetime.utcnow()
        
        return MockContact(phone)
    
    async def _log_message(self, phone: str, content: str, message_id: str, is_bot: bool = False):
        """Log message to database"""
        # TODO: Implement actual database logging
        # For now, just print for debugging
        direction = "OUT" if is_bot else "IN"
        print(f"[{direction}] {phone}: {content[:50]}...")
    


orchestrator = MessageOrchestrator()