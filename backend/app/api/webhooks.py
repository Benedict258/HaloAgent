from fastapi import APIRouter, Request, HTTPException, Query
from app.core.config import settings
from app.services.orchestrator import orchestrator

router = APIRouter()

@router.get("/webhooks/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token")
):
    # Check against global token (fallback) or user-specific tokens
    if hub_mode == "subscribe":
        if hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            return int(hub_challenge)
        
        # TODO: Check user-specific verify tokens from database
        # from app.models.user import User
        # user = db.query(User).filter(User.whatsapp_webhook_verify_token == hub_verify_token).first()
        # if user:
        #     return int(hub_challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhooks/whatsapp")
async def receive_whatsapp_message(request: Request):
    content_type = request.headers.get("content-type", "")
    
    # CASE 1: Twilio (Form URL Encoded)
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        data = dict(form)
        # Twilio maps fields differently
        from_number = data.get("From", "").replace("whatsapp:", "")
        body = data.get("Body", "")
        message_id = data.get("MessageSid", "twilio-msg")
        
        if from_number and body:
            await orchestrator.process_message(from_number, body, message_id)
        return {"status": "ok"}
        
    # CASE 2: Meta Cloud API (JSON)
    try:
        body = await request.json()
    except Exception:
         return {"status": "ignored", "reason": "invalid_json"}

    if body.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}
    
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            
            if "messages" in value:
                for message in value["messages"]:
                    from_number = message["from"]
                    message_type = message["type"]
                    message_id = message["id"]
                    
                    if message_type == "text":
                        text_body = message["text"]["body"]
                        await orchestrator.process_message(
                            from_number, text_body, message_id
                        )
    
    return {"status": "ok"}

@router.post("/webhooks/sms")
async def receive_sms(request: Request):
    """Handle SMS webhooks from Twilio"""
    # TODO: Implement SMS processing
    return {"status": "ok"}

@router.post("/webhooks/ussd")
async def receive_ussd(request: Request):
    """Handle USSD session callbacks"""
    # TODO: Implement USSD processing
    return {"status": "ok"}
