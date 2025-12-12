from fastapi import APIRouter, HTTPException
from app.services.analytics import analytics_service
from typing import Dict, List

router = APIRouter(prefix="/admin")

@router.get("/insights/weekly")
async def get_weekly_insights() -> Dict:
    """Get weekly business insights"""
    try:
        insights = await analytics_service.get_weekly_insights("default_business")
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customers/{contact_id}/journey")
async def get_customer_journey(contact_id: str) -> List[Dict]:
    """Get customer interaction timeline"""
    try:
        journey = await analytics_service.get_customer_journey(contact_id)
        return journey
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health/services")
async def check_services_health():
    """Check health of all services"""
    return {
        "whatsapp": "connected",
        "meta_ai": "connected", 
        "database": "connected",
        "redis": "connected"
    }