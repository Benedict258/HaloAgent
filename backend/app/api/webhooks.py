from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
from typing import Optional
from app.core.config import settings
from app.db.supabase_client import supabase
from app.services.business import business_service
from app.services.contact import contact_service
from app.services.orchestrator import orchestrator
from app.services.payments import payment_service
from app.services.vision import vision_service
from app.services.whatsapp import whatsapp_service
from app.utils.media_cache import media_cache
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
        to_number = data.get("To", "").replace("whatsapp:", "")
        body = data.get("Body", "")
        message_id = data.get("MessageSid", "twilio-msg")
        num_media = int(data.get("NumMedia", 0))

        await _maybe_enrich_contact_profile(
            from_number=from_number,
            to_number=to_number,
            name=data.get("ProfileName") or data.get("WaIdName"),
            source="twilio",
        )

        # Check if it's a voice note
        if num_media > 0:
            media_content_type = data.get("MediaContentType0", "")
            if "audio" in media_content_type:
                media_url = data.get("MediaUrl0", "")
                logger.info(f"Processing Twilio voice note from {from_number}, type: {media_content_type}")
                
                from app.services.voice import voice_service
                transcribed_text = await voice_service.transcribe_audio(
                    media_url,
                    media_content_type,
                    source="twilio",
                    message_sid=message_id,
                )
                
                if transcribed_text:
                    response_text = await orchestrator.process_message(from_number, transcribed_text, message_id, to_number, channel="twilio")
                    if response_text:
                        await send_twilio_message(from_number, response_text)
                else:
                    await send_twilio_message(from_number, "Sorry, I couldn't understand the voice note. Can you type your message?")
                return JSONResponse(content={"status": "ok", "platform": "twilio"})
            elif "image" in media_content_type:
                media_url = data.get("MediaUrl0", "")
                logger.info(f"Processing Twilio image from {from_number}, type: {media_content_type}")
                image_result = await _handle_image_attachment(
                    from_number=from_number,
                    to_number=to_number,
                    media_url=media_url,
                    message_id=message_id,
                    body=body,
                    channel="twilio",
                    media_content_type=media_content_type,
                )
                if image_result and image_result.get("response_text"):
                    await send_twilio_message(from_number, image_result["response_text"])
                return JSONResponse(content={"status": "ok", "platform": "twilio"})
        
        if from_number and body:
            logger.info(f"Processing Twilio message from {from_number} to {to_number}: {body}")
            response_text = await orchestrator.process_message(from_number, body, message_id, to_number, channel="twilio")
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

            profile_map = {}
            for contact in value.get("contacts", []) or []:
                wa_id = contact.get("wa_id")
                profile_name = (contact.get("profile") or {}).get("name")
                if wa_id and profile_name:
                    profile_map[wa_id] = profile_name

            metadata = value.get("metadata", {})
            display_number = metadata.get("display_phone_number")
            resolved_business_number = _normalize_phone_number(display_number)

            if "messages" in value:
                for message in value["messages"]:
                    from_number = message.get("from")
                    message_type = message.get("type")
                    message_id = message.get("id")
                    profile_name = profile_map.get(from_number)

                    if message_type == "text":
                        text_body = message.get("text", {}).get("body", "")
                        phone_id = value.get("metadata", {}).get("phone_number_id", settings.WHATSAPP_PHONE_NUMBER_ID)
                        to_number = f"+{phone_id}" if not phone_id.startswith("+") else phone_id
                        await _maybe_enrich_contact_profile(
                            from_number=from_number,
                            to_number=resolved_business_number or to_number,
                            name=profile_name,
                            source="meta",
                        )
                        logger.info(f"Processing Meta message from {from_number} to {to_number}: {text_body}")
                        response_text = await orchestrator.process_message(from_number, text_body, message_id, to_number, channel="meta")
                        if response_text:
                            await send_meta_message(from_number, response_text, phone_id)
                    
                    elif message_type == "audio":
                        # Handle voice note
                        audio_id = message.get("audio", {}).get("id")
                        logger.info(f"Processing voice note from {from_number}: {audio_id}")
                        await _maybe_enrich_contact_profile(
                            from_number=from_number,
                            to_number=resolved_business_number,
                            name=profile_name,
                            source="meta",
                        )
                        
                        # Download and transcribe
                        from app.services.voice import voice_service
                        audio_url = f"https://graph.facebook.com/v18.0/{audio_id}"
                        transcribed_text = await voice_service.transcribe_audio(
                            audio_url,
                            source="meta",
                            bearer_token=settings.WHATSAPP_API_TOKEN,
                        )
                        
                        if transcribed_text:
                            phone_id = value.get("metadata", {}).get("phone_number_id", settings.WHATSAPP_PHONE_NUMBER_ID)
                            to_number = f"+{phone_id}" if not phone_id.startswith("+") else phone_id
                            response_text = await orchestrator.process_message(from_number, transcribed_text, message_id, to_number, channel="meta")
                            
                            if response_text:
                                await send_meta_message(from_number, response_text, phone_id)
                        else:
                            response_text = "Sorry, I couldn't understand the voice note. Can you type your message?"
                            phone_id = value.get("metadata", {}).get("phone_number_id", settings.WHATSAPP_PHONE_NUMBER_ID)
                            await send_meta_message(from_number, response_text, phone_id)
                    elif message_type == "image":
                        phone_id = value.get("metadata", {}).get("phone_number_id", settings.WHATSAPP_PHONE_NUMBER_ID)
                        image_id = message.get("image", {}).get("id")
                        caption = message.get("image", {}).get("caption") or message.get("text", {}).get("body", "")
                        if image_id:
                            await _maybe_enrich_contact_profile(
                                from_number=from_number,
                                to_number=resolved_business_number or phone_id,
                                name=profile_name,
                                source="meta",
                            )
                            media_url = f"https://graph.facebook.com/v18.0/{image_id}"
                            logger.info(f"Processing Meta image from {from_number}: {image_id}")
                            image_result = await _handle_image_attachment(
                                from_number=from_number,
                                to_number=None,
                                media_url=media_url,
                                message_id=message_id,
                                body=caption,
                                channel="meta",
                                phone_id=phone_id,
                                media_content_type=message.get("image", {}).get("mime_type"),
                            )
                            if image_result and image_result.get("response_text"):
                                await send_meta_message(from_number, image_result["response_text"], phone_id)

    return JSONResponse(content={"status": "ok", "platform": "meta"})

