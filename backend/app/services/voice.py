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
        Transcribe audio using AssemblyAI (best codec support for WhatsApp)
        
        Args:
            audio_url: URL to audio file
            content_type: MIME type
        
        Returns:
            Transcribed text
        """
        try:
            # Download audio
            async with httpx.AsyncClient() as client:
                audio_response = await client.get(
                    audio_url,
                    auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                    timeout=30.0
                )
                audio_data = audio_response.content
                logger.info(f"Downloaded: {len(audio_data)} bytes")
            
            # AssemblyAI (free tier, best codec support)
            assembly_key = os.getenv("ASSEMBLYAI_API_KEY")
            if assembly_key:
                async with httpx.AsyncClient() as client:
                    # Upload
                    upload_response = await client.post(
                        "https://api.assemblyai.com/v2/upload",
                        headers={"authorization": assembly_key},
                        content=audio_data,
                        timeout=30.0
                    )
                    if upload_response.status_code == 200:
                        upload_url = upload_response.json()["upload_url"]
                        
                        # Transcribe
                        transcript_response = await client.post(
                            "https://api.assemblyai.com/v2/transcript",
                            headers={"authorization": assembly_key},
                            json={"audio_url": upload_url},
                            timeout=30.0
                        )
                        transcript_id = transcript_response.json()["id"]
                        
                        # Poll for result
                        import asyncio
                        for _ in range(30):
                            await asyncio.sleep(1)
                            result_response = await client.get(
                                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                                headers={"authorization": assembly_key}
                            )
                            result = result_response.json()
                            if result["status"] == "completed":
                                text = result.get("text", "")
                                logger.info(f"✅ Transcribed: {text}")
                                return text
                            elif result["status"] == "error":
                                break
            
            return ""
                    
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
    
    async def text_to_speech(self, text: str, voice: str = "alloy") -> bytes:
        """
        Convert text to speech using OpenAI TTS
        
        Args:
            text: Text to convert
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        
        Returns:
            Audio bytes (MP3)
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {settings.META_AI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "tts-1",
                        "input": text,
                        "voice": voice
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
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
        """Send voice via Twilio"""
        try:
            from twilio.rest import Client
            
            # Save audio temporarily
            temp_path = f"/tmp/voice_{to_number.replace('+', '')}.mp3"
            with open(temp_path, "wb") as f:
                f.write(audio_bytes)
            
            # Upload to public URL (you'd use Supabase Storage here)
            # For now, we'll use Twilio's media URL approach
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            message = client.messages.create(
                from_=f"whatsapp:{settings.TWILIO_PHONE_NUMBER}",
                to=f"whatsapp:{to_number}",
                media_url=[f"https://your-cdn.com/voice.mp3"]  # Replace with actual URL
            )
            
            logger.info(f"Voice sent via Twilio: {message.sid}")
            
            # Clean up
            os.remove(temp_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Twilio voice error: {e}")
            return False
    
    async def _send_meta_voice(self, to_number: str, audio_bytes: bytes):
        """Send voice via Meta WhatsApp"""
        # Similar to Twilio but using Meta API
        pass

voice_service = VoiceService()
