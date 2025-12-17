import json
import logging
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from app.services.meta_ai import meta_ai_service
from app.services.agent.tools import agent_tools
from app.services.agent.prompts import agent_prompts

logger = logging.getLogger(__name__)

class ConversationState:
    def __init__(self):
        self.pending_order = {
            "product_name": None,
            "price": None,
            "quantity": 1,
            "fulfillment_type": None,
            "delivery_address": None
        }
        self.order_intent_confirmed = False
        self.last_intent = None
        self.clarification_count = 0
        self.last_tool_name: Optional[str] = None
        self.last_tool_called_at: Optional[datetime] = None
        self.tool_cooldowns: Dict[str, datetime] = {}
        self.last_menu_shared_at: Optional[datetime] = None
        self.menu_summary: Optional[List[Dict[str, Any]]] = None
        self.channel: str = "whatsapp"
        self.business_id: Optional[str] = None
        self.business_name: str = "the business"
        self.profile = {
            "name": None,
            "loyalty_points": 0,
            "order_count": 0,
            "language": "en",
            "favorite_items": [],
            "last_order": None,
            "preferred_fulfillment": None,
            "last_delivery_address": None,
        }
        self.order_history: List[Dict[str, Any]] = []
        self.contact_id: Optional[int] = None
        self.last_profile_refresh: Optional[datetime] = None
        self.brand_voice: Optional[str] = None
        self.brand_description: Optional[str] = None
        self.brand_links: Dict[str, Any] = {}
        self.integration_channels: Dict[str, Any] = {}
        self.last_normalized_message: Optional[str] = None
        self.last_escalation_signature: Optional[str] = None
        self.pickup_address: Optional[str] = None
        self.pickup_instructions: Optional[str] = None
        self.settlement_account: Dict[str, Any] = {}

    def reset_pending_order(self):
        self.pending_order = {
            "product_name": None,
            "price": None,
            "quantity": 1,
            "fulfillment_type": None,
            "delivery_address": None
        }
        self.order_intent_confirmed = False

    def mark_order_intent(self):
        self.order_intent_confirmed = True

    def has_order_intent(self) -> bool:
        return bool(self.order_intent_confirmed)

    def update_channel(self, channel: str):
        self.channel = channel or self.channel

    def update_business(self, business_id: Optional[str], business_name: Optional[str]):
        if business_id:
            self.business_id = business_id
        if business_name:
            self.business_name = business_name

    def update_brand_profile(self, business_data: Optional[Dict[str, Any]]):
        if not business_data:
            return
        self.brand_voice = business_data.get("brand_voice") or business_data.get("settings", {}).get("tone") or self.brand_voice
        self.brand_description = business_data.get("description") or self.brand_description
        self.brand_links = business_data.get("settings") or self.brand_links
        integration_prefs = business_data.get("integration_preferences") or {}
        channels = integration_prefs.get("channels") if isinstance(integration_prefs, dict) else {}
        self.integration_channels = channels or self.integration_channels
        self.pickup_address = business_data.get("pickup_address") or self.pickup_address
        self.pickup_instructions = business_data.get("pickup_instructions") or self.pickup_instructions

        settlement_data = business_data.get("settlement_account") or business_data.get("payment_instructions")
        if isinstance(settlement_data, str):
            try:
                settlement_data = json.loads(settlement_data)
            except Exception:
                settlement_data = None
        if isinstance(settlement_data, dict):
            self.settlement_account = settlement_data

    def set_contact(self, contact_id: Optional[int]):
        if contact_id:
            self.contact_id = contact_id

    def remember_customer_message(self, normalized_text: Optional[str]):
        if normalized_text:
            self.last_normalized_message = normalized_text

    def extract_from_history(self, history: str, latest_message: Optional[str], inventory: List[Dict[str, Any]]):
        """Extract order cues from conversation history and latest message."""

        def _update_from_text(
            text: Optional[str],
            original_text: Optional[str],
            allow_override: bool,
            allow_address_lookup: bool,
        ):
            if not text:
                return
            for product in inventory or []:
                name = (product.get("name") or "").lower()
                if not name:
                    continue
                if name in text:
                    if allow_override or not self.pending_order["product_name"]:
                        self.pending_order["product_name"] = product.get("name")
                        self.pending_order["price"] = self._normalize_price(product.get("price"))
                    break

            pickup_keywords = ["pickup", "pick up", "pick-up", "collect", "collection"]
            delivery_keywords = ["deliver", "delivery", "deliveries", "drop off", "ship"]

            if any(word in text for word in pickup_keywords):
                if allow_override or not self.pending_order["fulfillment_type"]:
                    self.pending_order["fulfillment_type"] = "pickup"
                    self.pending_order["delivery_address"] = None
            elif any(word in text for word in delivery_keywords):
                if allow_override or not self.pending_order["fulfillment_type"]:
                    self.pending_order["fulfillment_type"] = "delivery"
                if allow_address_lookup and not self.pending_order["delivery_address"]:
                    address = self._extract_delivery_address_from_message(original_text)
                    if address:
                        self.pending_order["delivery_address"] = address

        if latest_message:
            _update_from_text(latest_message.lower(), latest_message, True, True)

        if history:
            history_lower = history.lower()
            _update_from_text(history_lower, history, False, False)

    def _normalize_price(self, price: Any) -> Optional[float]:
        if price is None:
            return None
        if isinstance(price, (int, float)):
            return float(price)
        if isinstance(price, str):
            digits = price.replace("₦", "").replace(",", "").strip()
            return float(digits) if digits.isdigit() else None
        return None

    def _extract_delivery_address_from_message(self, message: Optional[str]) -> Optional[str]:
        if not message:
            return None
        original = message.strip()
        if not original:
            return None
        lowered = original.lower()
        cues = [
            "deliver to",
            "delivery to",
            "send to",
            "ship to",
            "address is",
            "deliver at",
            "drop at"
        ]
        for cue in cues:
            if cue in lowered:
                start = lowered.find(cue) + len(cue)
                candidate = original[start:].strip(" .,:;\n\t")
                if candidate:
                    return candidate[:200]
        keywords = [
            "street", "st", "road", "rd", "avenue", "ave", "estate", "close",
            "phase", "way", "lane", "block", "apartment", "house", "junction"
        ]
        if any(kw in lowered for kw in keywords) and any(ch.isdigit() for ch in lowered):
            return original[:200]
        return None

    def update_profile(self, contact_data: Dict[str, Any], orders: List[Dict[str, Any]]):
        if contact_data:
            self.profile["name"] = contact_data.get("name") or self.profile["name"]
            self.profile["loyalty_points"] = contact_data.get("loyalty_points") or 0
            self.profile["order_count"] = contact_data.get("order_count") or 0
            self.profile["language"] = contact_data.get("language") or "en"
        self._apply_orders_snapshot(orders)
        self.last_profile_refresh = datetime.utcnow()

    def _apply_orders_snapshot(self, orders: List[Dict[str, Any]]):
        if not orders:
            self.order_history = []
            self.profile["favorite_items"] = []
            self.profile["last_order"] = None
            self.profile["last_delivery_address"] = None
            return

        normalized_orders: List[Dict[str, Any]] = []
        favorites: Counter = Counter()
        for order in orders:
            items = order.get("items") or []
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except json.JSONDecodeError:
                    items = []
            simplified_items = []
            for item in items:
                name = item.get("name")
                if not name:
                    continue
                qty = item.get("quantity") or 1
                simplified_items.append({"name": name, "quantity": qty})
                favorites[name] += qty
            normalized_orders.append({
                "id": order.get("id"),
                "order_number": order.get("order_number"),
                "status": order.get("status"),
                "created_at": order.get("created_at"),
                "fulfillment_type": order.get("fulfillment_type"),
                "delivery_address": order.get("delivery_address"),
                "items": simplified_items,
                "total_amount": order.get("total_amount"),
            })
        normalized_orders.sort(key=lambda row: row.get("created_at") or "", reverse=True)
        self.order_history = normalized_orders
        self.profile["last_order"] = normalized_orders[0] if normalized_orders else None
        if normalized_orders and normalized_orders[0].get("fulfillment_type"):
            self.profile["preferred_fulfillment"] = normalized_orders[0].get("fulfillment_type")
        latest_delivery = next(
            (
                row.get("delivery_address")
                for row in normalized_orders
                if row.get("fulfillment_type") == "delivery" and row.get("delivery_address")
            ),
            None,
        )
        self.profile["last_delivery_address"] = latest_delivery
        self.profile["favorite_items"] = [name for name, _ in favorites.most_common(3)]

    def has_all_order_details(self) -> bool:
        required = [
            self.pending_order["product_name"],
            self.pending_order["price"],
            self.pending_order["fulfillment_type"]
        ]
        if self.pending_order["fulfillment_type"] == "delivery":
            return all(required) and bool(self.pending_order["delivery_address"])
        return all(required)

    def get_missing_field(self) -> Optional[str]:
        if not self.pending_order["product_name"]:
            return "product"
        if not self.pending_order["fulfillment_type"]:
            return "fulfillment"
        if not self.pending_order["price"]:
            return "price"
        if self.pending_order["fulfillment_type"] == "delivery" and not self.pending_order["delivery_address"]:
            return "address"
        return None

    def build_profile_context(self) -> str:
        parts = []
        if self.profile["name"]:
            parts.append(f"Name: {self.profile['name']}")
        parts.append(f"Loyalty Points: {self.profile['loyalty_points']}")
        parts.append(f"Lifetime Orders: {self.profile['order_count']}")
        if self.profile["favorite_items"]:
            fav = ", ".join(self.profile["favorite_items"])
            parts.append(f"Favorites: {fav}")
        if self.profile["last_order"]:
            last = self.profile["last_order"]
            items_text = ", ".join(
                [
                    f"{item['name']} ×{item['quantity']}" if item['quantity'] > 1 else item['name']
                    for item in last.get("items", [])
                ]
            )
            parts.append(
                f"Last Order: {items_text} via {last.get('fulfillment_type') or 'unspecified'} on {last.get('created_at')}"
            )
        if self.profile.get("last_delivery_address"):
            parts.append(f"Last Delivery Address: {self.profile['last_delivery_address']}")
        if self.pending_order["product_name"]:
            missing = self.get_missing_field()
            pending_text = f"Pending order for {self.pending_order['product_name']}"
            if missing:
                pending_text += f" (need {missing})"
            parts.append(pending_text)
        return "\n".join(parts) or "No prior memory recorded."

    def build_brand_context(self) -> str:
        details: List[str] = []
        if self.brand_description:
            details.append(f"Brand description: {self.brand_description}")
        if self.brand_voice:
            details.append(f"Tone guidance: {self.brand_voice}")
        if self.brand_links:
            website = self.brand_links.get("website")
            instagram = self.brand_links.get("instagram")
            if website:
                details.append(f"Website: {website}")
            if instagram:
                details.append(f"Instagram: {instagram}")
        if self.integration_channels:
            channel_summaries = []
            for key, value in self.integration_channels.items():
                if not isinstance(value, dict):
                    continue
                status = "connected" if value.get("enabled") else "disabled"
                channel_summaries.append(f"{key}: {status}")
            if channel_summaries:
                details.append("Integration status: " + ", ".join(channel_summaries))
        pickup = self.get_pickup_summary()
        if pickup:
            details.append(f"Pickup: {pickup}")
        bank = self.settlement_account.get("bank") if isinstance(self.settlement_account, dict) else None
        account_number = self.settlement_account.get("account_number") if isinstance(self.settlement_account, dict) else None
        if bank and account_number:
            details.append(f"Settlement account: {bank} • {account_number}")
        return "\n".join(details)

    def get_pickup_summary(self) -> Optional[str]:
        parts: List[str] = []
        if self.pickup_address:
            parts.append(self.pickup_address)
        if self.pickup_instructions:
            parts.append(self.pickup_instructions)
        if not parts:
            return None
        return " • ".join(parts)

    def record_tool_call(self, tool_name: Optional[str]):
        if not tool_name:
            return
        now = datetime.utcnow()
        self.last_tool_name = tool_name
        self.last_tool_called_at = now
        self.tool_cooldowns[tool_name] = now
        if tool_name == "send_all_products":
            self.last_menu_shared_at = now

    def should_throttle_tool(self, tool_name: str, cooldown_seconds: int = 90) -> Tuple[bool, Optional[str]]:
        last_called = self.tool_cooldowns.get(tool_name)
        if not last_called:
            return False, None
        if datetime.utcnow() - last_called < timedelta(seconds=cooldown_seconds):
            reason = "Menu already shared recently." if tool_name == "send_all_products" else "Tool invoked too frequently."
            return True, reason
        return False, None

    def remember_menu_summary(self, products: List[Dict[str, Any]]):
        if products:
            self.menu_summary = products


