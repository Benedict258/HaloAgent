from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from app.db.supabase_client import supabase
from datetime import datetime
import logging
from app.api.auth import require_business_user
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[3]
RECEIPT_UPLOAD_DIR = BASE_DIR / "uploads" / "receipts"
RECEIPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class OrderStatusUpdate(BaseModel):
    status: str

class PaymentApproval(BaseModel):
    approved: bool
    notes: str = None


@router.get("/orders/payment-reviews")
async def get_payment_reviews(current_user: dict = Depends(require_business_user)):
    """Return orders waiting for payment confirmation with latest vision analysis."""
    try:
        business_id = current_user["business_id"]
        pending_orders = (
            supabase
            .table("orders")
            .select(
                "id, order_number, total_amount, status, payment_reference, payment_receipt_url, "
                "payment_receipt_uploaded_at, payment_receipt_analysis, updated_at, contacts(name, phone_number)"
            )
            .eq("business_id", business_id)
            .in_("status", ["payment_pending_review", "awaiting_confirmation"])
            .order("updated_at", desc=True)
            .limit(50)
            .execute()
        )

        reviews = pending_orders.data or []
        order_ids = [row.get("id") for row in reviews if row.get("id")]
        vision_map = {}
        if order_ids:
            vision_rows = (
                supabase
                .table("vision_analysis_results")
                .select("id, order_id, analysis_type, media_url, analysis, created_at")
                .in_("order_id", order_ids)
                .eq("analysis_type", "receipt")
                .order("created_at", desc=True)
                .execute()
            )
            for row in vision_rows.data or []:
                order_id = row.get("order_id")
                if order_id and order_id not in vision_map:
                    vision_map[order_id] = row

        for review in reviews:
            review_id = review.get("id")
            review["latest_receipt_analysis"] = vision_map.get(review_id)

        return reviews
    except Exception as e:
        logger.error(f"Get payment reviews error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load payment reviews")

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
        total_text = f"₦{total:,}" if isinstance(total, (int, float)) else str(total)
        order_number = order.data.get("order_number") or str(order_id)
        payment_reference = order.data.get("payment_reference")
        reference_line = f"\nReference: {payment_reference}" if payment_reference else ""
        
        # Send message via AI agent
        phone = order.data["contacts"]["phone_number"]
        
        if approval.approved:
            message = (
                "✅ Great news! Your payment has been confirmed.\n\n"
                f"Order #{order_number}{reference_line}\nItems: {items_text}\nTotal: {total_text}\n\n"
                "We're starting to prepare your order now. You'll get another message when it's ready! 🎂"
            )
        else:
            message = (
                f"❌ We couldn't verify your payment for order #{order_number}{reference_line}. "
                f"{approval.notes or 'Please contact us for assistance.'}"
            )
        
        # Send via Twilio (WhatsApp)
        from app.api.webhooks import send_twilio_message
        await send_twilio_message(phone, message)
        
        return {"success": True, "status": new_status, "message_sent": True}
    except Exception as e:
        logger.error(f"Approve payment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders/{order_id}/upload-receipt")
async def upload_order_receipt(order_id: str, receipt: UploadFile = File(...), current_user: dict = Depends(require_business_user)):
    """Business owner uploads a receipt on behalf of a customer."""
    try:
        try:
            order_pk = int(order_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid order id")

        allowed_types = {"image/jpeg", "image/png", "application/pdf"}
        if receipt.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        suffix = Path(receipt.filename or "").suffix.lower()
        if not suffix:
            suffix = ".pdf" if receipt.content_type == "application/pdf" else ".jpg"
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        filename = f"receipt-{order_pk}-{timestamp}{suffix}"
        file_path = RECEIPT_UPLOAD_DIR / filename
        file_bytes = await receipt.read()
        file_path.write_bytes(file_bytes)

        public_url = f"/uploads/receipts/{filename}"
        business_id = current_user["business_id"]

        update = (
            supabase
            .table("orders")
            .update({
                "payment_receipt_url": public_url,
                "payment_receipt_uploaded_at": datetime.utcnow().isoformat(),
                "payment_notes": "Receipt uploaded via dashboard",
                "status": "payment_pending_review",
                "updated_at": datetime.utcnow().isoformat()
            })
            .eq("id", order_pk)
            .eq("business_id", business_id)
            .execute()
        )

        if not update.data:
            raise HTTPException(status_code=404, detail="Order not found")

        return {"status": "success", "receipt_url": public_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Receipt upload error: {e}")
        raise HTTPException(status_code=500, detail="Unable to upload receipt")

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
        fulfillment_type = (order.data.get("fulfillment_type") or "pickup").lower()
        delivery_address = order.data.get("delivery_address")
        address_line = f"\n📍 Delivery Address: {delivery_address}" if delivery_address else ""

        pickup_messages = {
            "preparing": f"👨‍🍳 Good news! We've started preparing your order.\n\nOrder #{order_id}\nItems: {items_text}\n\nWe'll notify you as soon as it's ready!",
            "ready_for_pickup": f"🎉 Your order is ready for pickup!\n\nOrder #{order_id}\nItems: {items_text}\n\n📍 Pickup Location: [Your Business Address]\n⏰ Hours: 9am - 6pm\n\nSee you soon!",
            "out_for_delivery": f"🚚 Your order #{order_id} is ready for pickup!",  # fallback if status triggered accidentally
            "completed": f"✅ Thank you for your order!\n\nOrder #{order_id} is now complete. We hope you enjoyed {items_text}!\n\nHow was your experience? Reply with a rating (1-5 stars) ⭐"
        }

        delivery_messages = {
            "preparing": f"👨‍🍳 We're preparing your delivery.\n\nOrder #{order_id}\nItems: {items_text}{address_line}\n\nWe'll let you know once it's on the move!",
            "ready_for_pickup": f"🚚 Your order #{order_id} is packed and heading to you{address_line}. We'll keep you posted until it arrives!",
            "out_for_delivery": f"🚚 Your order #{order_id} is on the way{address_line}. It should arrive shortly!",
            "completed": f"✅ Order #{order_id} has been delivered{address_line}. Enjoy your {items_text}! Let us know if everything went well." 
        }

        messages = delivery_messages if fulfillment_type == "delivery" else pickup_messages
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
