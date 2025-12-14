from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.business import business_service
from typing import List, Optional

router = APIRouter()

class BusinessOnboarding(BaseModel):
    business_id: str
    business_name: str
    whatsapp_number: str
    owner_email: Optional[str] = None
    default_language: str = "en"
    supported_languages: List[str] = ["en"]
    inventory: Optional[List[dict]] = None

@router.post("/onboard-business")
async def onboard_business(data: BusinessOnboarding):
    """
    STEP 1: Create demo business
    
    Example:
    {
        "business_id": "sweetcrumbs_001",
        "business_name": "SweetCrumbs Cakes",
        "whatsapp_number": "+14155238886",
        "default_language": "en",
        "supported_languages": ["en", "yo"],
        "inventory": [
            {"name": "Chocolate Cake", "price": 5000, "available": true},
            {"name": "Vanilla Cake", "price": 4500, "available": true}
        ]
    }
    """
    
    # Check if business already exists
    existing = await business_service.get_business_by_whatsapp(data.whatsapp_number)
    if existing:
        raise HTTPException(status_code=400, detail="Business with this WhatsApp number already exists")
    
    business_data = {
        "business_id": data.business_id,
        "business_name": data.business_name,
        "whatsapp_number": data.whatsapp_number,
        "default_language": data.default_language,
        "supported_languages": data.supported_languages,
        "inventory": data.inventory or [],
        "active": True
    }
    
    business = await business_service.create_demo_business(business_data)
    
    if not business:
        raise HTTPException(status_code=500, detail="Failed to create business")
    
    return {
        "success": True,
        "message": f"Business '{data.business_name}' onboarded successfully!",
        "business": business,
        "next_steps": [
            "1. Configure WhatsApp webhook to point to your backend",
            "2. Test by sending a message to the WhatsApp number",
            "3. Customer phone numbers will auto-create as contacts",
            "4. Access dashboard to manage orders and contacts"
        ]
    }

@router.get("/business/{business_id}")
async def get_business(business_id: str):
    """Get business details"""
    business = await business_service.get_business_by_id(business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business

@router.get("/business/{business_id}/inventory")
async def get_inventory(business_id: str):
    """Get business product catalog"""
    inventory = await business_service.get_business_inventory(business_id)
    return {"business_id": business_id, "inventory": inventory}
