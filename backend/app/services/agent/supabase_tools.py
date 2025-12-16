"""
Supabase-connected tools for AI Agent
Agent can read/write directly to database
"""
from app.db.supabase_client import supabase
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class SupabaseTools:
    
    async def create_contact(self, phone: str, business_id: str, name: str = None, language: str = "en") -> str:
        """Create or update contact in Supabase"""
        try:
            contact_data = {
                "phone_number": phone,
                "business_id": business_id,
                "name": name,
                "language": language,
                "opt_in": True,
                "status": "active",
                "consent_timestamp": datetime.utcnow().isoformat(),
                "loyalty_points": 0,
                "order_count": 0
            }
            
            # Upsert (insert or update)
            result = supabase.table("contacts").upsert(contact_data, on_conflict="phone_number,business_id").execute()
            
            return json.dumps({"status": "success", "message": f"Contact {phone} saved", "data": result.data})
        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            return json.dumps({"status": "error", "message": str(e)})
    
    async def get_contact(self, phone: str, business_id: str) -> str:
        """Get contact details from Supabase"""
        try:
            result = supabase.table("contacts").select("*").eq("phone_number", phone).eq("business_id", business_id).execute()
            
            if result.data:
                return json.dumps({"status": "success", "contact": result.data[0]})
            return json.dumps({"status": "not_found", "message": "Contact not found"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    async def create_order(self, phone: str, business_id: str, items: list, total: float, delivery_type: str = "pickup") -> str:
        """Create order in Supabase"""
        try:
            # Get contact first
            contact_result = supabase.table("contacts").select("id").eq("phone_number", phone).eq("business_id", business_id).execute()
            
            if not contact_result.data:
                return json.dumps({"status": "error", "message": "Contact not found"})
            
            contact_id = contact_result.data[0]["id"]
            
            # Generate order number
            import random
            order_number = f"ORD-{random.randint(1000, 9999)}"
            
            order_data = {
                "contact_id": contact_id,
                "business_id": business_id,
                "order_number": order_number,
                "items": items,
                "total_amount": total,
                "status": "pending_payment",
                "fulfillment_type": delivery_type,
                "channel": "whatsapp",
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = supabase.table("orders").insert(order_data).execute()
            
            # Increment order count
            supabase.table("contacts").update({
                "order_count": supabase.rpc("increment", {"x": 1})
            }).eq("id", contact_id).execute()
            
            return json.dumps({
                "status": "success",
                "message": "Order created",
                "order_id": result.data[0]["id"] if result.data else None,
                "total": total
            })
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return json.dumps({"status": "error", "message": str(e)})
    
    async def get_orders(self, phone: str, business_id: str, limit: int = 5) -> str:
        """Get customer's recent orders"""
        try:
            contact_result = supabase.table("contacts").select("id").eq("phone_number", phone).eq("business_id", business_id).execute()
            
            if not contact_result.data:
                return json.dumps({"status": "error", "message": "Contact not found"})
            
            contact_id = contact_result.data[0]["id"]
            
            result = supabase.table("orders").select("*").eq("contact_id", contact_id).order("created_at", desc=True).limit(limit).execute()
            
            return json.dumps({"status": "success", "orders": result.data})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    async def update_order_status(self, order_id: int, status: str) -> str:
        """Update order status"""
        try:
            result = supabase.table("orders").update({"status": status}).eq("id", order_id).execute()
            return json.dumps({"status": "success", "message": f"Order {order_id} updated to {status}"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    async def add_loyalty_points(self, phone: str, business_id: str, points: int) -> str:
        """Add loyalty points to contact"""
        try:
            contact_result = supabase.table("contacts").select("id, loyalty_points").eq("phone_number", phone).eq("business_id", business_id).execute()
            
            if not contact_result.data:
                return json.dumps({"status": "error", "message": "Contact not found"})
            
            contact = contact_result.data[0]
            new_points = contact.get("loyalty_points", 0) + points
            
            supabase.table("contacts").update({"loyalty_points": new_points}).eq("id", contact["id"]).execute()
            
            return json.dumps({"status": "success", "message": f"Added {points} points", "total_points": new_points})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    async def get_loyalty_points(self, phone: str, business_id: str) -> str:
        """Get customer's loyalty points"""
        try:
            result = supabase.table("contacts").select("loyalty_points, order_count").eq("phone_number", phone).eq("business_id", business_id).execute()
            
            if result.data:
                return json.dumps({
                    "status": "success",
                    "loyalty_points": result.data[0].get("loyalty_points", 0),
                    "order_count": result.data[0].get("order_count", 0)
                })
            return json.dumps({"status": "not_found", "loyalty_points": 0})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    async def save_feedback(self, phone: str, business_id: str, order_id: int, rating: int, comment: str = None) -> str:
        """Save customer feedback"""
        try:
            contact_result = supabase.table("contacts").select("id").eq("phone_number", phone).eq("business_id", business_id).execute()
            
            if not contact_result.data:
                return json.dumps({"status": "error", "message": "Contact not found"})
            
            feedback_data = {
                "contact_id": contact_result.data[0]["id"],
                "order_id": order_id,
                "rating": rating,
                "comment": comment,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = supabase.table("feedback").insert(feedback_data).execute()
            
            # If rating is low, flag for remediation
            if rating <= 2:
                return json.dumps({
                    "status": "success",
                    "message": "Feedback saved",
                    "action": "remediation_needed",
                    "rating": rating
                })
            
            return json.dumps({"status": "success", "message": "Thank you for your feedback!", "rating": rating})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
    
    async def get_business_inventory(self, business_id: str) -> str:
        """Get business product catalog"""
        try:
            result = supabase.table("businesses").select("inventory").eq("business_id", business_id).execute()
            
            if result.data:
                inventory = result.data[0].get("inventory", [])
                return json.dumps({"status": "success", "inventory": inventory})
            return json.dumps({"status": "error", "message": "Business not found"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

supabase_tools = SupabaseTools()