# -------------------------------
# Media + Vision helpers
# -------------------------------

async def _handle_image_attachment(
    *,
    from_number: str,
    to_number: Optional[str],
    media_url: str,
    message_id: str,
    body: Optional[str],
    channel: str,
    phone_id: Optional[str] = None,
    media_content_type: Optional[str] = None,
) -> Optional[dict]:
    context = await _resolve_business_context(from_number, to_number=to_number, phone_id=phone_id)
    if not context:
        logger.warning("Unable to resolve business context for image from %s", from_number)
        return None

    business = context["business"] or {}
    business_id = context["business_id"]
    contact = context["contact"]
    if not contact or not contact.get("id"):
        logger.warning("No contact record for %s", from_number)
        return None

    contact_id = contact["id"]
    pending_order = _fetch_latest_pending_order(contact_id)
    resolved_to_number = to_number
    if not resolved_to_number and phone_id:
        resolved_to_number = phone_id if phone_id.startswith("+") else f"+{phone_id}"

    agent_message = (body or "").strip()
    cached_media = await media_cache.cache_remote_media(
        remote_url=media_url,
        source="meta" if channel == "meta" else "twilio",
        content_type=media_content_type,
        bearer_token=settings.WHATSAPP_API_TOKEN if channel == "meta" else None,
    )
    persisted_media_url = cached_media.get("public_url") if cached_media else media_url
    if pending_order:
        expected_amount = pending_order.get("total_amount")
        expected_reference = pending_order.get("order_number") or pending_order.get("payment_reference")
        receipt_analysis = await vision_service.analyze_receipt(
            business_id=business_id,
            contact_id=contact_id,
            order_id=pending_order["id"],
            media_url=persisted_media_url,
            expected_amount=expected_amount,
            expected_reference=expected_reference,
            text_hint=agent_message or body,
        )
        update = await payment_service.mark_payment_pending_review(
            business_id=business_id,
            contact_phone=from_number,
            order_id=pending_order["id"],
            receipt_url=persisted_media_url,
            note=f"Receipt uploaded via {channel}",
            receipt_analysis=receipt_analysis,
        )
        try:
            supabase.table("orders").update({
                "payment_receipt_analysis": receipt_analysis,
                "payment_receipt_uploaded_at": datetime.utcnow().isoformat(),
            }).eq("id", pending_order["id"]).execute()
        except Exception as update_err:
            logger.warning("Failed to persist receipt analysis for order %s: %s", pending_order["id"], update_err)
        if not agent_message:
            agent_message = "Shared my payment receipt."
        reference = update.get("payment_reference") if update else None
        if reference:
            agent_message += f"\n[receipt_reference {reference}]"
    else:
        inventory = business.get("inventory") or []
        product_analysis = await vision_service.analyze_product_photo(
            business_id=business_id,
            contact_id=contact_id,
            media_url=persisted_media_url,
            inventory=inventory,
        )
        if not agent_message:
            agent_message = "Here is a product photo for what I'm considering."
        top_match = product_analysis.get("top_match")
        if top_match and top_match.get("name"):
            agent_message += (
                f"\n[vision_product_match name={top_match['name']} confidence={top_match.get('confidence')}]"
            )

    if not resolved_to_number:
        logger.warning("Cannot route agent reply without destination number for %s", from_number)
        return None

    response_text = await orchestrator.process_message(
        from_number,
        agent_message,
        message_id,
        resolved_to_number,
        channel="whatsapp" if channel == "meta" else channel,
    )
    return {"response_text": response_text}


