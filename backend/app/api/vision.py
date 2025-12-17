from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging

from app.api.auth import require_business_user
from app.db.supabase_client import supabase, supabase_admin

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/vision/analyses")
async def list_vision_analyses(
    limit: int = Query(20, ge=1, le=100),
    analysis_type: Optional[str] = Query(None),
    current_user: dict = Depends(require_business_user),
):
    """Return recent vision analysis entries (receipt + product photos)."""
    try:
        business_id = current_user["business_id"]
        client = supabase_admin or supabase
        query = (
            client
            .table("vision_analysis_results")
            .select(
                "id, analysis_type, media_url, analysis, created_at, order_id, contact_id, "
                "contacts(name, phone_number), orders(order_number, payment_reference, total_amount)"
            )
            .eq("business_id", business_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if analysis_type:
            query = query.eq("analysis_type", analysis_type)
        result = query.execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Vision analyses fetch error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load vision analyses")
