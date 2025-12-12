from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.auth import get_current_user
from app.models.user import User
from app.db.base import get_db
from sqlalchemy.orm import Session

router = APIRouter()

class WhatsAppSetup(BaseModel):
    phone_number_id: str
    business_account_id: str
    access_token: str
    verify_token: str

@router.post("/setup-whatsapp")
async def setup_whatsapp_business(
    setup_data: WhatsAppSetup,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Configure WhatsApp Business API for this business"""
    
    # Update user's WhatsApp credentials
    current_user.whatsapp_phone_number_id = setup_data.phone_number_id
    current_user.whatsapp_business_account_id = setup_data.business_account_id
    current_user.whatsapp_access_token = setup_data.access_token
    current_user.whatsapp_webhook_verify_token = setup_data.verify_token
    
    db.commit()
    
    return {
        "message": "WhatsApp Business integration configured successfully",
        "webhook_url": f"https://haloagent.onrender.com/webhooks/whatsapp",
        "verify_token": setup_data.verify_token,
        "phone_number_id": setup_data.phone_number_id
    }

@router.get("/whatsapp-status")
async def get_whatsapp_status(current_user: User = Depends(get_current_user)):
    """Check WhatsApp Business integration status"""
    
    is_configured = bool(
        current_user.whatsapp_phone_number_id and 
        current_user.whatsapp_access_token
    )
    
    return {
        "is_configured": is_configured,
        "phone_number_id": current_user.whatsapp_phone_number_id,
        "business_account_id": current_user.whatsapp_business_account_id,
        "webhook_url": "https://haloagent.onrender.com/webhooks/whatsapp",
        "verify_token": current_user.whatsapp_webhook_verify_token
    }