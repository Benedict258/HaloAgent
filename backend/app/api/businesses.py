import re
import secrets
from datetime import datetime
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


class InventoryItemInput(BaseModel):
    sku: Optional[str] = Field(None, min_length=1, max_length=60)
    name: str = Field(..., min_length=2, max_length=140)
    description: Optional[str] = Field(None, max_length=600)
    price: float = Field(..., ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=5)
    category: Optional[str] = Field(None, max_length=80)
    image_urls: Optional[List[str]] = None
    image_url: Optional[str] = Field(None, max_length=500)
    available_today: Optional[bool] = None
    available: Optional[bool] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=140)
    description: Optional[str] = Field(None, max_length=600)
    price: Optional[float] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=80)
    image_urls: Optional[List[str]] = None
    image_url: Optional[str] = Field(None, max_length=500)
    available_today: Optional[bool] = None
    available: Optional[bool] = None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or f"biz-{secrets.token_hex(2)}"


def _canonical_business_id(value: Optional[str]) -> str:
    if not value:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized


def _generate_sandbox_code(existing: Optional[str]) -> str:
    if existing:
        return existing
    return f"JOINHALO{secrets.token_hex(2).upper()}"


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

    channels_payload: Dict[str, Any] = {}
    if isinstance(payload.integrations, dict):
        channels_payload = payload.integrations.copy()

    twilio_settings = channels_payload.get("twilio") if isinstance(channels_payload, dict) else None
    user_join_code = None
    if isinstance(twilio_settings, dict):
        raw_join_code = twilio_settings.get("join_code") or twilio_settings.get("sandbox_join_code")
        if isinstance(raw_join_code, str) and raw_join_code.strip():
            user_join_code = raw_join_code.upper().replace("-", "")
            channels_payload["twilio"] = {**twilio_settings, "join_code": user_join_code}

    integration_preferences = {
        "website": payload.website,
        "instagram": payload.instagram,
        "channels": channels_payload,
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
    existing_sandbox = existing.data[0].get("sandbox_code") if existing.data else None
    sandbox_code = user_join_code or _generate_sandbox_code(existing_sandbox)
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


def _normalize_image_urls(urls: Optional[List[str]]) -> List[str]:
    if not urls:
        return []
    normalized: List[str] = []
    for url in urls:
        if not isinstance(url, str):
            continue
        trimmed = url.strip()
        if trimmed:
            normalized.append(trimmed)
    # Keep a reasonable number of images per item
    return normalized[:6]


def _slugify_item_id(value: Optional[str]) -> str:
    if not value:
        return f"item-{secrets.token_hex(3)}"
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or f"item-{secrets.token_hex(3)}"


def _normalize_sku(raw: str) -> str:
    normalized = (raw or "").strip().upper()
    if not normalized:
        raise HTTPException(status_code=422, detail="SKU cannot be empty")
    return normalized


def _match_inventory_item(inventory: List[Dict[str, Any]], sku_or_slug: str) -> Optional[Dict[str, Any]]:
    normalized = (sku_or_slug or "").strip().upper()
    if not normalized:
        return None
    for item in inventory:
        item_sku = (item.get("sku") or "").strip().upper()
        if item_sku and item_sku == normalized:
            return item
        name_slug = _slugify_item_id(item.get("name"))
        item.setdefault("legacy_name_slug", name_slug)
        if name_slug.upper() == normalized:
            return item
    return None


def _coerce_price(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Price must be a number") from None


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _normalize_inventory_items(inventory: List[Dict[str, Any]]) -> Dict[str, Any]:
    changed = False
    normalized_items: List[Dict[str, Any]] = []
    for item in inventory:
        if not isinstance(item, dict):
            continue
        working = item.copy()
        if not working.get("sku"):
            working["sku"] = _slugify_item_id(working.get("name") or working.get("sku"))[:60].upper()
            changed = True
        working["sku"] = working["sku"].upper()
        working.setdefault("name", working.get("title") or "Unnamed Item")
        working.setdefault("legacy_name_slug", _slugify_item_id(working.get("name")))
        working["price"] = _coerce_price(working.get("price", 0))
        working.setdefault("currency", "NGN")
        urls = working.get("image_urls")
        if urls is None and working.get("image_url"):
            urls = [working.get("image_url")]  # type: ignore[list-item]
        working["image_urls"] = _normalize_image_urls(urls)
        if working["image_urls"]:
            working["image_url"] = working["image_urls"][0]
        working["available_today"] = _coerce_bool(working.get("available_today"), default=_coerce_bool(working.get("available"), default=True))
        working["available"] = working["available_today"]
        if not working.get("updated_at"):
            working["updated_at"] = datetime.utcnow().isoformat()
        normalized_items.append(working)
    return {"items": normalized_items, "changed": changed}


def _collect_business_lookup_values(business_id: Optional[str], current_user: dict) -> List[str]:
    lookup_values: List[str] = []

    def _append_variations(value: Optional[str]) -> None:
        if not value:
            return
        base = value.strip()
        if not base:
            return
        candidates = {
            base,
            base.lower(),
            base.upper(),
            base.replace("-", "_"),
            base.replace("_", "-"),
        }
        slug_form = _slugify(base)
        candidates.add(slug_form)
        candidates.add(slug_form.replace("-", "_"))
        for candidate in list(candidates):
            if candidate:
                candidates.add(candidate.replace("-", "_"))
                candidates.add(candidate.replace("_", "-"))
        for candidate in candidates:
            cleaned = candidate.strip()
            if cleaned and cleaned not in lookup_values:
                lookup_values.append(cleaned)

    normalized_param = (business_id or "").strip()
    if normalized_param.lower() in {"me", "self"}:
        normalized_param = current_user.get("business_id") or ""
    _append_variations(normalized_param)
    _append_variations(current_user.get("business_id"))
    _append_variations(current_user.get("business_name"))
    return lookup_values


SELECT_COLUMNS = "business_id,business_name,owner_user_id,inventory"


def _load_business_record(supabase, business_id: str, current_user: dict) -> Dict[str, Any]:
    lookup_values = _collect_business_lookup_values(business_id, current_user)

    def _fetch(filter_method: str, column: str, value: str):
        query = supabase.table("businesses").select(SELECT_COLUMNS)
        method = getattr(query, filter_method)
        return method(column, value).execute()

    last_error: Optional[Exception] = None
    for candidate in lookup_values:
        if not candidate:
            continue
        try:
            res = _fetch("eq", "business_id", candidate)
            if res.data:
                return res.data[0]
            pattern = candidate if "%" in candidate else candidate
            res = _fetch("ilike", "business_id", pattern)
            if res.data:
                return res.data[0]
            res = _fetch("ilike", "business_id", f"%{candidate}%")
            if res.data:
                return res.data[0]
            res = _fetch("ilike", "business_name", f"%{candidate}%")
            if res.data:
                return res.data[0]
        except Exception as exc:  # pragma: no cover
            last_error = exc
            break

    owner_id = current_user.get("id")
    if owner_id:
        try:
            res = (
                supabase
                .table("businesses")
                .select(SELECT_COLUMNS)
                .eq("owner_user_id", owner_id)
                .execute()
            )
            if res.data:
                return res.data[0]
        except Exception as exc:  # pragma: no cover
            last_error = exc

    if last_error:
        raise HTTPException(status_code=500, detail=f"Unable to load business: {last_error}") from last_error

    raise HTTPException(status_code=404, detail="Business not found")


def _check_inventory_scope(business_id: str, record: Dict[str, Any], current_user: dict) -> None:
    requested_canonical = _canonical_business_id(business_id)
    record_canonical = _canonical_business_id(record.get("business_id"))
    user_canonical = _canonical_business_id(current_user.get("business_id"))

    if user_canonical and (user_canonical == requested_canonical or user_canonical == record_canonical):
        return
    owner_id = record.get("owner_user_id")
    if owner_id and owner_id == current_user.get("id"):
        return
    raise HTTPException(status_code=403, detail="You can only manage your own inventory")


def _save_inventory(supabase, business_id: str, inventory: List[Dict[str, Any]]) -> None:
    try:
        supabase.table("businesses").update({"inventory": inventory}).eq("business_id", business_id).execute()
    except Exception as exc:  # pragma: no cover - Supabase client raises runtime errors
        raise HTTPException(status_code=500, detail=f"Unable to persist inventory: {exc}") from exc


def _serialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    serialized = item.copy()
    serialized.setdefault("currency", "NGN")
    serialized.setdefault("available_today", False)
    serialized.setdefault("available", serialized.get("available_today", False))
    serialized.setdefault("image_urls", [])
    if serialized["image_urls"] and not serialized.get("image_url"):
        serialized["image_url"] = serialized["image_urls"][0]
    return serialized


@router.get("/businesses/{business_id}/inventory")
async def list_inventory(business_id: str, current_user: dict = Depends(_require_business_account)):
    supabase = get_supabase()
    record = _load_business_record(supabase, business_id, current_user)
    _check_inventory_scope(business_id, record, current_user)
    target_business_id = record.get("business_id") or business_id
    inventory = record.get("inventory") or []
    normalized = _normalize_inventory_items(inventory)
    if normalized["changed"]:
        _save_inventory(supabase, target_business_id, normalized["items"])
    sanitized = [_serialize_item(item) for item in normalized["items"]]
    return {"business_id": target_business_id, "inventory": sanitized}


@router.post("/businesses/{business_id}/inventory", status_code=201)
async def create_inventory_item(
    business_id: str,
    payload: InventoryItemInput,
    current_user: dict = Depends(_require_business_account),
):
    supabase = get_supabase()
    record = _load_business_record(supabase, business_id, current_user)
    _check_inventory_scope(business_id, record, current_user)
    target_business_id = record.get("business_id") or business_id

    normalized_sku = _normalize_sku(payload.sku or _slugify_item_id(payload.name))
    inventory: List[Dict[str, Any]] = record.get("inventory") or []
    existing = next((item for item in inventory if (item.get("sku") or "").strip().upper() == normalized_sku), None)
    if existing:
        raise HTTPException(status_code=409, detail=f"Item with SKU '{normalized_sku}' already exists")

    combined_images: List[str] = []
    if payload.image_urls:
        combined_images = _normalize_image_urls(payload.image_urls)
    elif payload.image_url:
        combined_images = _normalize_image_urls([payload.image_url])

    available_flag = _coerce_bool(
        payload.available_today if payload.available_today is not None else payload.available,
        default=True,
    )

    new_item = {
        "sku": normalized_sku,
        "name": payload.name.strip(),
        "description": payload.description.strip() if payload.description else None,
        "price": float(payload.price),
        "currency": (payload.currency or "NGN").upper(),
        "category": payload.category.strip() if payload.category else None,
        "image_urls": combined_images,
        "image_url": combined_images[0] if combined_images else None,
        "available_today": available_flag,
        "available": available_flag,
        "updated_at": datetime.utcnow().isoformat(),
    }

    inventory.append(new_item)
    _save_inventory(supabase, target_business_id, inventory)
    return {"status": "success", "item": new_item, "inventory": inventory}


@router.put("/businesses/{business_id}/inventory/{sku}")
async def update_inventory_item(
    business_id: str,
    sku: str,
    payload: InventoryItemUpdate,
    current_user: dict = Depends(_require_business_account),
):
    supabase = get_supabase()
    record = _load_business_record(supabase, business_id, current_user)
    _check_inventory_scope(business_id, record, current_user)
    target_business_id = record.get("business_id") or business_id

    inventory: List[Dict[str, Any]] = record.get("inventory") or []
    target = _match_inventory_item(inventory, sku)
    if not target:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    target["sku"] = target.get("sku") or _slugify_item_id(target.get("name"))
    if payload.name is not None:
        target["name"] = payload.name.strip()
    if payload.description is not None:
        target["description"] = payload.description.strip() or None
    if payload.price is not None:
        target["price"] = float(payload.price)
    if payload.category is not None:
        target["category"] = payload.category.strip() or None
    if payload.image_urls is not None:
        target["image_urls"] = _normalize_image_urls(payload.image_urls)
    elif payload.image_url is not None:
        target["image_urls"] = _normalize_image_urls([payload.image_url])
    if payload.available_today is not None:
        target["available_today"] = payload.available_today
        target["available"] = payload.available_today
    elif payload.available is not None:
        available_flag = _coerce_bool(payload.available)
        target["available_today"] = available_flag
        target["available"] = available_flag

    if target.get("image_urls"):
        target["image_url"] = target["image_urls"][0]
    else:
        target["image_url"] = None

    target["updated_at"] = datetime.utcnow().isoformat()
    _save_inventory(supabase, target_business_id, inventory)
    return {"status": "success", "item": target, "inventory": inventory}
