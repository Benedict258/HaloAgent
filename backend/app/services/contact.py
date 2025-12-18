from app.db.supabase_client import supabase
from datetime import datetime
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class ContactService:
    
    async def get_or_create_contact(self, phone: str, business_id: str) -> Optional[Dict]:
        """
        Phone number = Contact ID
        Auto-create contact on first message
        """
        try:
            # Check if contact exists for this business
            res = supabase.table("contacts").select("*").eq("phone_number", phone).eq("business_id", business_id).execute()
            
            if res.data:
                return res.data[0]
            
            # Create new contact (unconsented by default)
            new_contact = {
                "phone_number": phone,
                "business_id": business_id,
                "opt_in": False,
                "status": "unconsented",
                "language": "unknown",
                "loyalty_points": 0,
                "order_count": 0,
                "created_at": datetime.utcnow().isoformat()
            }
            
            res = supabase.table("contacts").insert(new_contact).execute()
            if res.data:
                logger.info(f"Created new contact: {phone} for business: {business_id}")
                return res.data[0]
            
            return None
        except Exception as e:
            logger.error(f"Error in get_or_create_contact: {e}")
            return None

    async def ensure_contact_profile(
        self,
        *,
        phone: str,
        business_id: str,
        name: Optional[str] = None,
    ) -> Optional[Dict]:
        """Create contact if needed and enrich profile with the latest metadata."""
        contact = await self.get_or_create_contact(phone, business_id)
        if not contact:
            return None

        try:
            if name and name.strip():
                normalized = name.strip()
                existing = (contact.get("name") or "").strip()
                if not existing or existing.lower() in {"unknown", phone.lower()}:
                    updated = (
                        supabase
                        .table("contacts")
                        .update({
                            "name": normalized,
                            "updated_at": datetime.utcnow().isoformat(),
                        })
                        .eq("id", contact["id"])
                        .execute()
                    )
                    if updated.data:
                        contact = updated.data[0]
        except Exception as err:
            logger.warning("Unable to enrich contact profile for %s: %s", phone, err)

        return contact
    
    async def update_consent(self, phone: str, business_id: str, opt_in: bool, consent_phrase: str = None) -> bool:
        """Update contact consent status"""
        try:
            update_data = {
                "opt_in": opt_in,
                "status": "active" if opt_in else "opted_out",
                "consent_timestamp": datetime.utcnow().isoformat()
            }
            
            if consent_phrase:
                update_data["consent_phrase"] = consent_phrase
            
            supabase.table("contacts").update(update_data).eq("phone_number", phone).eq("business_id", business_id).execute()
            return True
            
        except Exception as e:
            logger.error(f"Error updating consent: {e}")
            return False
    
    async def update_language(self, phone: str, business_id: str, language: str) -> bool:
        """Update contact language preference"""
        try:
            supabase.table("contacts").update({"language": language}).eq("phone_number", phone).eq("business_id", business_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating language: {e}")
            return False
    
    async def increment_order_count(self, phone: str, business_id: str) -> bool:
        """Increment order count for loyalty tracking"""
        try:
            contact = await self.get_or_create_contact(phone, business_id)
            if contact:
                new_count = contact.get("order_count", 0) + 1
                supabase.table("contacts").update({"order_count": new_count}).eq("id", contact["id"]).execute()
                return True
            return False
        except Exception as e:
            logger.error(f"Error incrementing order count: {e}")
            return False

contact_service = ContactService()
