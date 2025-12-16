import re
import secrets
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.core.config import settings
from app.db.supabase_client import get_supabase

router = APIRouter()

DEFAULT_LANGUAGES = ["en", "yo", "ha", "ig"]
WEBHOOK_URL = "https://haloagent.onrender.com/webhooks/whatsapp"


class BusinessHours(BaseModel):
    mon: Optional[Dict[str, str]] = None
    tue: Optional[Dict[str, str]] = None
    wed: Optional[Dict[str, str]] = None
    thu: Optional[Dict[str, str]] = None
    fri: Optional[Dict[str, str]] = None
    sat: Optional[Dict[str, str]] = None
    sun: Optional[Dict[str, str]] = None


class BusinessProfileInput(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=600)
    whatsapp_number: str = Field(..., min_length=8, max_length=24)
    default_language: str = Field("en", min_length=2, max_length=5)
    supported_languages: List[str] = Field(default_factory=lambda: DEFAULT_LANGUAGES.copy())
    business_hours: Optional[BusinessHours] = None
    tone: Optional[str] = Field(None, max_length=240)
    website: Optional[str] = Field(None, max_length=200)
    instagram: Optional[str] = Field(None, max_length=200)
    sample_messages: List[str] = Field(default_factory=list)
    integrations: Optional[Dict[str, Any]] = Field(default_factory=dict)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or f"biz-{secrets.token_hex(2)}"


def _generate_sandbox_code(existing: Optional[str]) -> str:
    if existing:
        return existing
    return f"JOIN-HALO-{secrets.token_hex(2).upper()}"


async def _require_business_account(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("account_type") != "business":
        raise HTTPException(status_code=403, detail="Business account required")
    return current_user


@router.post("/businesses")
async def save_business_profile(payload: BusinessProfileInput, current_user: dict = Depends(_require_business_account)):
    supabase = get_supabase()
    business_id = current_user.get("business_id") or _slugify(payload.business_name)

    supported_languages = payload.supported_languages or DEFAULT_LANGUAGES
    if payload.default_language not in supported_languages:
        supported_languages = [payload.default_language, *[lang for lang in supported_languages if lang != payload.default_language]]

    profile_settings: Dict[str, Any] = {
        "tone": payload.tone,
        "website": payload.website,
        "instagram": payload.instagram,
        "sample_messages": [msg for msg in payload.sample_messages if msg.strip()],
    }

    integration_preferences = {
        "website": payload.website,
        "instagram": payload.instagram,
        "channels": payload.integrations or {}
    }

    business_record = {
        "business_id": business_id,
        "business_name": payload.business_name,
        "description": payload.description,
        "whatsapp_number": payload.whatsapp_number,
        "default_language": payload.default_language,
        "supported_languages": supported_languages,
        "business_hours": payload.business_hours.dict() if payload.business_hours else None,
        "brand_voice": payload.tone,
        "settings": profile_settings,
        "integration_preferences": integration_preferences,
        "webhook_url": WEBHOOK_URL,
    }

    # Fetch existing record (if any)
    existing = supabase.table("businesses").select("business_id,sandbox_code").eq("business_id", business_id).execute()
    sandbox_code = _generate_sandbox_code(existing.data[0]["sandbox_code"]) if existing.data else _generate_sandbox_code(None)
    business_record["sandbox_code"] = sandbox_code

    try:
        if existing.data:
            supabase.table("businesses").update(business_record).eq("business_id", business_id).execute()
        else:
            business_record["owner_user_id"] = current_user["id"]
            supabase.table("businesses").insert(business_record).execute()
            supabase.table("users").update({"business_id": business_id, "business_name": payload.business_name}).eq("id", current_user["id"]).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to save business profile: {exc}") from exc

    response = {
        "business_id": business_id,
        "webhook_url": WEBHOOK_URL,
        "verify_token": settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN,
        "sandbox_code": sandbox_code,
        "supported_languages": supported_languages,
        "message": "Business profile saved successfully.",
        "next_steps": [
            "Point your WhatsApp Business webhook to the HaloAgent URL.",
            "Upload or sync your inventory so the AI can quote accurate prices.",
            "Send a test message from WhatsApp, Twilio, or the Halo web chat to confirm responses.",
        ],
    }
    return response
