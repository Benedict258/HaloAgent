from app.db.supabase_client import supabase
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class BusinessService:
    
    async def get_business_by_whatsapp(self, whatsapp_number: str) -> Optional[Dict]:
        """Resolve business by WhatsApp number (incoming To field)"""
        try:
            res = supabase.table("businesses").select("*").eq("whatsapp_number", whatsapp_number).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching business: {e}")
            return None
    
    async def create_demo_business(self, business_data: Dict) -> Optional[Dict]:
        """Create a demo business for onboarding"""
        try:
            res = supabase.table("businesses").insert(business_data).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            logger.error(f"Error creating business: {e}")
            return None
    
    async def get_business_inventory(self, business_id: str) -> list:
        """Get business product catalog"""
        try:
            business = await self.get_business_by_id(business_id)
            if business and business.get("inventory"):
                return business["inventory"]
            return []
        except Exception as e:
            logger.error(f"Error fetching inventory: {e}")
            return []
    
    async def get_business_by_id(self, business_id: str) -> Optional[Dict]:
        """Get business by business_id"""
        try:
            res = supabase.table("businesses").select("*").eq("business_id", business_id).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching business: {e}")
            return None

business_service = BusinessService()
