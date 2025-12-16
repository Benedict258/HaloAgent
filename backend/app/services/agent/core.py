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
            "fulfillment_type": None
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
        }
        self.order_history: List[Dict[str, Any]] = []
        self.contact_id: Optional[int] = None
        self.last_profile_refresh: Optional[datetime] = None

    def reset_pending_order(self):
        self.pending_order = {
            "product_name": None,
            "price": None,
            "quantity": 1,
            "fulfillment_type": None
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

    def set_contact(self, contact_id: Optional[int]):
        if contact_id:
            self.contact_id = contact_id

    def extract_from_history(self, history: str, inventory: List[Dict[str, Any]]):
        """Extract order details from conversation history."""
        history_lower = history.lower()

        for product in inventory or []:
            name = (product.get("name") or "").lower()
            if name and name in history_lower:
                self.pending_order["product_name"] = product.get("name")
                self.pending_order["price"] = self._normalize_price(product.get("price"))
                break

        if "pickup" in history_lower:
            self.pending_order["fulfillment_type"] = "pickup"
        elif "delivery" in history_lower or "deliver" in history_lower:
            self.pending_order["fulfillment_type"] = "delivery"

    def _normalize_price(self, price: Any) -> Optional[float]:
        if price is None:
            return None
        if isinstance(price, (int, float)):
            return float(price)
        if isinstance(price, str):
            digits = price.replace("₦", "").replace(",", "").strip()
            return float(digits) if digits.isdigit() else None
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
                "items": simplified_items,
                "total_amount": order.get("total_amount"),
            })
        normalized_orders.sort(key=lambda row: row.get("created_at") or "", reverse=True)
        self.order_history = normalized_orders
        self.profile["last_order"] = normalized_orders[0] if normalized_orders else None
        if normalized_orders and normalized_orders[0].get("fulfillment_type"):
            self.profile["preferred_fulfillment"] = normalized_orders[0].get("fulfillment_type")
        self.profile["favorite_items"] = [name for name, _ in favorites.most_common(3)]

    def has_all_order_details(self) -> bool:
        return all([
            self.pending_order["product_name"],
            self.pending_order["price"],
            self.pending_order["fulfillment_type"]
        ])

    def get_missing_field(self) -> Optional[str]:
        if not self.pending_order["product_name"]:
            return "product"
        if not self.pending_order["fulfillment_type"]:
            return "fulfillment"
        if not self.pending_order["price"]:
            return "price"
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
        if self.pending_order["product_name"]:
            missing = self.get_missing_field()
            pending_text = f"Pending order for {self.pending_order['product_name']}"
            if missing:
                pending_text += f" (need {missing})"
            parts.append(pending_text)
        return "\n".join(parts) or "No prior memory recorded."

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
                    .select("id, order_number, items, total_amount, status, fulfillment_type, created_at")
                    .eq("contact_id", contact_id)
                    .order("created_at", desc=True)
                    .limit(5)
                    .execute()
                )
                recent_orders = orders_result.data or []

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
                else:
                    payment_details_text = None
            else:
                payment_details_text = None
        except Exception as e:
            logger.error(f"Error loading context: {e}")
            payment_details_text = None

        state.extract_from_history(conversation_history + message, inventory)
        state.update_profile(contact_data, recent_orders)

        if state.pending_order.get("product_name") and not state.pending_order.get("price"):
            product = self._find_product(inventory, state.pending_order["product_name"])
            if product:
                state.pending_order["price"] = state._normalize_price(product.get("price"))

        profile_context = state.build_profile_context()
        inventory_snapshot = self._format_inventory_snapshot(inventory)
        
        message_lower = message.lower()

        # Check if user is notifying payment
        if contact_id and any(word in message_lower for word in ["paid", "payment", "transferred", "sent money"]):
            try:
                pending_orders = (
                    supabase
                    .table("orders")
                    .select("id, order_number, items, total_amount")
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
                        orders_list.append(f"{i+1}. Order #{order['order_number']}\n   {items_text} - ₦{order['total_amount']:,}")

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

                supabase.table("orders").update({"status": "awaiting_confirmation"}).eq("id", order["id"]).execute()
                return (
                    f"Thank you! I've notified the business owner about your payment for Order #{order['order_number']} "
                    f"({items_text} - ₦{order['total_amount']:,}). They'll confirm it shortly and we'll start preparing your order! 🙏"
                )
            except Exception as e:
                logger.error(f"Payment notification error: {e}")

        if contact_id and "ord-" in message_lower:
            try:
                import re

                match = re.search(r'ORD-\d+', message.upper())
                if match:
                    order_number = match.group(0)
                    order = (
                        supabase
                        .table("orders")
                        .select("id, order_number")
                        .eq("contact_id", contact_id)
                        .eq("order_number", order_number)
                        .eq("status", "pending_payment")
                        .single()
                        .execute()
                    )

                    if order.data:
                        supabase.table("orders").update({"status": "awaiting_confirmation"}).eq("id", order.data["id"]).execute()
                        return f"Perfect! I've notified the business owner about your payment for Order #{order_number}. They'll confirm it shortly! 🙏"
            except Exception as e:
                logger.error(f"Order number payment error: {e}")
        
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

        if state.has_all_order_details() and state.has_order_intent() and business_id:
            logger.info(f"Creating order immediately: {state.pending_order}")
            pending_snapshot = state.pending_order.copy()
            try:
                price_value = pending_snapshot.get("price") or 0
                if isinstance(price_value, str):
                    normalized = price_value.replace("₦", "").replace(",", "").strip()
                    price_value = float(normalized) if normalized.isdigit() else 0
                order_total = float(price_value) * float(pending_snapshot.get("quantity", 1))
                await self.tools.db_create_order(
                    phone=phone,
                    business_id=business_id,
                    items=[{
                        "name": pending_snapshot["product_name"],
                        "quantity": pending_snapshot.get("quantity", 1),
                        "price": pending_snapshot["price"]
                    }],
                    total=order_total,
                    delivery_type=pending_snapshot["fulfillment_type"]
                )
                state.reset_pending_order()
                payment_copy = payment_details_text or self._default_payment_instructions()
                total_text = self._format_currency(order_total)
                return (
                    f"Perfect! Order confirmed for {pending_snapshot['product_name']} "
                    f"({pending_snapshot['fulfillment_type']}).\n\n"
                    f"Order Total: {total_text}\n\n{payment_copy}\n\n"
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
        if inventory_snapshot:
            user_context_blocks.append(f"Inventory Snapshot:\n{inventory_snapshot}")
        if context:
            user_context_blocks.append(f"Additional Context: {context}")
        user_context_blocks.append(f"Recent conversation:\n{conversation_history or 'No previous messages.'}")
        user_context_blocks.append(f"Customer now says: {message}")

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
        payment_meta = business_data.get("payment_instructions")
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

agent = HaloAgent()
