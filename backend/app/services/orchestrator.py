from app.services.whatsapp import whatsapp_service
from app.services.business import business_service
from app.services.contact import contact_service
from app.services.state import state_service
from app.db.supabase_client import supabase
from datetime import datetime
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class MessageOrchestrator:
    async def process_message(
        self,
        phone: str,
        message: str,
        message_id: str,
        to_number: Optional[str],
        channel: str = "whatsapp",
        *,
        business_id: Optional[str] = None,
        include_metadata: bool = False,
    ) -> Any:
        """Route an inbound message through the agent and optionally return metadata."""

        result = await self._process_message(
            phone=phone,
            message=message,
            message_id=message_id,
            to_number=to_number,
            channel=channel,
            business_id_override=business_id,
        )

        if include_metadata:
            return result
        return result.get("response_text")

    async def _process_message(
        self,
        *,
        phone: str,
        message: str,
        message_id: str,
        to_number: Optional[str],
        channel: str,
        business_id_override: Optional[str],
    ) -> Dict[str, Any]:
        # 1. Resolve business
        business = None
        resolved_business_id = business_id_override
        if resolved_business_id:
            business = await business_service.get_business_by_id(resolved_business_id)
        elif to_number:
            business = await business_service.get_business_by_whatsapp(to_number)
            if business:
                resolved_business_id = business.get("business_id")

        if not business or not resolved_business_id:
            logger.error("No business context for channel %s (to=%s, override=%s)", channel, to_number, business_id_override)
            fallback = "Service unavailable. Please contact support."
            return {
                "response_text": fallback,
                "contact_id": None,
                "business": None,
                "inbound_log": None,
                "outbound_log": None,
            }

        # 2. Get or create contact (phone = contact ID)
        contact = await contact_service.get_or_create_contact(phone, resolved_business_id)
        if not contact:
            return {
                "response_text": "Unable to process your message. Please try again.",
                "contact_id": None,
                "business": business,
                "inbound_log": None,
                "outbound_log": None,
            }

        contact_id = contact["id"]
        contact_name = contact.get("name")
        opt_in = contact.get("opt_in", False)

        # Log incoming
        inbound_log = await self._log_message(phone, message, message_id, contact_id, direction="IN", channel=channel)

        # 3. Build context for agent
        context = (
            f"Phone: {phone}, Business ID: {resolved_business_id}, Business Name: {business['business_name']}, "
            f"Opt-in: {opt_in}, Channel: {channel}"
        )
        if contact_name:
            context += f", Name: {contact_name}"

        inventory = business.get("inventory", [])
        if inventory:
            context += f", Products: {json.dumps(inventory)}"

        context += f"\n\nIMPORTANT: When calling tools, use business_id='{resolved_business_id}'"

        # 4. Run agent (handles tool calls internally)
        try:
            from app.services.agent.core import agent

            response_text = await agent.run(
                message,
                phone,
                context,
                business_id=resolved_business_id,
                channel=channel,
            )

            response_text = self._sanitize_response(response_text)

        except Exception as e:
            logger.error(f"Agent error: {e}")
            response_text = "I'm having a little trouble right now. Give me a moment and try again!"

        await state_service.update_state(phone, {"last_message_ts": datetime.utcnow().isoformat()})

        outbound_log = await self._log_message(
            phone,
            response_text,
            f"reply-{message_id}",
            contact_id,
            direction="OUT",
            is_bot=True,
            channel=channel,
        )

        return {
            "response_text": response_text,
            "contact_id": contact_id,
            "business": business,
            "inbound_log": inbound_log,
            "outbound_log": outbound_log,
        }
    
    def _sanitize_response(self, text: str) -> str:
        """Return clean conversational text (strip JSON/tool noise)."""
        if not text:
            return "Got it! Let me help you with that."

        cleaned = text.strip()

        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned.strip("`").strip()

        if cleaned.startswith("{") or cleaned.startswith("["):
            try:
                from app.services.agent.core import agent as _agent_singleton
                extracted = _agent_singleton._extract_final_message(cleaned)
                if extracted:
                    cleaned = extracted
            except Exception:
                pass

        bad_phrases = [
            "intent_classifier",
            "tool_call",
            "parameters",
            "action",
            "final_answer",
            "Let me process",
            "Processing your request"
        ]

        lowered = cleaned.lower()
        for phrase in bad_phrases:
            if phrase in lowered:
                return "Got it! Let me help you with that."

        return cleaned

    async def _log_message(
        self,
        phone: str,
        content: str,
        message_id: str,
        contact_id: Optional[int] = None,
        direction: str = "IN",
        is_bot: bool = False,
        channel: str = "meta",
    ) -> Optional[Dict[str, Any]]:
        """Log message to database and return the stored record."""

        if not contact_id:
            return None

        try:
            log_data = {
                "contact_id": contact_id,
                "message_id": message_id,
                "direction": direction,
                "message_type": "text",
                "channel": channel,
                "content": content,
                "status": "sent" if is_bot else "received",
                "created_at": datetime.utcnow().isoformat(),
            }
            result = supabase.table("message_logs").insert(log_data).execute()
            record = result.data[0] if result.data else None
            print(f"[{direction}] {phone}: {content[:50]}...")
            return record
        except Exception as e:
            logger.error(f"Failed to log message: {e}")
            return None

orchestrator = MessageOrchestrator()