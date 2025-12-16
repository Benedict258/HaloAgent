from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.supabase_client import supabase
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SendMessage(BaseModel):
    business_id: str
    contact_phone: str
    channel: str = "web"  # web, whatsapp, sms
    body: str
    attachments: list = []

@router.post("/messages/send")
async def send_message(data: SendMessage):
    """Send message from web UI or programmatically"""
    try:
        business_name = None
        business = (
            supabase
            .table("businesses")
            .select("business_name")
            .eq("business_id", data.business_id)
            .limit(1)
            .execute()
        )
        if business.data:
            business_name = business.data[0].get("business_name")

        # Get or create contact
        contact = (
            supabase
            .table("contacts")
            .select("id")
            .eq("phone_number", data.contact_phone)
            .eq("business_id", data.business_id)
            .execute()
        )
        created_new_contact = False

        if not contact.data:
            # Create contact
            new_contact = (
                supabase
                .table("contacts")
                .insert({
                    "phone_number": data.contact_phone,
                    "business_id": data.business_id,
                    "opt_in": True
                })
                .execute()
            )
            contact_id = new_contact.data[0]["id"]
            created_new_contact = True
        else:
            contact_id = contact.data[0]["id"]

        # Log message
        message_log = {
            "contact_id": contact_id,
            "direction": "IN",
            "message_type": data.channel,
            "content": data.body,
            "status": "delivered"
        }
        inbound_record = (
            supabase
            .table("message_logs")
            .insert(message_log)
            .execute()
        )
        inbound_message = inbound_record.data[0] if inbound_record.data else None
        
        # Process through AI agent directly (bypass orchestrator for web)
        from app.services.agent.core import agent
        
        # Build context
        context = f"Phone: {data.contact_phone}, Business ID: {data.business_id}, Channel: {data.channel}"
        
        try:
            response = await agent.run(
                data.body,
                data.contact_phone,
                context,
                business_id=data.business_id,
                channel=data.channel,
            )
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            response = "I'm having trouble processing that. Please try again!"
        
        business_label = business_name or "our business"
        greeting = (
            "Hello! Welcome to the business. How can I help you today? 🎉\n"
            f"Welcome to {business_label}"
        )

        if created_new_contact:
            response = f"{greeting}\n\n{response}" if response else greeting
        elif not response:
            response = greeting

        # Log response
        outbound_message = None
        if response:
            response_log = {
                "contact_id": contact_id,
                "direction": "OUT",
                "message_type": data.channel,
                "content": response,
                "status": "sent"
            }
            outbound_record = (
                supabase
                .table("message_logs")
                .insert(response_log)
                .execute()
            )
            outbound_message = outbound_record.data[0] if outbound_record.data else None
        
        return {
            "status": "sent",
            "response": response,
            "contact_id": contact_id,
            "message_logs": {
                "inbound": inbound_message,
                "outbound": outbound_message
            }
        }
    
    except Exception as e:
        logger.error(f"Send message error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/messages/{contact_phone}")
async def get_messages(contact_phone: str, business_id: str = "sweetcrumbs_001", limit: int = 50):
    """Get chat history for a contact"""
    try:
        # Get contact
        contact = (
            supabase
            .table("contacts")
            .select("id")
            .eq("phone_number", contact_phone)
            .eq("business_id", business_id)
            .execute()
        )
        
        if not contact.data:
            return []
        
        contact_id = contact.data[0]["id"]
        
        # Get messages
        result = (
            supabase
            .table("message_logs")
            .select("*")
            .eq("contact_id", contact_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        
        return result.data or []
    
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        return []