class HaloAgent:
    def __init__(self):
        self.tools = agent_tools
        self.tool_definitions = self.tools.get_tool_definitions()
        self.system_prompt = agent_prompts.get_system_prompt(json.dumps(self.tool_definitions, indent=2))
        self.max_iterations = 5
        self.conversation_states = {}  # (business_id:phone) -> ConversationState

    async def run(
        self,
        message: str,
        phone: str,
        context: Optional[str] = None,
        *,
        business_id: Optional[str] = None,
        channel: str = "whatsapp",
    ) -> str:
        """Run the agent loop - handles tool calls silently and returns natural responses."""
        business_id = business_id or self._extract_business_id(context) or "sweetcrumbs_001"
        channel = channel or "whatsapp"

        state_key = f"{business_id}:{phone}"
        if state_key not in self.conversation_states:
            self.conversation_states[state_key] = ConversationState()
        state = self.conversation_states[state_key]
        state.update_channel(channel)
        state.update_business(business_id, None)

        from app.db.supabase_client import supabase

        conversation_history = ""
        inventory: List[Dict[str, Any]] = []
        business_name = state.business_name
        payment_details_text = None
        contact_id = state.contact_id
        contact_data: Dict[str, Any] = {}
        recent_orders: List[Dict[str, Any]] = []

        try:
            if business_id:
                contact_query = (
                    supabase
                    .table("contacts")
                    .select("id, business_id, name, loyalty_points, order_count, language")
                    .eq("phone_number", phone)
                    .eq("business_id", business_id)
                    .execute()
                )
            else:
                contact_query = None

            if contact_query and contact_query.data:
                contact_data = contact_query.data[0]
                contact_id = contact_data.get("id")
                business_id = contact_data.get("business_id") or business_id
                state.set_contact(contact_id)
                state.update_business(business_id, None)

                history = (
                    supabase
                    .table("message_logs")
                    .select("direction, content")
                    .eq("contact_id", contact_id)
                    .order("created_at", desc=True)
                    .limit(12)
                    .execute()
                )
                if history.data:
                    for msg in reversed(history.data[-8:]):
                        role = "Customer" if msg["direction"] == "IN" else "You"
                        conversation_history += f"{role}: {msg['content']}\n"

                orders_result = (
                    supabase
                    .table("orders")
                    .select("id, order_number, items, total_amount, status, fulfillment_type, delivery_address, created_at")
                    .eq("contact_id", contact_id)
                    .order("created_at", desc=True)
                    .limit(5)
                    .execute()
                )
                recent_orders = orders_result.data or []
            elif business_id:
                ensured_contact = self._ensure_contact_record(
                    supabase_client=supabase,
                    phone=phone,
                    business_id=business_id,
                )
                if ensured_contact:
                    contact_data = ensured_contact
                    contact_id = ensured_contact.get("id")
                    state.set_contact(contact_id)
                    state.update_business(business_id, None)

            if business_id:
                business = (
                    supabase
                    .table("businesses")
                    .select("business_name, inventory, payment_instructions")
                    .eq("business_id", business_id)
                    .single()
                    .execute()
                )
                if business.data:
                    inventory = business.data.get("inventory") or []
                    business_name = business.data.get("business_name") or business_name
                    payment_details_text = self._format_payment_instructions(business.data)
                    state.update_business(business_id, business_name)
                    state.update_brand_profile(business.data)
                else:
                    payment_details_text = None
            else:
                payment_details_text = None
        except Exception as e:
            logger.error(f"Error loading context: {e}")
            payment_details_text = None

        state.extract_from_history(conversation_history, message, inventory)
        state.update_profile(contact_data, recent_orders)

        if state.pending_order.get("product_name") and not state.pending_order.get("price"):
            product = self._find_product(inventory, state.pending_order["product_name"])
            if product:
                state.pending_order["price"] = state._normalize_price(product.get("price"))

        profile_context = state.build_profile_context()
        inventory_snapshot = self._format_inventory_snapshot(inventory)
        brand_context = state.build_brand_context()
        
        message_lower = message.lower()
        normalized_message = self._normalize_customer_message(message)
        previous_normalized_message = state.last_normalized_message
        state.remember_customer_message(normalized_message)
        greeting_hint = self._is_simple_greeting(message_lower)
        message_analysis = self._analyze_customer_message(
            state=state,
            message_lower=message_lower,
            normalized_message=normalized_message,
            previous_normalized=previous_normalized_message,
            contact_id=contact_id,
            business_id=state.business_id,
            phone=phone,
            raw_message=message,
            supabase_client=supabase,
        )

        if (
            state.pending_order.get("fulfillment_type") == "delivery"
            and not state.pending_order.get("delivery_address")
        ):
            fallback_address = state.profile.get("last_delivery_address")
            if fallback_address:
                same_address_cues = [
                    "same address",
                    "same spot",
                    "same place",
                    "same as before",
                    "usual address",
                    "usual spot",
                    "deliver to the usual",
                    "you already have my address",
                    "use my saved address",
                ]
                if any(phrase in message_lower for phrase in same_address_cues):
                    state.pending_order["delivery_address"] = fallback_address

        # Check if user is notifying payment
        payment_confirmation_requested = self._looks_like_payment_confirmation(message_lower)
        if payment_confirmation_requested:
            resolved_contact_id = self._resolve_contact_id(
                state=state,
                current_contact_id=contact_id,
                supabase_client=supabase,
                phone=phone,
                business_id=state.business_id,
            )
            if not resolved_contact_id:
                return (
                    "I want to log that payment but I can't find an order tied to this number yet. "
                    "Mind telling me what you ordered so I can match it?"
                )
            contact_id = resolved_contact_id
            try:
                pending_orders = (
                    supabase
                    .table("orders")
                    .select("id, order_number, items, total_amount, payment_reference")
                    .eq("contact_id", contact_id)
                    .eq("status", "pending_payment")
                    .order("created_at", desc=True)
                    .execute()
                )

                if not pending_orders.data:
                    return "I don't see any pending orders. Would you like to place a new order?"

                if len(pending_orders.data) > 1:
                    orders_list = []
                    for i, order in enumerate(pending_orders.data):
                        items = order.get('items', [])
                        if isinstance(items, str):
                            items = json.loads(items)
                        items_text = ", ".join([item['name'] for item in items]) if items else "items"
                        ref = order.get("payment_reference")
                        ref_text = f" (Ref: {ref})" if ref else ""
                        orders_list.append(
                            f"{i+1}. Order #{order['order_number']}\n   {items_text} - ₦{order['total_amount']:,}{ref_text}"
                        )

                    orders_text = "\n\n".join(orders_list)
                    return (
                        f"You have {len(pending_orders.data)} pending orders:\n\n{orders_text}\n\n"
                        f"Which order did you pay for? Reply with the order number (e.g., {pending_orders.data[0]['order_number']})"
                    )

                order = pending_orders.data[0]
                items = order.get('items', [])
                if isinstance(items, str):
                    items = json.loads(items)
                items_text = ", ".join([item['name'] for item in items]) if items else "your order"

                supabase.table("orders").update({
                    "status": "awaiting_confirmation",
                    "payment_notes": f"Customer said they paid via chat on {datetime.utcnow().isoformat()}",
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", order["id"]).execute()
                reference = order.get("payment_reference")
                reference_line = (
                    f"Please make sure the transfer narration includes {reference} so the team can match it instantly. "
                    if reference else ""
                )
                return (
                    f"Thanks for the heads up! I've moved Order #{order['order_number']} "
                    f"({items_text} - ₦{order['total_amount']:,}) to awaiting confirmation. {reference_line}"
                    "We'll verify it shortly and kick off prep right after. 🙏"
                )
            except Exception as e:
                logger.error(f"Payment notification error: {e}")

        reference_contact_id = None
        if "ord-" in message_lower:
            reference_contact_id = self._resolve_contact_id(
                state=state,
                current_contact_id=contact_id,
                supabase_client=supabase,
                phone=phone,
                business_id=state.business_id,
            )
        if reference_contact_id:
            contact_id = reference_contact_id
            try:
                import re

                match = re.search(r"ORD-\d+", message.upper())
                if match:
                    order_number = match.group(0).upper()
                    order_query = (
                        supabase
                        .table("orders")
                        .select("id, order_number")
                        .eq("contact_id", contact_id)
                        .eq("order_number", order_number)
                        .eq("status", "pending_payment")
                        .limit(1)
                        .execute()
                    )

                    order_row = order_query.data[0] if order_query.data else None
                    if order_row:
                        supabase.table("orders").update({
                            "status": "awaiting_confirmation",
                            "payment_notes": f"Customer shared payment reference via chat on {datetime.utcnow().isoformat()}",
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", order_row["id"]).execute()
                        return (
                            f"Perfect! I've let the team know about your payment for Order #{order_number}. "
                            "They'll confirm it shortly! 🙏"
                        )
                    else:
                        return "I couldn't find that order number among pending payments. Mind confirming the digits?"
            except Exception as e:
                logger.error(f"Order number payment error: {e}")
        elif "ord-" in message_lower:
            return (
                "I spotted that order number but couldn't match it to your profile yet. "
                "Mind confirming the phone number used for the order or telling me what you bought?"
            )

        payment_instruction_keywords = [
            "payment details",
            "payment info",
            "payment instruction",
            "payment instructions",
            "bank details",
            "bank info",
            "bank account",
            "account number",
            "acct number",
            "share your account",
            "send your account",
            "send account",
            "how do i pay",
            "how should i pay",
            "where do i pay",
            "transfer details",
            "paying now",
            "need payment",
        ]
        wants_payment_instructions = any(phrase in message_lower for phrase in payment_instruction_keywords)
        if wants_payment_instructions:
            resolved_contact_id = self._resolve_contact_id(
                state=state,
                current_contact_id=contact_id,
                supabase_client=supabase,
                phone=phone,
                business_id=state.business_id,
            )
            if not resolved_contact_id:
                return (
                    "I'd love to share the payment details, but I don't see an order on file yet. "
                    "Tell me what you'd like to get and I'll pull it up for you."
                )
            contact_id = resolved_contact_id
            try:
                pending_instruction_order = (
                    supabase
                    .table("orders")
                    .select("id, order_number, total_amount, payment_reference")
                    .eq("contact_id", contact_id)
                    .eq("status", "pending_payment")
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )

                if not pending_instruction_order.data:
                    return (
                        "I'd love to share the bank details, but I don't see an order waiting for payment yet. "
                        "Want me to start an order for you?"
                    )

                order = pending_instruction_order.data[0]
                instructions_body = self._build_payment_instruction_block(
                    order_number=order.get("order_number"),
                    payment_reference=order.get("payment_reference"),
                    payment_details_text=payment_details_text,
                    pickup_summary=state.get_pickup_summary(),
                    order_internal_id=order.get("id"),
                )
                order_label = order.get("order_number") or str(order.get("id"))
                total_text = self._format_currency(order.get("total_amount"))
                reference_hint = order.get("payment_reference") or order_label
                try:
                    supabase.table("orders").update({
                        "payment_instructions_sent": True,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("id", order["id"]).execute()
                except Exception as marker_err:
                    logger.warning(
                        f"Failed to update payment instruction flag for order {order.get('id')}: {marker_err}"
                    )
                reference_line = (
                    f"Type {reference_hint} in the bank reference/description so we can match it instantly.\n\n"
                    if reference_hint
                    else ""
                )
                return (
                    f"No problem! Here's how to pay for Order #{order_label} ({total_text}).\n\n"
                    f"{instructions_body}\n\n"
                    f"{reference_line}"
                    "After you transfer, reply \"I paid\" with the reference or receipt so I can flag it for review."
                )
            except Exception as e:
                logger.error(f"Payment instruction share error: {e}")
                return "I'm having trouble loading the payment details right now. Mind trying again in a moment?"
        
        # Check if user is giving feedback/rating (HIGHEST PRIORITY)
        if any(word in message_lower for word in ["star", "rating", "rate", "/5"]):
            # Just acknowledge, don't create order
            return "Thank you so much for your feedback! We really appreciate it and hope to serve you again soon! 😊"
        
        # Check if user confirms pickup/delivery
        pickup_keywords = ["picked up", "picked it up", "received it", "got it", "collected it", "received my order", "got my order"]
        if contact_id and any(keyword in message_lower for keyword in pickup_keywords):
            # Mark order as completed
            try:
                recent_order = supabase.table("orders").select("id, order_number, items").eq("contact_id", contact_id).eq("status", "ready_for_pickup").order("created_at", desc=True).limit(1).execute()
                if recent_order.data:
                    order_id = recent_order.data[0]["id"]
                    order_number = recent_order.data[0]["order_number"]
                    items = recent_order.data[0].get('items', [])
                    if isinstance(items, str):
                        items = json.loads(items)
                    items_text = ", ".join([item['name'] for item in items]) if items else "your order"
                    
                    supabase.table("orders").update({"status": "completed", "completed_at": datetime.utcnow().isoformat()}).eq("id", order_id).execute()
                    return f"✅ Awesome! Your order #{order_number} is now complete. Thank you for choosing us!\n\nHow was your experience with {items_text}? Reply with a rating (1-5 stars) ⭐"
                else:
                    return "I don't see any orders ready for pickup. Is there anything else I can help you with?"
            except Exception as e:
                logger.error(f"Order completion error: {e}")
        
        # CRITICAL: Check if we have all order details AND user wants to order
        order_intent_keywords = ["order", "buy", "purchase", "get", "want"]
        confirmation_keywords = [
            "yes", "yeah", "yep", "sure", "ok", "okay", "alright",
            "do it", "please do", "confirm", "sounds good", "go ahead"
        ]

        explicit_intent = any(keyword in message_lower for keyword in order_intent_keywords)
        confirmation_intent = (
            any(phrase in message_lower for phrase in confirmation_keywords)
            and state.pending_order.get("product_name") is not None
        )

        if explicit_intent or confirmation_intent:
            state.mark_order_intent()

        missing_field = state.get_missing_field()
        if state.has_order_intent() and missing_field and not state.has_all_order_details():
            prompt = self._prompt_for_missing_detail(state, missing_field)
            if prompt:
                return prompt

        if state.has_all_order_details() and state.has_order_intent() and business_id:
            logger.info(f"Creating order immediately: {state.pending_order}")
            pending_snapshot = state.pending_order.copy()
            try:
                price_value = pending_snapshot.get("price") or 0
                if isinstance(price_value, str):
                    normalized = price_value.replace("₦", "").replace(",", "").strip()
                    price_value = float(normalized) if normalized.isdigit() else 0
                order_total = float(price_value) * float(pending_snapshot.get("quantity", 1))
                order_response_raw = await self.tools.db_create_order(
                    phone=phone,
                    business_id=business_id,
                    items=[{
                        "name": pending_snapshot["product_name"],
                        "quantity": pending_snapshot.get("quantity", 1),
                        "price": pending_snapshot["price"]
                    }],
                    total=order_total,
                    delivery_type=pending_snapshot["fulfillment_type"],
                    delivery_address=pending_snapshot.get("delivery_address"),
                    channel=state.channel
                )
                try:
                    order_response = json.loads(order_response_raw or "{}")
                except json.JSONDecodeError:
                    order_response = {}

                if order_response.get("status") != "success":
                    error_notice = order_response.get("message") or "Unknown error"
                    logger.error(f"Order creation failed for {phone}/{business_id}: {error_notice}")
                    return (
                        "I tried saving that order but the system needs a moment. "
                        "Give me a second and we can try again."
                    )

                order_number = order_response.get("order_number")
                payment_reference = order_response.get("payment_reference")
                order_id = order_response.get("order_id")

                if not order_id and contact_id:
                    try:
                        latest_order = (
                            supabase
                            .table("orders")
                            .select("id, order_number, payment_reference")
                            .eq("contact_id", contact_id)
                            .order("created_at", desc=True)
                            .limit(1)
                            .execute()
                        )
                        if latest_order.data:
                            resolved = latest_order.data[0]
                            order_id = resolved.get("id") or order_id
                            order_number = order_number or resolved.get("order_number")
                            payment_reference = payment_reference or resolved.get("payment_reference")
                    except Exception as lookup_err:
                        logger.warning(f"Could not backfill order metadata for {phone}: {lookup_err}")

                if order_id:
                    try:
                        supabase.table("orders").update({
                            "payment_instructions_sent": True,
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", order_id).execute()
                    except Exception as marker_err:
                        logger.warning(f"Failed to mark payment instructions sent for order {order_id}: {marker_err}")
                if (
                    pending_snapshot.get("fulfillment_type") == "delivery"
                    and pending_snapshot.get("delivery_address")
                ):
                    state.profile["last_delivery_address"] = pending_snapshot["delivery_address"]
                state.reset_pending_order()
                total_text = self._format_currency(order_total)
                order_identifier = order_number or (f"ORD-{order_id}" if order_id else None)
                payment_block = self._build_payment_instruction_block(
                    order_number=order_number,
                    payment_reference=payment_reference,
                    payment_details_text=payment_details_text,
                    pickup_summary=state.get_pickup_summary(),
                    order_internal_id=order_id,
                )
                reference_hint = payment_reference or order_identifier
                reference_line = (
                    f"Please type {reference_hint} in the bank transfer narration/reference so we can match it quickly.\n\n"
                    if reference_hint
                    else ""
                )
                address_line = ""
                if pending_snapshot.get("fulfillment_type") == "delivery":
                    delivery_dest = pending_snapshot.get("delivery_address") or state.profile.get("last_delivery_address")
                    if delivery_dest:
                        address_line = (
                            f"Delivering to: {delivery_dest}\n"
                            "If you need it sent somewhere else, just let me know before we dispatch.\n\n"
                        )
                order_heading = f"Order ID: {order_identifier}\n" if order_identifier else ""
                return (
                    f"Perfect! Order confirmed for {pending_snapshot['product_name']} "
                    f"({pending_snapshot['fulfillment_type']}).\n\n"
                    f"{order_heading}Order Total: {total_text}\n\n{address_line}{payment_block}\n\n"
                    f"{reference_line}"
                    "Once you've made the transfer, just let me know and we'll get started on your order right away! 🎉"
                )
            except Exception as e:
                logger.error(f"Order creation failed: {e}")
                return "I had trouble creating your order. Let me connect you with support."
        
        user_context_blocks = [
            f"Channel: {channel}",
            f"Business ID: {business_id}",
            f"Business Name: {state.business_name}",
            f"Customer Profile & Memory:\n{profile_context}",
        ]
        if brand_context:
            user_context_blocks.append(f"Business Brand Guidelines:\n{brand_context}")
        if inventory_snapshot:
            user_context_blocks.append(f"Inventory Snapshot:\n{inventory_snapshot}")
        if message_analysis.get("notes"):
            user_context_blocks.append("Agent Alert:\n" + "\n".join(message_analysis["notes"]))

        if context:
            user_context_blocks.append(f"Additional Context: {context}")
        user_context_blocks.append(f"Recent conversation:\n{conversation_history or 'No previous messages.'}")
        user_context_blocks.append(f"Customer now says: {message}")
        if greeting_hint:
            user_context_blocks.append(
                "Agent note: Customer only sent a greeting. Keep it warm and conversational—welcome them back and ask how you can help without assuming an order or payment."
            )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": "\n\n".join(user_context_blocks)}
        ]

        for _ in range(self.max_iterations):
            response_text = await meta_ai_service.chat_completion(messages, temperature=0.7)
            
            if not response_text:
                return "I'm having a bit of trouble right now. Mind trying again in a sec?"
            
            response_blocks = self._extract_json_blocks(response_text)

            if not response_blocks:
                fallback = self._extract_action_message(response_text)
                if fallback:
                    return fallback
                logger.info(f"Agent returned natural text: {response_text[:120]}")
                return self._extract_final_message(response_text)

            final_answer = None
            tool_called = False

            for block in response_blocks:
                action = block.get("action")

                if action == "final_answer":
                    final_answer = block.get("message", "Got it!")
                    continue

                if action == "tool_call":
                    tool_called = True
                    tool_name = block.get("tool_name")
                    parameters = block.get("parameters", {})

                    throttle, reason = state.should_throttle_tool(tool_name)
                    if throttle:
                        tool_result = json.dumps({"status": "throttled", "reason": reason})
                        logger.info(f"Tool {tool_name} throttled: {reason}")
                    else:
                        if "phone" not in parameters:
                            parameters["phone"] = phone
                        if "business_id" not in parameters and state.business_id:
                            parameters["business_id"] = state.business_id
                        if tool_name in {"send_all_products", "send_product_with_image"} and "channel" not in parameters:
                            parameters["channel"] = state.channel

                        tool_result = await self._execute_tool(tool_name, parameters)
                        state.record_tool_call(tool_name)
                        self._capture_tool_side_effects(state, tool_name, tool_result)
                        logger.info(f"Tool {tool_name} executed: {str(tool_result)[:120]}")

                    messages.append({"role": "assistant", "content": json.dumps(block)})
                    messages.append({"role": "user", "content": f"Tool result: {tool_result}"})
                    continue

                logger.debug(f"Unknown agent action: {action}")

            if tool_called and not final_answer:
                # Need another round so model can respond with natural text
                continue

            if final_answer:
                return self._extract_final_message(final_answer)

            return "Let me know how I can help!"
                
        return "This is taking a bit longer than expected. Can you try asking in a simpler way?"

    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        try:
            if hasattr(self.tools, tool_name):
                method = getattr(self.tools, tool_name)
                # Call the method with unpacked parameters
                # Note: This assumes parameters match the method signature
                # In a robust system, we'd inspect signature or use **kwargs
                return await method(**parameters)
            else:
                return json.dumps({"error": f"Tool '{tool_name}' not found"})
        except Exception as e:
            return json.dumps({"error": f"Error executing tool '{tool_name}': {str(e)}"})

    def _normalize_customer_message(self, message: Optional[str]) -> Optional[str]:
        if not message:
            return None
        cleaned = message.strip().lower()
        if not cleaned:
            return None
        return re.sub(r"\s+", " ", cleaned)

    def _analyze_customer_message(
        self,
        *,
        state: ConversationState,
        message_lower: str,
        normalized_message: Optional[str],
        previous_normalized: Optional[str],
        contact_id: Optional[int],
        business_id: Optional[str],
        phone: str,
        raw_message: str,
        supabase_client,
    ) -> Dict[str, Any]:
        notes: List[str] = []
        escalation_id = None
        issue_type = None

        if normalized_message and previous_normalized and normalized_message == previous_normalized:
            notes.append("Customer repeated the same request; acknowledge it and clarify what they still need.")

        if self._mentions_delivery_conflict(message_lower):
            notes.append("Customer mentioned both pickup and delivery. Ask which fulfillment option they prefer before proceeding.")

        if self._looks_ambiguous(message_lower):
            notes.append("Intent feels unclear. Ask a concise clarifying question before committing to an action.")

        escalation_keywords = {
            "complain": "service_complaint",
            "complaint": "service_complaint",
            "refund": "refund_request",
            "angry": "service_complaint",
            "disappointed": "service_complaint",
            "escalate": "owner_callback",
            "manager": "owner_callback",
            "chargeback": "payment_conflict",
            "wrong order": "order_issue",
            "missing": "order_issue",
            "late": "delivery_issue",
            "scam": "payment_conflict",
            "fraud": "payment_conflict",
            "dispute": "payment_conflict",
        }

        for keyword, mapped in escalation_keywords.items():
            if keyword in message_lower:
                issue_type = mapped
                break

        if not issue_type and "payment" in message_lower and any(term in message_lower for term in ["issue", "problem", "double", "wrong", "failed"]):
            issue_type = "payment_conflict"

        if issue_type and business_id:
            signature = f"{issue_type}:{normalized_message or raw_message.strip().lower()}"
            if state.last_escalation_signature != signature:
                escalation_id = self._record_escalation_ticket(
                    supabase_client=supabase_client,
                    business_id=business_id,
                    contact_id=contact_id,
                    phone=phone,
                    issue_type=issue_type,
                    description=raw_message.strip(),
                )
                if escalation_id:
                    state.last_escalation_signature = signature
                    notes.append(
                        f"Sensitive issue detected ({issue_type}). Escalation ticket #{escalation_id} created—reassure the customer and promise a follow-up."
                    )

        return {"notes": notes, "escalation_id": escalation_id}

    def _mentions_delivery_conflict(self, message_lower: str) -> bool:
        if not message_lower:
            return False
        pickup_keywords = ["pickup", "pick up", "collect", "collection"]
        delivery_keywords = ["deliver", "delivery", "ship", "drop off"]
        return any(word in message_lower for word in pickup_keywords) and any(word in message_lower for word in delivery_keywords)

    def _looks_ambiguous(self, message_lower: str) -> bool:
        if not message_lower:
            return True
        filler_cues = ["not sure", "confused", "what now", "what next", "help", "??", "???"]
        if any(cue in message_lower for cue in filler_cues):
            return True
        if message_lower.strip() in {"hmm", "ok", "okay", "alright", "yes", "no"}:
            return True
        if "?" in message_lower and not any(keyword in message_lower for keyword in ["order", "pay", "pickup", "deliver", "price", "menu", "tracking", "status"]):
            return True
        return False

    def _record_escalation_ticket(
        self,
        *,
        supabase_client,
        business_id: str,
        contact_id: Optional[int],
        phone: str,
        issue_type: str,
        description: str,
    ) -> Optional[int]:
        try:
            payload = {
                "business_id": business_id,
                "contact_id": contact_id,
                "phone_number": phone,
                "issue_type": issue_type,
                "description": description,
                "status": "open",
            }
            result = supabase_client.table("escalations").insert(payload).execute()
            if result.data:
                return result.data[0].get("id")
        except Exception as exc:
            logger.error(f"Failed to record escalation: {exc}")
        return None

    def _extract_business_id(self, context: Optional[str]) -> Optional[str]:
        if not context:
            return None
        token = "Business ID:"
        if token in context:
            try:
                after = context.split(token, 1)[1].strip()
                return after.split()[0].strip().strip(",")
            except Exception:
                return None
        return None

    def _format_inventory_snapshot(self, inventory: List[Dict[str, Any]]) -> str:
        if not inventory:
            return ""
        lines = []
        for product in inventory[:6]:
            name = product.get("name")
            if not name:
                continue
            price = product.get("price")
            if isinstance(price, (int, float)):
                price_text = f"₦{int(price):,}"
            elif isinstance(price, str) and price.strip():
                price_text = price.strip()
            else:
                price_text = "price on request"
            lines.append(f"- {name}: {price_text}")
        return "\n".join(lines)

    def _format_payment_instructions(self, business_data: Dict[str, Any]) -> str:
        payment_meta = business_data.get("settlement_account") or business_data.get("payment_instructions")
        if isinstance(payment_meta, str):
            try:
                payment_meta = json.loads(payment_meta)
            except Exception:
                payment_meta = payment_meta.strip()

        if isinstance(payment_meta, dict):
            bank = payment_meta.get("bank") or "GTBank"
            account_name = payment_meta.get("account_name") or business_data.get("business_name") or "SweetCrumbs Cakes"
            account_number = payment_meta.get("account_number") or "0123456789"
            extra = payment_meta.get("notes") or "Send a quick message once you pay so we can confirm."
            return (
                f"💳 Payment Details:\nBank: {bank}\nAccount Name: {account_name}\n"
                f"Account Number: {account_number}\n{extra}"
            )
        if isinstance(payment_meta, str) and payment_meta.strip():
            return payment_meta.strip()
        return self._default_payment_instructions()

    def _default_payment_instructions(self) -> str:
        return (
            "💳 Payment Details:\nBank: GTBank\nAccount Name: SweetCrumbs Cakes\n"
            "Account Number: 0123456789"
        )

    def _build_payment_instruction_block(
        self,
        order_number: Optional[str],
        payment_reference: Optional[str],
        payment_details_text: Optional[str],
        pickup_summary: Optional[str] = None,
        order_internal_id: Optional[Any] = None,
    ) -> str:
        parts: List[str] = []
        internal_id_text = str(order_internal_id).strip() if order_internal_id else None
        order_identifier = order_number or (f"ORD-{internal_id_text}" if internal_id_text else None)
        reference_hint = payment_reference or order_identifier
        if order_identifier:
            parts.append(f"Order ID: {order_identifier}")
        if reference_hint:
            if reference_hint == order_identifier:
                parts.append(
                    f"Use {reference_hint} as your bank transfer narration/reference so we can match the receipt instantly."
                )
            else:
                parts.append(f"Payment Reference: {reference_hint}")
                parts.append(
                    f"Please include \"{reference_hint}\" in your bank transfer narration or on the receipt so we can match it quickly."
                )
        instructions = payment_details_text or self._default_payment_instructions()
        parts.append(instructions.strip())
        if pickup_summary:
            parts.append(f"Pickup: {pickup_summary}")
        return "\n".join(parts)

    def _format_currency(self, amount: Optional[float]) -> str:
        if amount is None:
            return "₦0"
        try:
            return f"₦{int(amount):,}"
        except Exception:
            return "₦0"

    def _find_product(self, inventory: List[Dict[str, Any]], product_name: str) -> Optional[Dict[str, Any]]:
        if not inventory or not product_name:
            return None
        name_lower = product_name.lower()
        for product in inventory:
            if (product.get("name") or "").lower() == name_lower:
                return product
        return None

    def _capture_tool_side_effects(self, state: ConversationState, tool_name: str, tool_result: Any):
        try:
            parsed = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
        except Exception:
            return
        if tool_name == "send_all_products" and isinstance(parsed, dict):
            products = parsed.get("products")
            if isinstance(products, list):
                state.remember_menu_summary(products)
        if tool_name == "send_product_with_image" and isinstance(parsed, dict):
            product = parsed.get("product")
            if product:
                state.remember_menu_summary([product])

    def _prompt_for_missing_detail(self, state: ConversationState, missing_field: str) -> Optional[str]:
        pending = state.pending_order
        business = state.business_name or "our shop"
        product = pending.get("product_name")
        fulfillment = pending.get("fulfillment_type")
        quantity = pending.get("quantity") or 1

        if missing_field == "product":
            return (
                f"Happy to help with your order from {business}! What would you like to get today? "
                "Feel free to mention the exact item or share a quick idea so I can guide you."
            )
        if missing_field == "fulfillment":
            base = product or "that order"
            qty_text = f"{quantity} x {base}" if product and quantity > 1 else base
            return (
                f"Noted on {qty_text}! Would you like to pick it up or should we deliver it to you?"
            )
        if missing_field == "price" and product:
            return (
                f"I have {product} noted. Do you recall the size or price you want, or should I double-check the menu to be sure?"
            )
        if missing_field == "address" and fulfillment == "delivery":
            base = product or "your order"
            last_address = state.profile.get("last_delivery_address")
            if last_address:
                return (
                    f"Great, we'll deliver {base}. Should I send it to the usual spot ({last_address}) or do you have a new delivery location?"
                )
            return (
                f"Great, we'll deliver {base}. Could you share the delivery address plus any nearby landmark so the rider finds you easily?"
            )
        return None

    def _looks_like_payment_confirmation(self, message_lower: Optional[str]) -> bool:
        if not message_lower:
            return False
        confirmation_phrases = [
            "i paid",
            "i have paid",
            "i've paid",
            "i just paid",
            "payment done",
            "payment made",
            "i made the payment",
            "i sent the money",
            "transfer done",
            "i've transferred",
            "money sent",
            "paid already",
        ]
        return any(phrase in message_lower for phrase in confirmation_phrases)

    def _is_simple_greeting(self, text: str) -> bool:
        if not text:
            return False
        cleaned = text.strip()
        if not cleaned:
            return False
        greeting_phrases = [
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "morning",
            "evening",
            "afternoon",
            "greetings",
        ]
        if not any(phrase in cleaned for phrase in greeting_phrases):
            return False
        disqualifiers = [
            "order",
            "buy",
            "price",
            "payment",
            "paid",
            "ready",
            "pickup",
            "deliver",
            "address",
            "status",
            "question",
            "how much",
            "cost",
            "balance",
        ]
        if any(word in cleaned for word in disqualifiers):
            return False
        return len(cleaned) <= 120

    def _clean_json_response(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _extract_json_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Handle responses that include multiple JSON objects (tool call + final answer)."""
        cleaned = self._clean_json_response(text)
        decoder = json.JSONDecoder()
        idx = 0
        results: List[Dict[str, Any]] = []

        while idx < len(cleaned):
            while idx < len(cleaned) and cleaned[idx].isspace():
                idx += 1
            if idx >= len(cleaned):
                break

            if cleaned[idx] not in "{[":
                idx += 1
                continue

            try:
                obj, offset = decoder.raw_decode(cleaned[idx:])
                if isinstance(obj, dict):
                    results.append(obj)
                idx += offset
            except json.JSONDecodeError:
                idx += 1

        return results

    def _extract_final_message(self, text: str) -> str:
        if not text:
            return ""

        cleaned = self._clean_json_response(str(text)).strip()
        candidates: List[str] = []

        def _collect(obj: Any):
            if isinstance(obj, dict):
                message = obj.get("message")
                if isinstance(message, str):
                    candidates.append(message.strip())
                    return
                content = obj.get("content")
                if isinstance(content, str):
                    candidates.append(content.strip())
                    return
            elif isinstance(obj, list):
                for entry in obj:
                    _collect(entry)

        if cleaned.startswith("{") or cleaned.startswith("["):
            try:
                parsed = json.loads(cleaned)
                _collect(parsed)
            except json.JSONDecodeError:
                pass

        if not candidates:
            brace_start = cleaned.find('{')
            brace_end = cleaned.rfind('}')
            if brace_start != -1 and brace_end > brace_start:
                snippet = cleaned[brace_start:brace_end+1]
                try:
                    parsed = json.loads(snippet)
                    _collect(parsed)
                except json.JSONDecodeError:
                    pass

        if not candidates:
            match = re.search(r'"message"\s*:\s*"(.*?)"', cleaned)
            if match:
                extracted = bytes(match.group(1), "utf-8").decode("unicode_escape")
                candidates.append(extracted.strip())

        return candidates[0] if candidates else cleaned

    def _extract_action_message(self, text: Any) -> Optional[str]:
        if not text:
            return None
        cleaned = self._clean_json_response(str(text))
        if "\"action\"" not in cleaned:
            return None
        try:
            snippet = self._extract_json_blocks(cleaned)
            for block in snippet:
                if block.get("action") == "final_answer":
                    message = block.get("message")
                    if isinstance(message, str):
                        return message.strip()
        except Exception:
            pass
        match = re.search(r"\{[^{}]*\"action\"\s*:\s*\"final_answer\"[^{}]*\}", cleaned, re.DOTALL)
        if match:
            try:
                block = json.loads(match.group(0))
                message = block.get("message")
                if isinstance(message, str):
                    return message.strip()
            except Exception:
                return None
        return None

    def _resolve_contact_id(
        self,
        *,
        state: ConversationState,
        current_contact_id: Optional[int],
        supabase_client,
        phone: Optional[str],
        business_id: Optional[str],
    ) -> Optional[int]:
        if current_contact_id:
            return current_contact_id
        lookup_id = self._lookup_contact_id(
            supabase_client=supabase_client,
            phone=phone,
            business_id=business_id,
        )
        if lookup_id:
            state.set_contact(lookup_id)
        return lookup_id

    def _ensure_contact_record(
        self,
        *,
        supabase_client,
        phone: Optional[str],
        business_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not phone or not business_id:
            return None
        payload = {
            "phone_number": phone,
            "business_id": business_id,
            "opt_in": True,
            "status": "active",
            "consent_timestamp": datetime.utcnow().isoformat(),
        }
        try:
            supabase_client.table("contacts").upsert(payload, on_conflict="phone_number,business_id").execute()
            lookup = (
                supabase_client
                .table("contacts")
                .select("id, business_id, name, loyalty_points, order_count, language")
                .eq("phone_number", phone)
                .eq("business_id", business_id)
                .limit(1)
                .execute()
            )
            if lookup.data:
                return lookup.data[0]
        except Exception as exc:
            logger.error(f"Failed to ensure contact record for {phone}/{business_id}: {exc}")
        return None

    def _lookup_contact_id(
        self,
        *,
        supabase_client,
        phone: Optional[str],
        business_id: Optional[str],
    ) -> Optional[int]:
        if not phone or not business_id:
            return None
        try:
            lookup = (
                supabase_client
                .table("contacts")
                .select("id")
                .eq("phone_number", phone)
                .eq("business_id", business_id)
                .limit(1)
                .execute()
            )
            if lookup.data:
                return lookup.data[0].get("id")
        except Exception as exc:
            logger.error(f"Failed to look up contact for {phone}/{business_id}: {exc}")
        return None

agent = HaloAgent()
