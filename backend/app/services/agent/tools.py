from app.services.loyalty import loyalty_service
from app.services.compliance import compliance_service
from app.services.analytics import analytics_service
from app.services.language import language_service
from app.services.agent.supabase_tools import supabase_tools
from app.services.media import media_service
from typing import Dict, Any, List
import json

class AgentTools:
    async def award_loyalty_points(self, phone: str, amount: float, reason: str = "order") -> str:
        """Award loyalty points to a customer."""
        points = await loyalty_service.award_points(phone, amount, reason)
        return json.dumps({"status": "success", "points_awarded": points, "message": f"Awarded {points} points to {phone}"})

    async def check_loyalty_points(self, phone: str) -> str:
        """Check the loyalty points balance for a customer."""
        balance = await loyalty_service.get_points_balance(phone)
        return json.dumps({"points_balance": balance})

    async def get_privacy_policy(self) -> str:
        """Get the privacy policy content."""
        return "Our privacy policy ensures your data is safe. You can request deletion by saying 'delete my data'."

    async def handle_data_deletion(self, phone: str) -> str:
        """Handle a request to delete user data."""
        response = await compliance_service.handle_data_deletion_request(phone)
        return json.dumps({"status": "processing", "message": response})
    
    async def log_complaint(self, phone: str, description: str) -> str:
        """Log a customer complaint."""
        # Resolve contact_id
        contact = await loyalty_service._get_or_create_contact(phone)
        contact_id = contact['id'] if contact else None
        
        if contact_id:
            await analytics_service.track_interaction(contact_id, "complaint", {"description": description})
            return json.dumps({"status": "logged", "message": "Complaint has been logged and will be reviewed."})
        return json.dumps({"status": "error", "message": "Could not identify customer."})
    
    async def get_products(self, category: str = None) -> str:
        """Fetch available products from Airtable inventory."""
        # This assumes there is an Airtable table named 'Products'
        from app.services.airtable import airtable_service
        formula = f"{{Category}} = '{category}'" if category else None
        records = await airtable_service.get_records("Products", formula)
        
        # Simplify output for LLM
        products = [{"name": r["fields"].get("Name"), "price": r["fields"].get("Price"), "stock": r["fields"].get("Stock")} for r in records]
        return json.dumps({"products": products})

    async def create_order(self, phone: str, items: List[str], total_amount: float) -> str:
        """Create a new order for the customer."""
        # For now, this is a placeholder as per existing code
        await loyalty_service.award_points(phone, total_amount, "purchase")
        return json.dumps({"status": "created", "order_id": "ORD-12345", "message": "Order created successfully. Points awarded."})

    async def intent_classifier(self, text: str, context: Dict[str, Any] = None) -> str:
        """Classify the intent of the user message."""
        from app.services.intent import intent_service
        result = await intent_service.identify_intent(text, context)
        return json.dumps(result)

    async def extract_order_details(self, text: str, menu: List[Any] = None) -> str:
        """Extract structured order details from text."""
        # We can usage Meta AI directly or regex. Since Agent call is expensive, maybe regex for simple?
        # But for robustness, let's assume we return a structured pending object.
        # For now, simple mock or heuristic. The Agent itself is an LLM, asking it to call another LLM tool is funny.
        # But following instructions:
        from app.services.meta_ai import meta_ai_service
        prompt = f"Extract items, qty, and delivery from: '{text}'. Return JSON: {{'items':[], 'delivery':{{}}}}"
        try:
             res = await meta_ai_service.chat_completion(prompt)
             # Extract JSON from res
             if "{" in res:
                 return res[res.find("{"):res.rfind("}")+1]
             return json.dumps({"items": [], "error": "parsing_failed"})
        except:
             return json.dumps({"items": []})
             
    async def check_message_logs(self, phone: str, limit: int = 10) -> str:
        """Fetch recent message logs for a specific user to debugging or monitoring."""
        # Using Supabase directly here would be ideal, or via analytics service.
        # Assuming analytics_service or direct supabase client.
        from app.db.supabase_client import supabase
        try:
            # We need to find contact_id first or just search by phone if we joined, but schema uses contact_id.
            # Let's try to query message_logs via contact ID or if message_logs has phone? Schema says user_id/contact_id.
            # Let's usage loyalty service to finding contact id.
            contact = await loyalty_service._get_or_create_contact(phone)
            if not contact:
                return json.dumps({"status": "error", "message": "Contact not found"})
                
            contact_id = contact['id']
            res = supabase.table("message_logs").select("*").eq("contact_id", contact_id).order("created_at", desc=True).limit(limit).execute()
            
            logs = res.data if res.data else []
            return json.dumps({"logs": logs, "count": len(logs)})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    # Supabase Tools (Direct Database Access)
    async def db_create_contact(self, phone: str, business_id: str, name: str = None, language: str = "en") -> str:
        """Save contact to database"""
        return await supabase_tools.create_contact(phone, business_id, name, language)
    
    async def db_get_contact(self, phone: str, business_id: str) -> str:
        """Get contact from database"""
        return await supabase_tools.get_contact(phone, business_id)
    
    async def db_create_order(self, phone: str, business_id: str, items: List[dict], total: float, delivery_type: str = "pickup") -> str:
        """Create order in database"""
        return await supabase_tools.create_order(phone, business_id, items, total, delivery_type)
    
    async def db_get_orders(self, phone: str, business_id: str) -> str:
        """Get customer orders from database"""
        return await supabase_tools.get_orders(phone, business_id)
    
    async def db_add_loyalty_points(self, phone: str, business_id: str, points: int) -> str:
        """Add loyalty points in database"""
        return await supabase_tools.add_loyalty_points(phone, business_id, points)
    
    async def db_get_loyalty_points(self, phone: str, business_id: str) -> str:
        """Get loyalty points from database"""
        return await supabase_tools.get_loyalty_points(phone, business_id)
    
    async def db_save_feedback(self, phone: str, business_id: str, order_id: int, rating: int, comment: str = None) -> str:
        """Save feedback to database"""
        return await supabase_tools.save_feedback(phone, business_id, order_id, rating, comment)
    
    async def db_get_inventory(self, business_id: str) -> str:
        """Get business inventory from database"""
        return await supabase_tools.get_business_inventory(business_id)
    
    async def send_product_with_image(self, phone: str, product_name: str, business_id: str, channel: str = "whatsapp") -> str:
        """Send product details with image to customer"""
        try:
            # Get inventory
            inventory_result = await supabase_tools.get_business_inventory(business_id)
            inventory_data = json.loads(inventory_result)
            
            if inventory_data.get("status") != "success":
                return json.dumps({"status": "error", "message": "Could not fetch inventory"})
            
            products = inventory_data.get("inventory", [])
            product = next((p for p in products if p["name"].lower() == product_name.lower()), None)
            
            if not product:
                return json.dumps({"status": "error", "message": f"Product '{product_name}' not found"})
            
            product_info = {
                "name": product.get("name"),
                "price": product.get("price"),
                "description": product.get("description"),
                "available": product.get("available", True)
            }
            
            media_status = "skipped"
            if channel.lower() in {"whatsapp", "sms"}:
                try:
                    await media_service.send_product_image(phone, product)
                    media_status = "sent"
                except Exception:
                    media_status = "not_sent"
            
            return json.dumps({
                "status": "success",
                "media_status": media_status,
                "product": product_info
            })
            
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    async def send_all_products(self, phone: str, business_id: str, channel: str = "whatsapp") -> str:
        """Send all products with images (one message per product)"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"send_all_products called: phone={phone}, business_id={business_id}")
            
            # Get inventory
            inventory_result = await supabase_tools.get_business_inventory(business_id)
            logger.info(f"Inventory result: {inventory_result}")
            
            inventory_data = json.loads(inventory_result)
            
            if inventory_data.get("status") != "success":
                logger.error(f"Inventory fetch failed: {inventory_data}")
                return json.dumps({"status": "error", "message": "Could not fetch inventory"})
            
            products = inventory_data.get("inventory", [])
            logger.info(f"Found {len(products)} products")
            
            if not products:
                return json.dumps({"status": "error", "message": "No products available"})
            
            summary = [
                {
                    "name": p.get("name"),
                    "price": p.get("price"),
                    "description": p.get("description"),
                    "available": p.get("available", True)
                }
                for p in products
            ]
            
            sent_count = 0
            if channel.lower() in {"whatsapp", "sms"}:
                try:
                    sent_count = await media_service.send_multiple_products(phone, products, channel="twilio")
                except Exception:
                    sent_count = 0
            
            return json.dumps({
                "status": "success",
                "message": f"Shared {len(products)} products",
                "count": len(products),
                "media_sent": sent_count,
                "products": summary
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"send_all_products error: {e}", exc_info=True)
            return json.dumps({"status": "error", "message": str(e)})
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return the JSON schema definitions for the tools."""
        return [
            {
                "name": "db_create_contact",
                "description": "Save customer contact to database with consent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string"},
                        "business_id": {"type": "string"},
                        "name": {"type": "string"},
                        "language": {"type": "string"}
                    },
                    "required": ["phone", "business_id"]
                }
            },
            {
                "name": "db_create_order",
                "description": "Create order in database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string"},
                        "business_id": {"type": "string"},
                        "items": {"type": "array"},
                        "total": {"type": "number"},
                        "delivery_type": {"type": "string"}
                    },
                    "required": ["phone", "business_id", "items", "total"]
                }
            },
            {
                "name": "db_get_orders",
                "description": "Get customer's order history from database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string"},
                        "business_id": {"type": "string"}
                    },
                    "required": ["phone", "business_id"]
                }
            },
            {
                "name": "db_add_loyalty_points",
                "description": "Add loyalty points to customer in database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string"},
                        "business_id": {"type": "string"},
                        "points": {"type": "integer"}
                    },
                    "required": ["phone", "business_id", "points"]
                }
            },
            {
                "name": "db_get_loyalty_points",
                "description": "Get customer's loyalty points from database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string"},
                        "business_id": {"type": "string"}
                    },
                    "required": ["phone", "business_id"]
                }
            },
            {
                "name": "db_save_feedback",
                "description": "Save customer feedback to database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string"},
                        "business_id": {"type": "string"},
                        "order_id": {"type": "integer"},
                        "rating": {"type": "integer"},
                        "comment": {"type": "string"}
                    },
                    "required": ["phone", "business_id", "order_id", "rating"]
                }
            },
            {
                "name": "db_get_inventory",
                "description": "Get business product catalog from database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "business_id": {"type": "string"}
                    },
                    "required": ["business_id"]
                }
            },
            {
                "name": "send_product_with_image",
                "description": "Send a specific product with image, description, and price to customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"},
                        "product_name": {"type": "string", "description": "Name of the product"},
                        "business_id": {"type": "string", "description": "Business ID"},
                        "channel": {"type": "string", "description": "Channel invoking the tool (web, whatsapp, sms)"}
                    },
                    "required": ["phone", "product_name", "business_id"]
                }
            },
            {
                "name": "send_all_products",
                "description": "Send all products with images (one message per product). Use when customer asks for menu or all products.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"},
                        "business_id": {"type": "string", "description": "Business ID"},
                        "channel": {"type": "string", "description": "Channel invoking the tool (web, whatsapp, sms)"}
                    },
                    "required": ["phone", "business_id"]
                }
            },
            {
                "name": "award_loyalty_points",
                "description": "Award loyalty points to a customer for a specific amount spent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"},
                        "amount": {"type": "number", "description": "Amount spent in Naira"},
                        "reason": {"type": "string", "description": "Reason for points (e.g., 'order')"}
                    },
                    "required": ["phone", "amount"]
                }
            },
            {
                "name": "check_loyalty_points",
                "description": "Check the current loyalty points balance of a customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"}
                    },
                    "required": ["phone"]
                }
            },
            {
                "name": "get_products",
                "description": "Get a list of available products, optionally filtered by category.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Optional category to filter by"}
                    }
                }
            },
            {
                "name": "handle_data_deletion",
                "description": "Process a request to delete a customer's data (NDPA compliance).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"}
                    },
                    "required": ["phone"]
                }
            },
            {
                "name": "log_complaint",
                "description": "Log a customer complaint or issue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"},
                        "description": {"type": "string", "description": "Details of the complaint"}
                    },
                    "required": ["phone", "description"]
                }
            },
            {
                "name": "create_order",
                "description": "Create a new order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"},
                        "items": {"type": "array", "items": {"type": "string"}, "description": "List of items ordered"},
                        "total_amount": {"type": "number", "description": "Total cost of the order"}
                    },
                    "required": ["phone", "items", "total_amount"]
                }
            },
            {
                "name": "check_message_logs",
                "description": "Fetch recent message history for a user for debugging.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Customer phone number"},
                        "limit": {"type": "integer", "description": "Number of messages to retrieve (default 10)"}
                    },
                    "required": ["phone"]
                }
            },
            {
                "name": "intent_classifier",
                "description": "Classify the intent of the input text (ORDER, STATUS, FEEDBACK, HELP).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The user message text"},
                        "context": {"type": "object", "description": "Optional context"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "extract_order_details",
                "description": "Extract structured order information from text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The user message text"},
                        "menu": {"type": "array", "description": "Optional menu items to match against"}
                    },
                    "required": ["text"]
                }
            }
        ]
        
agent_tools = AgentTools()
