from datetime import datetime, timedelta
from typing import Optional

class LoyaltyService:
    def __init__(self):
        self.points_per_naira = 1  # 1 point per ₦1 spent
        self.welcome_bonus = 100
        self.referral_bonus = 500
        
    async def award_points(self, contact_id: str, amount: float, reason: str = "purchase") -> int:
        """Award loyalty points to customer"""
        points = int(amount * self.points_per_naira)
        
        # TODO: Save to database
        # reward = Reward(
        #     contact_id=contact_id,
        #     points=points,
        #     reason=reason,
        #     created_at=datetime.utcnow()
        # )
        
        return points
    
    async def get_points_balance(self, contact_id: str) -> int:
        """Get customer's current points balance"""
        # TODO: Query database
        return 0
    
    async def redeem_points(self, contact_id: str, points: int) -> bool:
        """Redeem points for rewards"""
        balance = await self.get_points_balance(contact_id)
        
        if balance >= points:
            # TODO: Update database
            return True
        return False
    
    def calculate_tier(self, total_spent: float) -> str:
        """Calculate customer tier based on spending"""
        if total_spent >= 100000:  # ₦100k
            return "Gold"
        elif total_spent >= 50000:  # ₦50k
            return "Silver"
        else:
            return "Bronze"

loyalty_service = LoyaltyService()