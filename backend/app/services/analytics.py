from datetime import datetime, timedelta
from typing import Dict, List
from app.db.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        pass
    
    async def get_weekly_insights(self, business_id: str) -> Dict:
        """Generate weekly business insights"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        try:
            # Fetch interactions from DB
            response = supabase.table("interactions").select("*").gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).execute()
            interactions = response.data
            
            # Simple aggregation logic (can be moved to DB query for performance)
            total_messages = len(interactions)
            complaints = [i for i in interactions if i.get("type") == "complaint"]
            
            insights = {
                "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "total_messages": total_messages,
                "complaints_count": len(complaints),
                "trends": {
                    "volume": "up" if total_messages > 100 else "stable"
                }
            }
            return insights
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {}

    async def track_interaction(self, contact_id: str, interaction_type: str, metadata: Dict = None):
        """Track customer interaction for analytics"""
        try:
            data = {
                "contact_id": contact_id,
                "type": interaction_type,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table("interactions").insert(data).execute()
        except Exception as e:
            logger.error(f"Error tracking interaction: {e}")

    async def get_customer_journey(self, contact_id: str) -> List[Dict]:
        """Get customer interaction timeline"""
        try:
            response = supabase.table("interactions").select("*").eq("contact_id", contact_id).order("created_at", desc=True).limit(20).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting customer journey: {e}")
            return []

analytics_service = AnalyticsService()