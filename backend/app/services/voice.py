"""
Voice service for speech-to-text and text-to-speech
"""
import httpx
import os
import io
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class VoiceService:
    
    async def transcribe_audio(self, audio_url: str, content_type: str = "audio/ogg") -> str:
        """
        Transcribe audio using AssemblyAI
        """
        try:
            logger.info(f"Starting transcription for {audio_url}")
            
            # Download audio with proper Twilio auth
            async with httpx.AsyncClient() as client:
                audio_response = await client.get(
                    audio_url,
                    auth=httpx.BasicAuth(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                    follow_redirects=True,
                    timeout=30.0
                )
                
                if audio_response.status_code != 200:
                    logger.error(f"Download failed: {audio_response.status_code} - {audio_response.text[:200]}")
                    return ""
                
                audio_data = audio_response.content
                logger.info(f"Downloaded: {len(audio_data)} bytes, content-type: {audio_response.headers.get('content-type')}")
                
                # Check if we got XML error instead of audio
                if b'<?xml' in audio_data[:100] or b'<html' in audio_data[:100]:
                    logger.error(f"Got HTML/XML instead of audio: {audio_data[:200]}")
                    return ""
            
            # AssemblyAI
            assembly_key = os.getenv("ASSEMBLYAI_API_KEY")
            if not assembly_key:
                logger.error("No AssemblyAI key")
                return ""
            
            logger.info("Uploading to AssemblyAI...")
            async with httpx.AsyncClient() as client:
                # Upload
                upload_response = await client.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers={"authorization": assembly_key},
                    content=audio_data,
                    timeout=30.0
                )
                
                if upload_response.status_code != 200:
                    logger.error(f"Upload failed: {upload_response.text}")
                    return ""
                
                upload_url = upload_response.json()["upload_url"]
                logger.info(f"Uploaded, starting transcription...")
                
                # Transcribe
                transcript_response = await client.post(
                    "https://api.assemblyai.com/v2/transcript",
                    headers={"authorization": assembly_key},
                    json={"audio_url": upload_url},
                    timeout=30.0
                )
                transcript_id = transcript_response.json()["id"]
                logger.info(f"Transcription started: {transcript_id}")
                
                # Poll for result
                import asyncio
                for i in range(30):
                    await asyncio.sleep(1)
                    result_response = await client.get(
                        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                        headers={"authorization": assembly_key}
                    )
                    result = result_response.json()
                    status = result["status"]
                    
                    if status == "completed":
                        text = result.get("text", "")
                        logger.info(f"✅ Transcribed: {text}")
                        return text
                    elif status == "error":
                        logger.error(f"Transcription error: {result.get('error')}")
                        return ""
                    
                    if i % 5 == 0:
                        logger.info(f"Polling... status={status}")
                
                logger.error("Transcription timeout")
                return ""
                    
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
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
            # Upload to Supabase Storage
            from supabase import create_client
            import time
            
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            
            filename = f"voice_{to_number.replace('+', '')}_{int(time.time())}.mp3"
            supabase.storage.from_("voice-messages").upload(filename, audio_bytes)
            
            # Get public URL
            audio_url = supabase.storage.from_("voice-messages").get_public_url(filename)
            
            # Send via Twilio
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            message = client.messages.create(
                from_=f"whatsapp:{settings.TWILIO_PHONE_NUMBER}",
                to=f"whatsapp:{to_number}",
                media_url=[audio_url]
            )
            
            logger.info(f"Voice sent: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Twilio voice error: {e}")
            return False
    
    async def _send_meta_voice(self, to_number: str, audio_bytes: bytes):
        """Send voice via Meta WhatsApp"""
        # Similar to Twilio but using Meta API
        pass

voice_service = VoiceService()
