import logging
import random
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)

ORD_PATTERN = re.compile(r"ORD[-\s]?\d{3,}", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(
    r"(?:NGN|\u20A6)\s*((?:[0-9]{1,3}(?:[.,\s][0-9]{3})*(?:[.,][0-9]{2})?)|(?:[0-9]+(?:[.,][0-9]{2})?))",
    re.IGNORECASE,
)
ACCOUNT_NUMBER_PATTERN = re.compile(r"\b\d{10}\b")
ACCOUNT_NAME_PATTERN = re.compile(r"(?:ACCOUNT\s+NAME|ACCT\s+NAME|BENEFICIARY)[\s:.-]*([A-Z0-9\s.&]+)", re.IGNORECASE)


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
        detected_reference = self._extract_reference_from_text(text_hint)
        if not detected_reference:
            detected_reference = self._extract_reference_from_text(media_url)
        if detected_reference:
            hints.append(f"Reference candidate: {detected_reference}")
        elif normalized_reference:
            hints.append(f"Expected reference {normalized_reference} missing from receipt upload.")

        detected_amount = self._extract_amount_from_text(text_hint)
        if detected_amount is None:
            detected_amount = self._extract_amount_from_text(media_url)
        if detected_amount is not None:
            hints.append(f"Amount candidate: NGN {detected_amount:,.0f}")
        elif expected_amount is not None:
            hints.append(f"Could not read amount from receipt; expected NGN {expected_amount:,.0f}.")

        settlement_account = self._fetch_settlement_account(business_id)
        expected_account_name = settlement_account.get("account_name")
        expected_account_number = settlement_account.get("account_number")

        detected_account_number = self._extract_account_number_from_text(text_hint)
        if detected_account_number is None:
            detected_account_number = self._extract_account_number_from_text(media_url)

        detected_account_name = self._extract_account_name_from_text(text_hint)
        if detected_account_name is None:
            detected_account_name = self._extract_account_name_from_text(media_url)

        account_number_match = self._compare_account_numbers(expected_account_number, detected_account_number)
        account_name_match = self._compare_account_names(expected_account_name, detected_account_name)

        if expected_account_number:
            if account_number_match:
                hints.append("Account number matches the saved payout details.")
            elif detected_account_number:
                hints.append(
                    "Account number differs: expected "
                    f"{self._mask_account_number(expected_account_number)}, saw "
                    f"{self._mask_account_number(detected_account_number)}."
                )
            else:
                hints.append("Receipt is missing an account number while one was expected.")

        if expected_account_name:
            if account_name_match:
                hints.append("Account name matches the saved payout details.")
            elif detected_account_name:
                hints.append(
                    "Account name differs: expected "
                    f"{expected_account_name}, saw {detected_account_name}."
                )
            else:
                hints.append("Receipt did not include the business account name.")

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
            "expected_account_name": expected_account_name,
            "expected_account_number": expected_account_number,
            "detected_account_name": detected_account_name,
            "detected_account_number": detected_account_number,
            "account_name_match": account_name_match,
            "account_number_match": account_number_match,
            "bank_details_match": account_name_match and account_number_match,
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
        upper_text = text.upper()
        for match in AMOUNT_PATTERN.finditer(upper_text):
            raw_value = match.group(1)
            cleaned = raw_value.replace(",", "").replace(" ", "")
            try:
                return float(cleaned)
            except ValueError:
                continue
        return None

    def _extract_account_number_from_text(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        for match in ACCOUNT_NUMBER_PATTERN.findall(text):
            digits = re.sub(r"\D", "", match)
            if len(digits) == 10:
                return digits
        return None

    def _extract_account_name_from_text(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        match = ACCOUNT_NAME_PATTERN.search(text)
        if match:
            candidate = match.group(1).strip()
            return re.sub(r"\s+", " ", candidate)
        return None

    def _compare_account_numbers(self, expected: Optional[str], detected: Optional[str]) -> bool:
        expected_norm = self._normalize_account_number(expected)
        detected_norm = self._normalize_account_number(detected)
        return bool(expected_norm and detected_norm and expected_norm == detected_norm)

    def _compare_account_names(self, expected: Optional[str], detected: Optional[str]) -> bool:
        expected_norm = self._normalize_account_name(expected)
        detected_norm = self._normalize_account_name(detected)
        if not expected_norm or not detected_norm:
            return False
        return expected_norm == detected_norm or expected_norm in detected_norm or detected_norm in expected_norm

    def _normalize_account_number(self, number: Optional[str]) -> Optional[str]:
        if not number:
            return None
        digits = re.sub(r"\D", "", number)
        return digits or None

    def _mask_account_number(self, number: Optional[str]) -> str:
        normalized = self._normalize_account_number(number)
        if not normalized:
            return "(unknown)"
        if len(normalized) <= 4:
            return normalized
        return f"{'*' * (len(normalized) - 4)}{normalized[-4:]}"

    def _normalize_account_name(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        cleaned = re.sub(r"\s+", " ", name).strip()
        return cleaned.upper() or None

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

    def _fetch_settlement_account(self, business_id: str) -> Dict[str, Any]:
        try:
            result = (
                supabase
                .table("businesses")
                .select("settlement_account, payment_instructions")
                .eq("business_id", business_id)
                .limit(1)
                .execute()
            )
            if result.data:
                payload = result.data[0]
                return payload.get("settlement_account") or payload.get("payment_instructions") or {}
        except Exception as exc:
            logger.warning("Unable to fetch settlement account for %s: %s", business_id, exc)
        return {}


vision_service = VisionService()
