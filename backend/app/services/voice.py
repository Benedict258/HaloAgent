"""
Voice service for speech-to-text and text-to-speech
"""
import asyncio
import logging
import os
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

class VoiceService:
    
    async def transcribe_audio(
        self,
        audio_url: str,
        content_type: str = "audio/ogg",
        *,
        source: str = "twilio",
        message_sid: Optional[str] = None,
        bearer_token: Optional[str] = None,
    ) -> str:
        """Transcribe WhatsApp/Twilio voice notes via AssemblyAI."""

        try:
            logger.info("Starting transcription for %s [%s]", audio_url, source)
            audio_bytes = await self._download_audio(
                audio_url=audio_url,
                source=source,
                content_type=content_type,
                message_sid=message_sid,
                bearer_token=bearer_token,
            )

            if not audio_bytes:
                logger.error("Unable to download audio for transcription")
                return ""

            return await self._transcribe_with_assembly(audio_bytes)
        except Exception as exc:
            logger.error("Transcription error: %s", exc, exc_info=True)
            return ""
    
    async def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech using Deepgram Aura TTS
        """
        try:
            deepgram_key = os.getenv("DEEPGRAM_API_KEY")
            if not deepgram_key:
                logger.error("No Deepgram key for TTS")
                return None
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepgram.com/v1/speak?model=aura-asteria-en",
                    headers={
                        "Authorization": f"Token {deepgram_key}",
                        "Content-Type": "application/json"
                    },
                    json={"text": text},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Generated TTS: {len(response.content)} bytes")
                    return response.content
                else:
                    logger.error(f"TTS failed: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
    
    async def send_voice_message(self, to_number: str, audio_bytes: bytes, channel: str = "twilio"):
        """
        Send voice message via WhatsApp
        
        Args:
            to_number: Recipient phone
            audio_bytes: Audio file bytes
            channel: twilio or meta
        """
        try:
            if channel == "twilio":
                return await self._send_twilio_voice(to_number, audio_bytes)
            else:
                return await self._send_meta_voice(to_number, audio_bytes)
        except Exception as e:
            logger.error(f"Send voice error: {e}")
            return False
    
    async def _send_twilio_voice(self, to_number: str, audio_bytes: bytes):
        """Send voice via Twilio using Supabase storage"""
        try:
            # Upload to Supabase Storage with service key
            from supabase import create_client
            import time
            
            logger.info(f"Uploading {len(audio_bytes)} bytes to Supabase...")
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            
            filename = f"voice_{to_number.replace('+', '')}_{int(time.time())}.mp3"
            upload_result = supabase.storage.from_("voice-messages").upload(filename, audio_bytes)
            logger.info(f"Upload result: {upload_result}")
            
            # Get public URL
            audio_url = supabase.storage.from_("voice-messages").get_public_url(filename)
            logger.info(f"Public URL: {audio_url}")
            
            # Send via Twilio
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            message = client.messages.create(
                from_=f"whatsapp:{settings.TWILIO_PHONE_NUMBER}",
                to=f"whatsapp:{to_number}",
                media_url=[audio_url]
            )
            
            logger.info(f"✅ Voice sent: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Twilio voice error: {e}", exc_info=True)
            return False
    
    async def _send_meta_voice(self, to_number: str, audio_bytes: bytes):
        """Send voice via Meta WhatsApp"""
        # Similar to Twilio but using Meta API
        pass

    async def _download_audio(
        self,
        *,
        audio_url: str,
        source: str,
        content_type: str,
        message_sid: Optional[str],
        bearer_token: Optional[str],
    ) -> Optional[bytes]:
        headers = {}
        auth = None

        if source == "twilio":
            if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
                logger.error("Missing Twilio credentials for audio download")
                return None
            auth = httpx.BasicAuth(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        elif source == "meta":
            token = bearer_token or settings.WHATSAPP_API_TOKEN
            if token:
                headers["Authorization"] = f"Bearer {token}"
            else:
                logger.warning("No Meta access token available for voice download")

        response = await self._http_get(audio_url, auth=auth, headers=headers or None)
        if self._looks_like_audio(response):
            logger.info("Downloaded %s bytes (%s)", len(response.content), response.headers.get("content-type"))
            return response.content

        if source == "twilio":
            fallback_bytes = await self._download_twilio_media_via_api(audio_url, message_sid)
            if fallback_bytes:
                return fallback_bytes

        status = response.status_code if response else "unknown"
        logger.error("Unable to fetch audio from %s (status=%s, type=%s)", audio_url, status, content_type)
        return None

    async def _http_get(self, url: str, auth=None, headers=None) -> Optional[httpx.Response]:
        try:
            async with httpx.AsyncClient() as client:
                return await client.get(
                    url,
                    auth=auth,
                    headers=headers,
                    follow_redirects=True,
                    timeout=30.0,
                )
        except Exception as exc:
            logger.error("HTTP GET failed for %s: %s", url, exc)
            return None

    def _looks_like_audio(self, response: Optional[httpx.Response]) -> bool:
        if not response or response.status_code != 200:
            return False
        content_type = (response.headers.get("content-type") or "").lower()
        if "audio" in content_type or "ogg" in content_type:
            return True
        snippet = response.content[:64].lstrip()
        if snippet.startswith(b"<"):
            logger.error("Voice download returned HTML/XML instead of audio: %s", snippet[:64])
            return False
        return bool(response.content)

    def _extract_twilio_media_sid(self, audio_url: str) -> Optional[str]:
        try:
            parsed = urlparse(audio_url)
            segments = [segment for segment in parsed.path.split("/") if segment]
            if "Media" in segments:
                media_index = segments.index("Media")
                if len(segments) > media_index + 1:
                    return segments[media_index + 1]
        except Exception as exc:
            logger.debug("Unable to parse media SID from %s: %s", audio_url, exc)
        return None

    async def _download_twilio_media_via_api(self, audio_url: str, message_sid: Optional[str]) -> Optional[bytes]:
        media_sid = self._extract_twilio_media_sid(audio_url)
        if not media_sid or not message_sid:
            return None
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            return None

        from twilio.rest import Client

        def _fetch() -> Optional[bytes]:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            response = client.request(
                "GET",
                f"/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages/{message_sid}/Media/{media_sid}",
            )
            if response.status_code == 200:
                logger.info("Downloaded audio via Twilio media API fallback")
                return response.content
            logger.error(
                "Twilio media API fallback failed (%s): %s",
                response.status_code,
                response.text[:120],
            )
            return None

        return await asyncio.to_thread(_fetch)

    async def _transcribe_with_assembly(self, audio_data: bytes) -> str:
        assembly_key = os.getenv("ASSEMBLYAI_API_KEY")
        if not assembly_key:
            logger.error("No AssemblyAI key configured")
            return ""

        logger.info("Uploading audio to AssemblyAI (%s bytes)...", len(audio_data))
        async with httpx.AsyncClient() as client:
            upload_response = await client.post(
                "https://api.assemblyai.com/v2/upload",
                headers={"authorization": assembly_key},
                content=audio_data,
                timeout=30.0,
            )

            if upload_response.status_code != 200:
                logger.error("AssemblyAI upload failed: %s", upload_response.text[:200])
                return ""

            upload_url = upload_response.json().get("upload_url")
            transcript_response = await client.post(
                "https://api.assemblyai.com/v2/transcript",
                headers={"authorization": assembly_key},
                json={"audio_url": upload_url},
                timeout=30.0,
            )
            transcript_id = transcript_response.json().get("id")
            logger.info("AssemblyAI transcript job %s created", transcript_id)

            for attempt in range(45):
                await asyncio.sleep(1)
                poll = await client.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers={"authorization": assembly_key},
                )
                payload = poll.json()
                status = payload.get("status")
                if status == "completed":
                    text = payload.get("text", "")
                    logger.info("✅ Transcribed text: %s", text)
                    return text
                if status == "error":
                    logger.error("AssemblyAI error: %s", payload.get("error"))
                    return ""
                if attempt % 10 == 0:
                    logger.info("Polling AssemblyAI... status=%s", status)

        logger.error("AssemblyAI transcription timed out")
        return ""

voice_service = VoiceService()
