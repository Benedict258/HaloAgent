from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.db.supabase_client import supabase
from datetime import datetime
import logging
from app.api.auth import require_business_user

router = APIRouter()
logger = logging.getLogger(__name__)

class OrderStatusUpdate(BaseModel):
    status: str

class PaymentApproval(BaseModel):
    approved: bool
    notes: str = None

@router.get("/orders")
async def get_orders(status: str = None, current_user: dict = Depends(require_business_user)):
    """Get all orders for a business"""
    try:
        business_id = current_user["business_id"]
        query = supabase.table("orders").select("*").eq("business_id", business_id)
        if status and status != 'all':
            query = query.eq("status", status)
        result = query.order("created_at", desc=True).limit(50).execute()
        
        # Manually fetch contact info for each order
        orders = result.data or []
        for order in orders:
            # Parse items if it's a string
            if isinstance(order.get('items'), str):
                import json
                try:
                    order['items'] = json.loads(order['items'])
                except:
                    order['items'] = []
            
            if order.get('contact_id'):
                contact = supabase.table("contacts").select("name, phone_number").eq("id", order['contact_id']).single().execute()
                order['contacts'] = contact.data if contact.data else {"name": "Unknown", "phone_number": "N/A"}
            else:
                order['contacts'] = {"name": "Unknown", "phone_number": "N/A"}
        
        return orders
    except Exception as e:
        logger.error(f"Get orders error: {e}", exc_info=True)
        return []

@router.get("/orders/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(require_business_user)):
    """Get single order details"""
    try:
        business_id = current_user["business_id"]
        result = (
            supabase
            .table("orders")
            .select("*, contacts(name, phone)")
            .eq("id", order_id)
            .eq("business_id", business_id)
            .single()
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error(f"Get order error: {e}")
        raise HTTPException(status_code=404, detail="Order not found")

@router.post("/orders/{order_id}/approve-payment")
async def approve_payment(order_id: str, approval: PaymentApproval, current_user: dict = Depends(require_business_user)):
    """Owner approves/rejects payment - AI sends notification to customer"""
    try:
        business_id = current_user["business_id"]
        # Get order with contact info
        order = (
            supabase
            .table("orders")
            .select("*, contacts(phone_number)")
            .eq("id", order_id)
            .eq("business_id", business_id)
            .single()
            .execute()
        )
        if not order.data:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Update order status
        new_status = "paid" if approval.approved else "payment_rejected"
        supabase.table("orders").update({
            "status": new_status,
            "payment_confirmed_at": datetime.utcnow().isoformat() if approval.approved else None,
            "payment_notes": approval.notes
        }).eq("id", order_id).execute()
        
        # Get order details for message
        items = order.data.get("items", [])
        if isinstance(items, str):
            import json
            items = json.loads(items)
        
        items_text = ", ".join([item["name"] for item in items]) if items else "your order"
        total = order.data.get("total_amount", 0)
        
        # Send message via AI agent
        phone = order.data["contacts"]["phone_number"]
        
        if approval.approved:
            message = f"✅ Great news! Your payment has been confirmed.\n\nOrder #{order_id}\nItems: {items_text}\nTotal: ₦{total:,}\n\nWe're starting to prepare your order now. You'll get another message when it's ready for pickup! 🎂"
        else:
            message = f"❌ We couldn't verify your payment for order #{order_id}. {approval.notes or 'Please contact us for assistance.'}"
        
        # Send via Twilio (WhatsApp)
        from app.api.webhooks import send_twilio_message
        await send_twilio_message(phone, message)
        
        return {"success": True, "status": new_status, "message_sent": True}
    except Exception as e:
        logger.error(f"Approve payment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders/{order_id}/update-status")
async def update_order_status(order_id: str, update: OrderStatusUpdate, current_user: dict = Depends(require_business_user)):
    """Owner updates order status (preparing, ready, completed) - AI notifies customer"""
    try:
        business_id = current_user["business_id"]
        # Get order with contact info
        order = (
            supabase
            .table("orders")
            .select("*, contacts(phone_number)")
            .eq("id", order_id)
            .eq("business_id", business_id)
            .single()
            .execute()
        )
        if not order.data:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Update status
        updates = {"status": update.status}
        if update.status == "ready_for_pickup":
            updates["ready_at"] = datetime.utcnow().isoformat()
        elif update.status == "completed":
            updates["completed_at"] = datetime.utcnow().isoformat()
        
        supabase.table("orders").update(updates).eq("id", order_id).execute()
        
        # Get order details
        items = order.data.get("items", [])
        if isinstance(items, str):
            import json
            items = json.loads(items)
        items_text = ", ".join([item["name"] for item in items]) if items else "your order"
        
        # Send WhatsApp notification via Twilio
        phone = order.data["contacts"]["phone_number"]
        
        messages = {
            "preparing": f"👨‍🍳 Good news! We've started preparing your order.\n\nOrder #{order_id}\nItems: {items_text}\n\nWe'll notify you as soon as it's ready!",
            "ready_for_pickup": f"🎉 Your order is ready for pickup!\n\nOrder #{order_id}\nItems: {items_text}\n\n📍 Pickup Location: [Your Business Address]\n⏰ Hours: 9am - 6pm\n\nSee you soon!",
            "out_for_delivery": f"🚚 Your order #{order_id} is on the way! It should arrive soon.",
            "completed": f"✅ Thank you for your order!\n\nOrder #{order_id} is now complete. We hope you enjoyed {items_text}!\n\nHow was your experience? Reply with a rating (1-5 stars) ⭐"
        }
        
        message = messages.get(update.status, f"Order #{order_id} status: {update.status}")
        
        # Send via Twilio
        from app.api.webhooks import send_twilio_message
        await send_twilio_message(phone, message)
        
        # Award loyalty points on completion
        if update.status == "completed":
            contact_id = order.data["contact_id"]
            total = order.data["total_amount"]
            points = int(total / 100)  # 1 point per ₦100
            
            current_contact = supabase.table("contacts").select("loyalty_points").eq("id", contact_id).single().execute()
            current_points = current_contact.data.get("loyalty_points", 0) if current_contact.data else 0
            
            supabase.table("contacts").update({
                "loyalty_points": current_points + points
            }).eq("id", contact_id).execute()
        
        return {"success": True, "status": update.status, "message_sent": True}
    except Exception as e:
        logger.error(f"Update status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
