from fastapi import APIRouter, Request, HTTPException, Query
from app.core.config import settings
from app.services.orchestrator import orchestrator
import httpx
import logging

router = APIRouter()
logger = logging.getLogger("webhook")

# -------------------------------
# Webhook Verification for Meta
# -------------------------------
@router.get("/webhooks/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token")
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

# -------------------------------
# WhatsApp Incoming Messages
# -------------------------------
@router.post("/webhooks/whatsapp")
async def receive_whatsapp_message(request: Request):
    content_type = request.headers.get("content-type", "")

    # -------- CASE 1: Twilio (Form URL Encoded) --------
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        data = dict(form)
        from_number = data.get("From", "").replace("whatsapp:", "")
        body = data.get("Body", "")
        message_id = data.get("MessageSid", "twilio-msg")

        logger.info(f"[Twilio IN] {from_number}: {body}")

        if from_number and body:
            # Use Orchestrator to get response
            response_text = await orchestrator.process_message(from_number, body, message_id, channel="twilio")
            if response_text:
                await send_twilio_message(from_number, response_text)
        return {"status": "ok"}

    # -------- CASE 2: Meta Cloud API (JSON) --------
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid_json"}

    if payload.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if "messages" in value:
                for message in value["messages"]:
                    from_number = message["from"]
                    message_type = message["type"]
                    message_id = message["id"]

                    logger.info(f"[Meta IN] {from_number}: {message_type}")

                    if message_type == "text":
                        text_body = message["text"]["body"]
                        # Process and send via Meta (orchestrator handles it or returns it)
                        # To support the new pattern, we will make orchestrator return text
                        # and we send it here.
                        response_text = await orchestrator.process_message(from_number, text_body, message_id, channel="meta")
                        
                        # Only send if orchestrator didn't handle it internally (backward compat check)
                        # OR we assume orchestrator ONLY returns text now.
                        if response_text:
                            # Verify if metadata exists in value
                            phone_id = value.get("metadata", {}).get("phone_number_id", settings.WHATSAPP_PHONE_NUMBER_ID)
                            await send_meta_message(from_number, response_text, phone_id)

    return {"status": "ok"}

# -------------------------------
# Twilio Message Sender
# -------------------------------
async def send_twilio_message(to_number: str, body: str):
    from twilio.rest import Client
    # Ensure variables exist
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.error("Twilio credentials missing")
        return

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    sandbox_number = settings.TWILIO_WHATSAPP_SANDBOX_NUMBER or settings.TWILIO_PHONE_NUMBER

    try:
        message = client.messages.create(
            from_=f"whatsapp:{sandbox_number}",
            to=f"whatsapp:{to_number}",
            body=body
        )
        logger.info(f"[Twilio OUT] {to_number}: {body} (SID: {message.sid})")
    except Exception as e:
        logger.error(f"Twilio send failed: {e}")

# -------------------------------
# Meta Cloud API Message Sender
# -------------------------------
async def send_meta_message(to_number: str, body: str, phone_number_id: str):
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body}
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info(f"[Meta OUT] {to_number}: {body}")
            else:
                logger.error(f"Meta send failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Meta send exception: {e}")

@router.post("/webhooks/sms")
async def receive_sms(request: Request):
    """Handle SMS from Twilio"""
    return {"status": "ok"}

@router.post("/webhooks/ussd")
async def receive_ussd(request: Request):
    """Handle USSD"""
    return {"status": "ok"}
