from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from app.db.supabase_client import supabase
import logging
import json
from app.api.auth import require_business_user

router = APIRouter()
logger = logging.getLogger(__name__)

class IdentifyContact(BaseModel):
    phone: str
    business_id: str = "sweetcrumbs_001"

@router.get("/contacts")
async def get_contacts(current_user: dict = Depends(require_business_user)):
    """Get all contacts/customers for a business"""
    try:
        business_id = current_user["business_id"]
        result = supabase.table("contacts").select("*").eq("business_id", business_id).order("created_at", desc=True).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Get contacts error: {e}")
        return []

@router.post("/contacts/identify")
async def identify_contact(data: IdentifyContact):
    """Identify or create contact by phone number"""
    try:
        # Check if contact exists
        result = supabase.table("contacts").select("*").eq("phone_number", data.phone).eq("business_id", data.business_id).execute()
        
        if result.data:
            return {"status": "found", "contact": result.data[0]}
        
        # Create new contact
        new_contact = {
            "phone_number": data.phone,
            "business_id": data.business_id,
            "opt_in": False,
            "status": "active"
        }
        
        create_result = supabase.table("contacts").insert(new_contact).execute()
        return {"status": "created", "contact": create_result.data[0] if create_result.data else None}
    
    except Exception as e:
        logger.error(f"Identify contact error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contacts/orders")
async def get_contact_orders(phone: str = Query(...), business_id: str = Query("sweetcrumbs_001")):
    """Get all orders for a contact by phone number"""
    try:
        # Find contact
        contact = (
            supabase
            .table("contacts")
            .select("id")
            .eq("phone_number", phone)
            .eq("business_id", business_id)
            .limit(1)
            .execute()
        )
        if not contact.data:
            return []
        
        # Get orders
        contact_id = contact.data[0]["id"]
        result = (
            supabase
            .table("orders")
            .select("*")
            .eq("contact_id", contact_id)
            .order("created_at", desc=True)
            .execute()
        )
        orders = result.data or []
        
        # Parse items
        for order in orders:
            if isinstance(order.get('items'), str):
                try:
                    order['items'] = json.loads(order['items'])
                except:
                    order['items'] = []
        
        return orders
    except Exception as e:
        logger.error(f"Get contact orders error: {e}")
        return []

@router.get("/contacts/notifications")
async def get_contact_notifications(phone: str = Query(...), business_id: str = Query("sweetcrumbs_001")):
    """Return user-facing notifications derived from their order activity."""
    try:
        contact = (
            supabase
            .table("contacts")
            .select("id")
            .eq("phone_number", phone)
            .eq("business_id", business_id)
            .single()
            .execute()
        )
        if not contact.data:
            return []

        orders_result = (
            supabase
            .table("orders")
            .select("id, order_number, status, total_amount, fulfillment_type, created_at, updated_at, payment_confirmed_at, ready_at, completed_at")
            .eq("contact_id", contact.data["id"])
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        status_copy = {
            "pending_payment": "We're waiting for payment so we can start your order.",
            "payment_pending_review": "Thanks for paying! The team is confirming your transfer.",
            "paid": "Payment confirmed. We're about to start prepping your order.",
            "preparing": "Your order is being prepared right now.",
            "ready_for_pickup": "Your order is ready for pickup!",
            "out_for_delivery": "Your order is on the way!",
            "completed": "Thanks again! Your order is complete.",
            "cancelled": "This order was cancelled. Reach out if that's unexpected.",
            "awaiting_confirmation": "Thanks for paying! The team is confirming your transfer.",
        }

        notifications = []
        for order in orders_result.data or []:
            order_id = order.get("id")
            order_number = order.get("order_number") or order_id
            total = order.get("total_amount")
            created_at = order.get("created_at")

            notifications.append({
                "id": f"{order_id}-created",
                "order_id": order_id,
                "order_number": order_number,
                "status": "pending_payment",
                "message": f"You started order #{order_number}. We'll send payment details right away.",
                "total_amount": total,
                "fulfillment_type": order.get("fulfillment_type"),
                "created_at": created_at,
                "type": "order_started",
            })

            status = order.get("status")
            if status:
                if status == "completed":
                    status_ts = order.get("completed_at") or order.get("updated_at") or created_at
                elif status == "ready_for_pickup":
                    status_ts = order.get("ready_at") or order.get("updated_at") or created_at
                elif status in {"paid"}:
                    status_ts = order.get("payment_confirmed_at") or order.get("updated_at") or created_at
                else:
                    status_ts = order.get("updated_at") or created_at

                notifications.append({
                    "id": f"{order_id}-{status}",
                    "order_id": order_id,
                    "order_number": order_number,
                    "status": status,
                    "message": status_copy.get(status, f"Update on order #{order_number}"),
                    "total_amount": total,
                    "fulfillment_type": order.get("fulfillment_type"),
                    "created_at": status_ts,
                    "type": "order_status",
                })

        notifications.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return notifications
    except Exception as e:
        logger.error(f"Get contact notifications error: {e}")
        return []

@router.get("/contacts/{phone}")
async def get_contact(phone: str, current_user: dict = Depends(require_business_user)):
    """Get specific contact by phone"""
    try:
        business_id = current_user["business_id"]
        result = supabase.table("contacts").select("*").eq("phone_number", phone).eq("business_id", business_id).single().execute()
        return result.data
    except Exception as e:
        logger.error(f"Get contact error: {e}")
        raise HTTPException(status_code=404, detail="Contact not found")
