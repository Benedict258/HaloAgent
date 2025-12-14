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
        Phase 2 & 3: Structured Intent Routing & Order Flow.
        Returns the text response to be sent back.
        """
        
        # 1. State Retrieval
        state = await state_service.get_state(phone)
        contact_id = state.get("contact_id")
        current_stage = state.get("current_stage", "NONE")
        context_data = state.get("context_data", {})
        
        # Log Incoming
        await self._log_message(phone, message, message_id, contact_id, direction="IN", channel=channel)
        
        # 2. Intent Classification
        # If we are in the middle of a flow (INITIATED/CONFIRM), we might bias intent or skip it?
        # But user might say "Cancel" or "Help".
        # So classify always, but context matters.
        intent_res = await intent_service.identify_intent(message)
        intent = intent_res["intent"]
        confidence = intent_res["confidence"]
        
        logger.info(f"Intent: {intent} ({confidence}) for {phone} [Stage: {current_stage}]")
        
        # Track Intent
        if contact_id:
             await analytics_service.track_interaction(contact_id, "intent_detected", {"intent": intent, "confidence": confidence})

        response_text = ""
        next_stage = current_stage # Default stay same
        updates = {}

        # 3. Routing Logic
        
        # CRITICAL: If stage is INITIATED or CONFIRM_PENDING, we treat input as part of flow UNLESS strong 'CANCEL'/'HELP' intent?
        # For MVP, if Intent is HELP, break flow. If ORDER/UNKNOWN/STATUS, continue flow.
        
        if intent == "HELP":
            response_text = "I can help you place an order, check status, or take feedback. \n- To order, say 'I want to buy...'\n- To check status, say 'Order status'."
            next_stage = "NONE" # Reset
            
        elif intent == "FEEDBACK":
            response_text = "Thank you for your feedback. We have logged it for the team."
            # TODO: Save feedback to DB
            next_stage = "NONE"
            
        elif intent == "STATUS":
            # Lookup last order
            response_text = "You have no pending orders. (MVP Stub)" # TODO: Actual lookup
            next_stage = "NONE"
            
        elif intent == "ORDER" or current_stage in ["INITIATED", "CONFIRM_PENDING"]:
            # --- ORDER SUB-FLOW ---
            
            # Start New Order
            if current_stage == "NONE" or intent == "ORDER":
                response_text = "What would you like to order today? (e.g. '2 Jollof Rice')"
                next_stage = "INITIATED"
                updates["context_data"] = {} # Clear context
                
            # Extract Details & Validate
            elif current_stage == "INITIATED":
                # AI Extraction
                extracted = await self._extract_order_details(message)
                items = extracted.get("items", [])
                
                if items:
                    # Summary
                    item_summary = ", ".join([f"{i['qty']}x {i['name']}" for i in items])
                    response_text = f"I have: {item_summary}. \nDo you want to confirm this order? Reply YES or NO."
                    next_stage = "CONFIRM_PENDING"
                    updates["context_data"] = {"pending_items": items}
                else:
                    response_text = "I didn't catch that. Please list the items and quantity (e.g. '1 Fried Rice')."
                    next_stage = "INITIATED" # Retry
                    
            # Confirm
            elif current_stage == "CONFIRM_PENDING":
                text_lower = message.lower()
                if "yes" in text_lower:
                    # Save Order
                    pending_items = context_data.get("pending_items", [])
                    order_id = await self._create_order(contact_id, pending_items)
                    response_text = f"✅ Order #{order_id} Confirmed! We will notify you when it's ready."
                    next_stage = "NONE" # Done
                    updates["last_intent"] = "ORDER_COMPLETED"
                elif "no" in text_lower:
                    response_text = "Okay, cancelled. What would you like to order instead?"
                    next_stage = "INITIATED"
                    updates["context_data"] = {}
                else:
                    response_text = "Please reply YES to confirm or NO to cancel."
                    next_stage = "CONFIRM_PENDING" # Stay
                    
        else:
            # Fallback / UNKNOWN
            response_text = "I didn't understand. You can say 'Order food' or 'Help'."
            next_stage = "NONE"

        # 4. State Update
        updates["current_stage"] = next_stage
        updates["last_intent"] = intent
        await state_service.update_state(phone, updates)
        
        # Log Outgoing
        await self._log_message(phone, response_text, f"reply-{message_id}", contact_id, direction="OUT", is_bot=True, channel=channel)
        
        return response_text

    async def _extract_order_details(self, text: str) -> dict:
        """Use AI to extract structured items"""
        prompt = f"""
        Extract order items from: "{text}".
        Return JSON only: {{ "items": [ {{ "name": "item", "qty": 1 }} ] }}
        If no items found, return {{ "items": [] }}
        """
        try:
            res = await meta_ai_service.chat_completion(prompt)
            if "{" in res:
                 json_str = res[res.find("{"):res.rfind("}")+1]
                 return json.loads(json_str)
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
        return {"items": []}

    async def _create_order(self, contact_id: int, items: list) -> str:
        """Save order to DB (Mock or Real)"""
        # MVP: Create Mock ID or usage supabase if orders table ready
        # We usage timestamp as ID
        order_id = f"ORD-{int(datetime.utcnow().timestamp())}"
        # TODO: Insert into 'orders' table
        return order_id

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