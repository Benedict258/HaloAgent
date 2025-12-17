import logging
import mimetypes
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
MEDIA_ROOT = BASE_DIR / "uploads" / "media"
PUBLIC_PREFIX = "/uploads/media"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def _guess_extension(content_type: Optional[str], fallback_ext: Optional[str], url: str) -> str:
    if fallback_ext:
        return fallback_ext.lower().lstrip(".")
    if content_type:
        guess = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guess:
            return guess.lstrip(".")
    suffix = Path(url).suffix
    if suffix:
        return suffix.lower().lstrip(".")
    return "bin"


def _build_filename(source: str, extension: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    token = secrets.token_hex(4)
    ext = extension or "bin"
    return f"{source}-{timestamp}-{token}.{ext}"


class MediaCache:
    async def cache_remote_media(
        self,
        *,
        remote_url: str,
        source: str,
        content_type: Optional[str] = None,
        explicit_extension: Optional[str] = None,
        bearer_token: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """Download media from Meta/Twilio and return a public path."""
        if not remote_url:
            return None
        headers = {}
        auth = None

        if source == "meta" and bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        if source == "twilio":
            account_sid = settings.TWILIO_ACCOUNT_SID
            auth_token = settings.TWILIO_AUTH_TOKEN
            if not (account_sid and auth_token):
                logger.warning("Twilio credentials missing, skipping media cache")
                return None
            auth = (account_sid, auth_token)

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(remote_url, headers=headers, auth=auth)
                response.raise_for_status()
                body = response.content
                resolved_content_type = content_type or response.headers.get("content-type")
                extension = _guess_extension(resolved_content_type, explicit_extension, remote_url)
                filename = _build_filename(source, extension)
                file_path = MEDIA_ROOT / filename
                file_path.write_bytes(body)
                logger.info("Cached %s media to %s", source, file_path)
                return {
                    "public_url": f"{PUBLIC_PREFIX}/{filename}",
                    "path": str(file_path),
                    "content_type": resolved_content_type or "application/octet-stream",
                }
        except Exception as exc:
            logger.warning("Failed to cache media from %s: %s", remote_url, exc)
            return None


media_cache = MediaCache()
