import logging
import random
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


class VisionService:
    """Stub DINOV3 integration for receipt + product image analysis."""

    async def analyze_receipt(
        self,
        *,
        business_id: str,
        contact_id: Optional[int],
        order_id: Optional[int],
        media_url: str,
    ) -> Dict[str, Any]:
        """Return mock receipt extraction until DINOV3 wiring is ready."""
        analysis = {
            "type": "receipt",
            "model": "dinov3-stub",
            "confidence": round(random.uniform(0.65, 0.92), 2),
            "total_amount": None,
            "currency": "NGN",
            "detected_reference": None,
            "detected_items": [],
        }
        await self._record_analysis(
            business_id=business_id,
            contact_id=contact_id,
            order_id=order_id,
            analysis_type="receipt",
            media_url=media_url,
            analysis=analysis,
        )
        return analysis

    async def analyze_product_photo(
        self,
        *,
        business_id: str,
        contact_id: Optional[int],
        media_url: str,
        inventory: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Roughly match product photo to nearest inventory item (stub)."""
        top_match = None
        if inventory:
            sample = random.choice(inventory)
            top_match = {
                "name": sample.get("name"),
                "confidence": round(random.uniform(0.55, 0.88), 2),
                "price": sample.get("price"),
            }
        analysis = {
            "type": "product_photo",
            "model": "dinov3-stub",
            "top_match": top_match,
            "notes": "Vision pipeline stubbed."
        }
        await self._record_analysis(
            business_id=business_id,
            contact_id=contact_id,
            order_id=None,
            analysis_type="product_photo",
            media_url=media_url,
            analysis=analysis,
        )
        return analysis

    async def _record_analysis(
        self,
        *,
        business_id: str,
        contact_id: Optional[int],
        order_id: Optional[int],
        analysis_type: str,
        media_url: str,
        analysis: Dict[str, Any],
    ) -> None:
        try:
            payload = {
                "business_id": business_id,
                "contact_id": contact_id,
                "order_id": order_id,
                "analysis_type": analysis_type,
                "media_url": media_url,
                "analysis": analysis,
                "created_at": datetime.utcnow().isoformat(),
            }
            supabase.table("vision_analysis_results").insert(payload).execute()
        except Exception as exc:
            logger.error("Failed to record vision analysis: %s", exc)


vision_service = VisionService()
