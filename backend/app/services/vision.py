import logging
import random
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)

ORD_PATTERN = re.compile(r"ORD[-\s]?\d{3,}", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r"(NGN|N|#)?\s*([0-9]{3,}(?:[.,]\d{2})?)")


class VisionService:
    """Stub DINOV3 integration for receipt + product image analysis."""

    async def analyze_receipt(
        self,
        *,
        business_id: str,
        contact_id: Optional[int],
        order_id: Optional[int],
        media_url: str,
        expected_amount: Optional[float] = None,
        expected_reference: Optional[str] = None,
        text_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return mock receipt extraction until DINOV3 wiring is ready."""
        hints: List[str] = []
        normalized_reference = self._normalize_reference(expected_reference)
        detected_reference = normalized_reference or self._extract_reference_from_text(text_hint)
        if not detected_reference:
            detected_reference = self._extract_reference_from_text(media_url)
        if detected_reference:
            hints.append(f"Reference candidate: {detected_reference}")

        detected_amount = None
        if expected_amount is not None:
            detected_amount = expected_amount
            hints.append(f"Amount matches expected NGN {expected_amount:,.0f}")
        else:
            detected_amount = self._extract_amount_from_text(text_hint)
            if detected_amount is not None:
                hints.append(f"Amount candidate: NGN {detected_amount:,.0f}")

        match_status = self._resolve_match_status(normalized_reference, detected_reference, expected_amount, detected_amount)

        analysis = {
            "type": "receipt",
            "model": "dinov3-stub",
            "confidence": round(random.uniform(0.7, 0.95), 2),
            "currency": "NGN",
            "expected_amount": expected_amount,
            "expected_reference": normalized_reference,
            "detected_reference": detected_reference,
            "detected_amount": detected_amount,
            "total_amount": detected_amount,
            "match_status": match_status,
            "hints": hints,
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
        hints: List[str] = []
        if inventory:
            sample = random.choice(inventory)
            top_match = {
                "name": sample.get("name"),
                "confidence": round(random.uniform(0.55, 0.88), 2),
                "price": sample.get("price"),
            }
            if top_match.get("name"):
                hints.append(f"Looks like {top_match['name']}")
        analysis = {
            "type": "product_photo",
            "model": "dinov3-stub",
            "top_match": top_match,
            "notes": "Vision pipeline stubbed.",
            "hints": hints,
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

    def _normalize_reference(self, reference: Optional[str]) -> Optional[str]:
        if not reference:
            return None
        cleaned = reference.strip().upper().replace(" ", "")
        cleaned = cleaned.replace("_", "-")
        return cleaned

    def _extract_reference_from_text(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        match = ORD_PATTERN.search(text.upper())
        if match:
            candidate = match.group(0).upper().replace(" ", "")
            return candidate if candidate.startswith("ORD") else None
        return None

    def _extract_amount_from_text(self, text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        for match in AMOUNT_PATTERN.findall(text.upper()):
            raw_value = match[1]
            digits = raw_value.replace(",", "").replace(" ", "")
            try:
                return float(digits)
            except ValueError:
                continue
        return None

    def _resolve_match_status(
        self,
        expected_reference: Optional[str],
        detected_reference: Optional[str],
        expected_amount: Optional[float],
        detected_amount: Optional[float],
    ) -> str:
        reference_match = bool(expected_reference and detected_reference and expected_reference == detected_reference)
        amount_match = False
        if expected_amount is not None and detected_amount is not None:
            amount_match = abs(expected_amount - detected_amount) < 1
        if reference_match and amount_match:
            return "reference_and_amount_match"
        if reference_match:
            return "reference_match"
        if amount_match:
            return "amount_match"
        return "needs_review"

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