async def _resolve_business_context(
    from_number: str,
    *,
    to_number: Optional[str],
    phone_id: Optional[str] = None,
) -> Optional[dict]:
    business = None
    business_id = None
    if to_number:
        business = await business_service.get_business_by_whatsapp(to_number)
        if business:
            business_id = business.get("business_id")

    if not business_id:
        contact_lookup = (
            supabase
            .table("contacts")
            .select("id, business_id")
            .eq("phone_number", from_number)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if contact_lookup.data:
            contact_row = contact_lookup.data[0]
            business_id = contact_row.get("business_id")
            if business_id:
                business = await business_service.get_business_by_id(business_id)
            contact = contact_row
        else:
            contact = None
    else:
        contact = None

    if not business_id and phone_id:
        # Fallback to default mapping using configured phone id
        business = await business_service.get_business_by_whatsapp(phone_id)
        if business:
            business_id = business.get("business_id")

    if not business_id:
        return None

    if not contact:
        contact = await contact_service.get_or_create_contact(from_number, business_id)
    elif not contact.get("id"):
        contact = await contact_service.get_or_create_contact(from_number, business_id)

    return {
        "business": business,
        "business_id": business_id,
        "contact": contact,
    }


def _fetch_latest_pending_order(contact_id: int) -> Optional[dict]:
    try:
        result = (
            supabase
            .table("orders")
            .select("id, order_number, status, payment_reference, total_amount")
            .eq("contact_id", contact_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        allowed = {"pending_payment", "payment_pending_review", "awaiting_confirmation"}
        for row in result.data or []:
            if row.get("status") in allowed:
                return row
    except Exception as exc:
        logger.error("Failed to fetch pending order: %s", exc)
    return None


def _normalize_phone_number(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    return value if value.startswith("+") else f"+{value}"


async def _maybe_enrich_contact_profile(*, from_number: str, to_number: Optional[str], name: Optional[str], source: str) -> None:
    if not from_number or not name:
        return
    normalized_name = name.strip()
    if not normalized_name:
        return

    normalized_to = _normalize_phone_number(to_number)
    business = None
    if normalized_to:
        business = await business_service.get_business_by_whatsapp(normalized_to)

    if not business:
        return

    business_id = business.get("business_id")
    if not business_id:
        return

    await contact_service.ensure_contact_profile(
        phone=from_number,
        business_id=business_id,
        name=normalized_name,
    )

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
