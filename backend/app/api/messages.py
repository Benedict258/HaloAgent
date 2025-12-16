from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from app.db.supabase_client import supabase
from datetime import datetime
import logging
from pathlib import Path
from app.services.payments import payment_service
from app.services.vision import vision_service

router = APIRouter()
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[3]
RECEIPT_UPLOAD_DIR = BASE_DIR / "uploads" / "receipts"
RECEIPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
        contact_name = None
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
            .select("id, name")
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
            contact_name = contact.data[0].get("name")

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
        if contact_name:
            greeting = (
                f"Hi {contact_name}! You're chatting with {business_label}. "
                "Happy to help with anything you need—just let me know what you're craving."
            )
        else:
            greeting = (
                f"Hey there! It's {business_label}. I'm here if you need recommendations or want to place an order—"
                "what are you in the mood for today?"
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

@router.post("/messages/upload-receipt")
async def upload_receipt_via_chat(
    business_id: str = Form(...),
    contact_phone: str = Form(...),
    channel: str = Form("web"),
    receipt: UploadFile = File(...)
):
    """Allow end-users on web chat to upload payment receipts."""
    try:
        allowed_types = {"image/jpeg", "image/png", "application/pdf"}
        if receipt.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        suffix = Path(receipt.filename or "").suffix.lower()
        if not suffix:
            suffix = ".pdf" if receipt.content_type == "application/pdf" else ".jpg"
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        filename = f"receipt-{contact_phone}-{timestamp}{suffix}"
        file_path = RECEIPT_UPLOAD_DIR / filename
        file_bytes = await receipt.read()
        file_path.write_bytes(file_bytes)
        public_url = f"/uploads/receipts/{filename}"

        contact_query = (
            supabase
            .table("contacts")
            .select("id, name")
            .eq("phone_number", contact_phone)
            .eq("business_id", business_id)
            .single()
            .execute()
        )
        if contact_query.data:
            contact_id = contact_query.data["id"]
            contact_name = contact_query.data.get("name")
        else:
            new_contact = (
                supabase
                .table("contacts")
                .insert({
                    "phone_number": contact_phone,
                    "business_id": business_id,
                    "opt_in": True
                })
                .execute()
            )
            if not new_contact.data:
                raise HTTPException(status_code=500, detail="Unable to create contact")
            contact_id = new_contact.data[0]["id"]
            contact_name = None

        payment_update = await payment_service.mark_payment_pending_review(
            business_id=business_id,
            contact_phone=contact_phone,
            receipt_url=public_url,
            note=f"Receipt uploaded via {channel}",
        )

        if not payment_update:
            raise HTTPException(status_code=404, detail="No pending order to attach receipt")

        order_id = payment_update["order_id"]
        receipt_analysis = await vision_service.analyze_receipt(
            business_id=business_id,
            contact_id=contact_id,
            order_id=order_id,
            media_url=public_url,
        )
        supabase.table("orders").update({
            "payment_receipt_analysis": receipt_analysis,
            "payment_receipt_uploaded_at": datetime.utcnow().isoformat()
        }).eq("id", order_id).execute()

        inbound_log = (
            supabase
            .table("message_logs")
            .insert({
                "contact_id": contact_id,
                "direction": "IN",
                "message_type": channel,
                "content": "[Attachment] Payment receipt uploaded",
                "status": "delivered",
                "created_at": datetime.utcnow().isoformat()
            })
            .execute()
        )

        from app.services.agent.core import agent

        context = f"Phone: {contact_phone}, Business ID: {business_id}, Channel: {channel}"
        agent_message = "I just uploaded my payment receipt through the portal."
        reference = payment_update.get("payment_reference")
        if reference:
            agent_message += f" Reference: {reference}."
        agent_message += " Please confirm when you can."

        response = await agent.run(
            agent_message,
            contact_phone,
            context,
            business_id=business_id,
            channel=channel,
        )

        outbound_log = None
        if response:
            outbound_log = (
                supabase
                .table("message_logs")
                .insert({
                    "contact_id": contact_id,
                    "direction": "OUT",
                    "message_type": channel,
                    "content": response,
                    "status": "sent",
                    "created_at": datetime.utcnow().isoformat()
                })
                .execute()
            )

        return {
            "status": "success",
            "receipt_url": public_url,
            "message": response,
            "message_logs": {
                "inbound": (inbound_log.data[0] if inbound_log.data else None),
                "outbound": (outbound_log.data[0] if outbound_log and outbound_log.data else None),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Receipt upload via chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to upload receipt right now")

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
