from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse
import logging
from app.core.config import settings
from app.services.orchestrator import orchestrator
from app.services.whatsapp import whatsapp_service
# Note: We need a way to send back to Twilio. The previously implemented `send_twilio_message` is good.
# I will integrate it here or assume Orchestrator handles it if I reverted?
# Wait, my previous step made Orchestrator return the text.
# The user's NEW code snippet assumes:
# "await orchestrator.process_message(from_number, body, message_id)"
# And checking the User Request: "No interference with your existing orchestrator logic — your existing process_message is reused."
# This implies the user might NOT know I refactored it to return text.
# If I use this code, Orchestrator returns text, but this code DOES NOT DO ANYTHING with the return value.
# It just returns JSONResponse("ok").
# THIS IS A PROBLEM. No reply will be sent.
# I must ensure replies are sent.
# Option A: Re-add sending logic to Orchestrator (revert refactor).
# Option B: usage the "response_text" pattern in this new webhook too.
# The user's prompt *also* said: "Respond properly so WhatsApp knows your webhook received the message" (which is the JSONResponse).
# But for the USER to get a reply, we need to send it.
# The user's previous prompt (Step 540) included sending logic in the webhook.
# This new prompt (Step 563) REMOVED the sending logic from the webhook example code!
# "await orchestrator.process_message(from_number, body, message_id)" -> and that's it.
# This implies the User expects Orchestrator to send it.
# BUT I just removed sending from Orchestrator.
# I MUST PUT SENDING BACK INTO ORCHESTRATOR or Add it here effectively.
# Given "No interference with your existing orchestrator logic", the user probably assumes standard orchestrator behavior (which was sending).
# So I should PROBABLY REVERT the Orchestrator change or Handle sending here.
# I will saferly Handle sending HERE by checking the return value (since I know I changed it) and sending it.
# OR, to be strictly following "No interference", I should modify Orchestrator to send again? 
# No, "process_message" is the boundary.
# I will modify the Webhook code to capture the return and SEND.
# I will re-include the send_twilio_message and send_meta_message functions from previous step to be safe.
# Or, simpler: I'll modify Orchestrator to SEND if a flag is passed, or just send always.
# Easiest path: Update Orchestrator to SEND directly again (hybrid approach).
# But wait, sending to Twilio requires Twilio Client, sending to Meta requires HTTPX. Orchestrator only has `whatsapp_service` (Meta).
# So Orchestrator cannot send to Twilio easily without adding TwilioService.
# So the Webhook MUST handle responding for Twilio.
# So I will keep Orchestrator returning text.
# And I will update this Webhook code to use that text to send.
# "await orchestrator.process_message" returns the text. I will capture it.
# And I need the `send_twilio_message` and `send_meta_message` logic.
# I will combine the user's logging structure with the previous sending logic.

router = APIRouter()

# Set up logging for debugging
logger = logging.getLogger("webhook_logger")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ---------------------------
# Meta Webhook Verification
# ---------------------------
@router.get("/webhooks/whatsapp")
async def verify_meta_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token")
):
    """
    Responds to Meta webhook verification request.
    """
    logger.info(f"Meta webhook verification attempt: mode={hub_mode}, token={hub_verify_token}")
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        logger.info("Meta webhook verified successfully")
        return int(hub_challenge)
    logger.warning("Meta webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


# ---------------------------
# Main Webhook Receiver
# ---------------------------
@router.post("/webhooks/whatsapp")
async def receive_whatsapp_message(request: Request):
    """
    Receives incoming messages from Meta or Twilio.
    Logs everything for debugging.
    """
    # Log request headers
    # logger.info(f"Incoming request headers: {dict(request.headers)}") # Verbose

    content_type = request.headers.get("content-type", "")

    # ---------------------------
    # CASE 1: Twilio (Form URL Encoded)
    # ---------------------------
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        data = dict(form)
        logger.info(f"Twilio payload received for validation")

        from_number = data.get("From", "").replace("whatsapp:", "")
        body = data.get("Body", "")
        message_id = data.get("MessageSid", "twilio-msg")

        if from_number and body:
            logger.info(f"Processing Twilio message from {from_number}: {body}")
            response_text = await orchestrator.process_message(from_number, body, message_id, channel="twilio")
            if response_text:
                await send_twilio_message(from_number, response_text)

        return JSONResponse(content={"status": "ok", "platform": "twilio"})

    # ---------------------------
    # CASE 2: Meta Cloud API (JSON)
    # ---------------------------
    try:
        body = await request.json()
        logger.info(f"Meta payload received")
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        return JSONResponse(content={"status": "ignored", "reason": "invalid_json"}, status_code=400)

    if body.get("object") != "whatsapp_business_account":
        logger.warning("Ignored non-whatsapp_business_account payload")
        return JSONResponse(content={"status": "ignored"})

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            if "messages" in value:
                for message in value["messages"]:
                    from_number = message.get("from")
                    message_type = message.get("type")
                    message_id = message.get("id")

                    if message_type == "text":
                        text_body = message.get("text", {}).get("body", "")
                        logger.info(f"Processing Meta message from {from_number}: {text_body}")
                        response_text = await orchestrator.process_message(from_number, text_body, message_id, channel="meta")
                        
                        if response_text:
                             phone_id = value.get("metadata", {}).get("phone_number_id", settings.WHATSAPP_PHONE_NUMBER_ID)
                             await send_meta_message(from_number, response_text, phone_id)

    return JSONResponse(content={"status": "ok", "platform": "meta"})

# -------------------------------
# Helper Senders (Restored for completeness)
# -------------------------------
async def send_twilio_message(to_number: str, body: str):
    from twilio.rest import Client
    if not settings.TWILIO_ACCOUNT_SID: return
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        sandbox = settings.TWILIO_WHATSAPP_SANDBOX_NUMBER or settings.TWILIO_PHONE_NUMBER
        client.messages.create(
            from_=f"whatsapp:{sandbox}",
            to=f"whatsapp:{to_number}",
            body=body
        )
        logger.info(f"Values sent to Twilio: {to_number}")
    except Exception as e:
        logger.error(f"Twilio send error: {e}")

async def send_meta_message(to_number: str, body: str, phone_id: str):
    import httpx
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": body}}
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)

@router.post("/webhooks/sms")
async def receive_sms(request: Request):
    return {"status": "ok"}

@router.post("/webhooks/ussd")
async def receive_ussd(request: Request):
    return {"status": "ok"}
