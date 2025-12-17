from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services.voice import voice_service


@pytest.mark.asyncio
async def test_twilio_voice_download_uses_media_fallback(monkeypatch):
    """Expired Twilio media URLs should fall back to the media API."""

    class DummyResponse:
        status_code = 404
        headers = {"content-type": "text/html"}
        content = b"<html>Expired</html>"

    async def fake_http_get(*args, **kwargs):
        return DummyResponse()

    fallback_calls = SimpleNamespace(count=0)

    async def fake_media_fetch(*_, **__):
        fallback_calls.count += 1
        return b"audio-bytes"

    monkeypatch.setattr(voice_service, "_http_get", fake_http_get)
    monkeypatch.setattr(voice_service, "_download_twilio_media_via_api", fake_media_fetch)
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "ACXXXX", raising=False)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "auth-token", raising=False)

    audio = await voice_service._download_audio(
        audio_url="https://api.twilio.com/2010-04-01/Accounts/ACXXXX/Messages/SMYYY/Media/MMZZZ",
        source="twilio",
        content_type="audio/ogg",
        message_sid="SMYYY",
        bearer_token=None,
    )

    assert audio == b"audio-bytes"
    assert fallback_calls.count == 1
