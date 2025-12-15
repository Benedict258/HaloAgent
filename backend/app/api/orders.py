from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.supabase_client import supabase
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class OrderStatusUpdate(BaseModel):
    status: str

class PaymentApproval(BaseModel):
    approved: bool
    notes: str = None

@router.get("/orders")
async def get_orders(business_id: str = "sweetcrumbs_001", status: str = None):
    """Get all orders for a business"""
    try:
        query = supabase.table("orders").select("*")
        if status and status != 'all':
            query = query.eq("status", status)
        result = query.order("created_at", desc=True).limit(50).execute()
        
        # Manually fetch contact info for each order
        orders = result.data or []
        for order in orders:
            if order.get('contact_id'):
                contact = supabase.table("contacts").select("name, phone").eq("id", order['contact_id']).single().execute()
                order['contacts'] = contact.data if contact.data else {"name": "Unknown", "phone": "N/A"}
            else:
                order['contacts'] = {"name": "Unknown", "phone": "N/A"}
        
        return orders
    except Exception as e:
        logger.error(f"Get orders error: {e}", exc_info=True)
        return []

@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get single order details"""
    try:
        result = supabase.table("orders").select("*, contacts(name, phone)").eq("id", order_id).single().execute()
        return result.data
    except Exception as e:
        logger.error(f"Get order error: {e}")
        raise HTTPException(status_code=404, detail="Order not found")

@router.post("/orders/{order_id}/approve-payment")
async def approve_payment(order_id: str, approval: PaymentApproval):
    """Owner approves/rejects payment"""
    try:
        # Get order
        order = supabase.table("orders").select("*, contacts(phone)").eq("id", order_id).single().execute()
        if not order.data:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Update order status
        new_status = "paid" if approval.approved else "payment_rejected"
        supabase.table("orders").update({
            "status": new_status,
            "payment_confirmed_at": datetime.utcnow().isoformat() if approval.approved else None,
            "payment_notes": approval.notes
        }).eq("id", order_id).execute()
        
        # Send WhatsApp notification
        from app.services.whatsapp import whatsapp_service
        phone = order.data["contacts"]["phone"]
        
        if approval.approved:
            message = f"✅ Payment confirmed! Your order #{order_id} is now being prepared. We'll notify you when it's ready! 🎂"
        else:
            message = f"❌ Payment verification failed for order #{order_id}. {approval.notes or 'Please contact us.'}"
        
        await whatsapp_service.send_message(phone, message)
        
        return {"success": True, "status": new_status}
    except Exception as e:
        logger.error(f"Approve payment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders/{order_id}/update-status")
async def update_order_status(order_id: str, update: OrderStatusUpdate):
    """Owner updates order status (preparing, ready, completed)"""
    try:
        # Get order
        order = supabase.table("orders").select("*, contacts(phone)").eq("id", order_id).single().execute()
        if not order.data:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Update status
        updates = {"status": update.status}
        if update.status == "ready_for_pickup":
            updates["ready_at"] = datetime.utcnow().isoformat()
        elif update.status == "completed":
            updates["completed_at"] = datetime.utcnow().isoformat()
        
        supabase.table("orders").update(updates).eq("id", order_id).execute()
        
        # Send WhatsApp notification
        from app.services.whatsapp import whatsapp_service
        phone = order.data["contacts"]["phone"]
        
        messages = {
            "preparing": f"👨‍🍳 Your order #{order_id} is being prepared! We'll let you know when it's ready.",
            "ready_for_pickup": f"🎉 Great news! Your order #{order_id} is ready for pickup!\n\n📍 Location: [Business Address]\n⏰ Pickup Hours: 9am - 6pm\n\nReply 'PICKED UP' when you collect it.",
            "out_for_delivery": f"🚚 Your order #{order_id} is out for delivery! It should arrive soon.",
            "completed": f"✅ Order #{order_id} completed! Thank you for your business. How was your experience? (Reply with 1-5 stars)"
        }
        
        message = messages.get(update.status, f"Order #{order_id} status updated to {update.status}")
        await whatsapp_service.send_message(phone, message)
        
        # Award loyalty points on completion
        if update.status == "completed":
            contact_id = order.data["contact_id"]
            total = order.data["total_amount"]
            points = int(total / 100)  # 1 point per ₦100
            
            supabase.table("contacts").update({
                "loyalty_points": supabase.table("contacts").select("loyalty_points").eq("id", contact_id).single().execute().data["loyalty_points"] + points
            }).eq("id", contact_id).execute()
        
        return {"success": True, "status": update.status}
    except Exception as e:
        logger.error(f"Update status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
