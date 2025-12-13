from datetime import datetime, timedelta
from typing import Optional
from app.db.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

class LoyaltyService:
    def __init__(self):
        self.points_per_naira = 1
        self.welcome_bonus = 100
        
    async def _get_or_create_contact(self, phone: str) -> Optional[dict]:
        """Get contact by phone or create if not exists"""
        try:
            # Check existence
            res = supabase.table("contacts").select("*").eq("phone_number", phone).execute()
            if res.data:
                return res.data[0]
            
            # Create new
            new_contact = {
                "phone_number": phone,
                "loyalty_points": 0,
                "created_at": datetime.utcnow().isoformat()
            }
            # We assume user_id is nullable or handled elsewhere, but schema says user_id is FK. 
            # If user_id is mandatory, this might fail unless we have a default user or make it nullable.
            # Setup script says: user_id INTEGER REFERENCES users(id) -- doesn't say NOT NULL?
            # Actually standard Postgres FKs are nullable unless specified NOT NULL. Use 'psql' logic.
            
            res = supabase.table("contacts").insert(new_contact).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting/creating contact: {e}")
            return None

    async def award_points(self, phone: str, amount: float, reason: str = "purchase") -> int:
        """Award loyalty points to customer"""
        points = int(amount * self.points_per_naira)
        contact = await self._get_or_create_contact(phone)
        
        if not contact:
            logger.error(f"Could not resolve contact for phone {phone}")
            return 0
            
        contact_id = contact['id']
        current_points = contact.get('loyalty_points', 0) or 0
        new_balance = current_points + points
        
        try:
            # 1. Update balance
            supabase.table("contacts").update({"loyalty_points": new_balance}).eq("id", contact_id).execute()
            
            # 2. Log reward transaction
            supabase.table("rewards").insert({
                "contact_id": contact_id,
                "reward_type": "earned",
                "points_earned": points,
                "description": reason,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            
            return points
        except Exception as e:
            logger.error(f"Error awarding points: {e}")
            return 0
    
    async def get_points_balance(self, phone: str) -> int:
        """Get customer's current points balance"""
        contact = await self._get_or_create_contact(phone)
        if contact:
            return contact.get('loyalty_points', 0)
        return 0
    
    async def redeem_points(self, phone: str, points: int) -> bool:
        """Redeem points for rewards"""
        contact = await self._get_or_create_contact(phone)
        if not contact:
            return False
            
        contact_id = contact['id']
        balance = contact.get('loyalty_points', 0)
        
        if balance >= points:
            try:
                new_balance = balance - points
                supabase.table("contacts").update({"loyalty_points": new_balance}).eq("id", contact_id).execute()
                
                # Log transaction
                supabase.table("rewards").insert({
                    "contact_id": contact_id,
                    "reward_type": "redeemed",
                    "points_redeemed": points,
                    "description": "redemption",
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
                
                return True
            except Exception as e:
                logger.error(f"Error redeeming points: {e}")
                return False
        return False
    
    def calculate_tier(self, total_spent: float) -> str:
        if total_spent >= 100000:
            return "Gold"
        elif total_spent >= 50000:
            return "Silver"
        else:
            return "Bronze"

loyalty_service = LoyaltyService()