from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.db.supabase_client import supabase
from datetime import datetime
import logging
from typing import List
from app.api.auth import require_business_user

router = APIRouter()
logger = logging.getLogger(__name__)

class PaymentNotification(BaseModel):
    order_id: int
    contact_phone: str
    payment_method: str = "bank_transfer"
    receipt_url: str = None
    notes: str = None


class NotificationReadItem(BaseModel):
    notification_type: str
    entity_id: int


class MarkNotificationsRead(BaseModel):
    business_id: str = "sweetcrumbs_001"
    notifications: List[NotificationReadItem]

@router.post("/orders/{order_id}/notify-payment")
async def notify_payment(order_id: int, data: PaymentNotification):
    """Customer notifies they have paid - moves order to awaiting_confirmation"""
    try:
        # Update order status
        update_data = {
            "status": "awaiting_confirmation",
            "payment_method": data.payment_method,
            "payment_receipt_url": data.receipt_url,
            "payment_notes": data.notes,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("orders").update(update_data).eq("id", order_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Send notification to owner (you can implement push notification here)
        logger.info(f"Payment notification for order {order_id} - pending owner review")
        
        return {
            "status": "success",
            "message": "Payment notification sent to business owner",
            "order_status": "awaiting_confirmation"
        }
    
    except Exception as e:
        logger.error(f"Notify payment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _notification_id(notification_type: str, entity_id: int) -> str:
    return f"{notification_type}:{entity_id}"


@router.get("/notifications")
async def get_notifications(current_user: dict = Depends(require_business_user)):
    """Get notifications for business owner (payments, new orders, feedback)"""
    try:
        business_id = current_user["business_id"]
        notifications = []
        read_map = set()

        try:
            read_result = (
                supabase.table("notification_reads")
                .select("notification_type, entity_id")
                .eq("business_id", business_id)
                .execute()
            )
            read_map = {
                _notification_id(row["notification_type"], row["entity_id"])
                for row in read_result.data or []
            }
        except Exception:
            # Table might not exist yet on new environments
            logger.debug("notification_reads table not found yet")

        def append_notification(payload: dict):
            payload["read"] = payload["id"] in read_map
            notifications.append(payload)

        # Pending payment confirmations
        payment_orders = (
            supabase.table("orders")
            .select(
                "id, order_number, status, total_amount, payment_receipt_url, payment_reference, delivery_address, payment_notes, updated_at, created_at, "
                "contacts(name, phone_number, user_id, users(first_name))"
            )
            .eq("business_id", business_id)
            .in_("status", ["payment_pending_review", "awaiting_confirmation", "payment_rejected"])
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        for order in payment_orders.data or []:
            notif_id = _notification_id("payment_confirmation", order["id"])
            contact = order.get("contacts") or {}
            user_profile = contact.get("users") or {}
            profile_name = (user_profile.get("first_name") or "").strip() if user_profile else ""
            contact_name = contact.get("name") or profile_name or contact.get("phone_number") or "Customer"
            reference = order.get("payment_reference")
            receipt_url = order.get("payment_receipt_url")
            append_notification({
                "id": notif_id,
                "entity_id": order["id"],
                "type": "payment_confirmation",
                "category": "payments",
                "title": "Payment awaiting approval",
                "message": (
                    f"{contact_name} paid order #{order.get('order_number') or order['id']}"
                    + (f" · Ref: {reference}" if reference else "")
                ),
                "order_id": order["id"],
                "amount": order.get("total_amount"),
                "receipt_url": receipt_url,
                "reference": reference,
                "contact_phone": contact.get("phone_number"),
                "delivery_address": order.get("delivery_address"),
                "status": order.get("status"),
                "notes": order.get("payment_notes"),
                "updated_at": order.get("updated_at"),
                "created_at": order.get("created_at"),
            })

        # New orders awaiting payment
        new_orders = (
            supabase.table("orders")
            .select("id, order_number, status, total_amount, created_at, contacts(name, phone_number)")
            .eq("business_id", business_id)
            .eq("status", "pending_payment")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        for order in new_orders.data or []:
            notif_id = _notification_id("new_order", order["id"])
            contact = order.get("contacts") or {}
            append_notification({
                "id": notif_id,
                "entity_id": order["id"],
                "type": "new_order",
                "category": "orders",
                "title": "New order received",
                "message": f"{contact.get('name') or 'Customer'} started order #{order.get('order_number') or order['id']}",
                "order_id": order["id"],
                "amount": order.get("total_amount"),
                "created_at": order.get("created_at"),
            })

        # Feedback / complaints
        feedback_result = (
            supabase.table("feedback")
            .select("id, order_id, rating, comment, created_at, contacts!inner(name, phone_number, business_id)")
            .eq("contacts.business_id", business_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        for feedback in feedback_result.data or []:
            if feedback.get("resolved") or feedback.get("resolved_flag"):
                continue
            notif_id = _notification_id("feedback", feedback["id"])
            contact = feedback.get("contacts") or {}
            append_notification({
                "id": notif_id,
                "entity_id": feedback["id"],
                "type": "feedback",
                "category": "feedback",
                "title": "New feedback received" if feedback.get("rating", 0) >= 3 else "Complaint reported",
                "message": feedback.get("comment") or "Customer left feedback",
                "order_id": feedback.get("order_id"),
                "rating": feedback.get("rating"),
                "contact_name": contact.get("name"),
                "created_at": feedback.get("created_at"),
            })

        notifications.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return notifications

    except Exception as e:
        logger.error(f"Get notifications error: {e}", exc_info=True)
        return []


@router.post("/notifications/read")
async def mark_notifications_read(payload: MarkNotificationsRead, current_user: dict = Depends(require_business_user)):
    """Mark notifications as read for a business"""
    try:
        if not payload.notifications:
            return {"status": "success", "updated": 0}
        business_id = current_user["business_id"]

        rows = [
            {
                "business_id": business_id,
                "notification_type": item.notification_type,
                "entity_id": item.entity_id,
                "read_at": datetime.utcnow().isoformat(),
            }
            for item in payload.notifications
        ]

        supabase.table("notification_reads").upsert(
            rows,
            on_conflict="business_id,notification_type,entity_id",
        ).execute()

        return {"status": "success", "updated": len(rows)}
    except Exception as e:
        logger.error(f"Mark notifications read error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
