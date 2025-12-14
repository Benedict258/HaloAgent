from datetime import datetime
from typing import Dict, Any, Optional
from app.db.supabase_client import supabase
from app.services.loyalty import loyalty_service
import logging

logger = logging.getLogger(__name__)

class StateService:
    async def get_state(self, phone: str) -> Dict[str, Any]:
        """
        Retrieve customer state including contact_id, stage, intent, and context.
        Ensures contact exists using loyalty_service logic.
        """
        # 1. Get/Create Contact (Standard CRM Entry)
        contact = await loyalty_service._get_or_create_contact(phone)
        if not contact:
            # Should not happen ideally
            return {}
            
        return {
            "contact_id": contact["id"],
            "phone": contact["phone_number"],
            "current_stage": contact.get("current_stage", "NONE"),
            "last_intent": contact.get("last_intent", "UNKNOWN"),
            "context_data": contact.get("context_data", {}) or {},
            "opt_in": contact["consent_given"],
            "updated_at": contact.get("updated_at")
        }

    async def update_state(self, phone: str, updates: Dict[str, Any]):
        """
        Update specific state fields for a customer (e.g. stage, intent, context).
        """
        try:
            # We update by phone for simplicity as we know phone is unique in contacts
            # but ideally we usage contact_id if we have it. 
            # Given flow, we might have just phone.
            data = {
                "updated_at": datetime.utcnow().isoformat(),
                **updates
            }
            
            # Remove keys that are not columns if mixed
            # Allow: current_stage, last_intent, context_data, consent_given
            valid_cols = ["current_stage", "last_intent", "context_data", "consent_given", "updated_at"]
            filtered_data = {k: v for k, v in data.items() if k in valid_cols}
            
            if filtered_data:
                supabase.table("contacts").update(filtered_data).eq("phone_number", phone).execute()
                
        except Exception as e:
            logger.error(f"Failed to update state for {phone}: {e}")

state_service = StateService()
