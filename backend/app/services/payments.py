import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


class PaymentService:
    async def mark_payment_pending_review(
        self,
        *,
        business_id: str,
        contact_phone: str,
        order_id: Optional[int] = None,
        receipt_url: Optional[str] = None,
        note: Optional[str] = None,
        receipt_analysis: Optional[Dict[str, Any]] = None,
        payment_method: str = "bank_transfer",
    ) -> Optional[Dict[str, Any]]:
        """Attach receipt + move most recent pending order to payment_pending_review."""
        try:
            contact = (
                supabase
                .table("contacts")
                .select("id")
                .eq("phone_number", contact_phone)
                .eq("business_id", business_id)
                .single()
                .execute()
            )
            if not contact.data:
                logger.info("No contact for %s/%s", business_id, contact_phone)
                return None
            contact_id = contact.data["id"]

            target_order = None
            if order_id:
                result = (
                    supabase
                    .table("orders")
                    .select("id, order_number, status, payment_reference")
                    .eq("id", order_id)
                    .eq("contact_id", contact_id)
                    .single()
                    .execute()
                )
                target_order = result.data if result.data else None
            else:
                orders = (
                    supabase
                    .table("orders")
                    .select("id, order_number, status, payment_reference")
                    .eq("contact_id", contact_id)
                    .order("created_at", desc=True)
                    .limit(5)
                    .execute()
                )
                allowed_statuses = {"pending_payment", "payment_pending_review", "awaiting_confirmation"}
                for row in orders.data or []:
                    if row.get("status") in allowed_statuses:
                        target_order = row
                        break

            if not target_order:
                logger.info("No pending order to mark for %s/%s", business_id, contact_phone)
                return None

            update_payload = {
                "status": "payment_pending_review",
                "payment_method": payment_method,
                "payment_notes": note,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if receipt_url:
                update_payload["payment_receipt_url"] = receipt_url
                update_payload["payment_receipt_uploaded_at"] = datetime.utcnow().isoformat()
            if receipt_analysis is not None:
                update_payload["payment_receipt_analysis"] = receipt_analysis

            supabase.table("orders").update(update_payload).eq("id", target_order["id"]).execute()

            return {
                "order_id": target_order["id"],
                "order_number": target_order.get("order_number"),
                "payment_reference": target_order.get("payment_reference"),
                "contact_id": contact_id,
            }
        except Exception as exc:
            logger.error("Failed to mark payment pending review: %s", exc, exc_info=True)
            return None


payment_service = PaymentService()
