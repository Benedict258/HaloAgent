import httpx
from app.core.config import settings
from typing import Optional

class WhatsAppService:
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}"
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json"
        }
    
    async def send_text(self, to: str, message: str) -> bool:
        """Send text message via WhatsApp"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "text",
                        "text": {"body": message}
                    }
                )
                return response.status_code == 200
        except Exception as e:
            print(f"WhatsApp send error: {e}")
            return False
    
    async def send_template(self, to: str, template_name: str, language: str = "en") -> bool:
        """Send template message"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "template",
                        "template": {
                            "name": template_name,
                            "language": {"code": language}
                        }
                    }
                )
                return response.status_code == 200
        except Exception as e:
            print(f"WhatsApp template error: {e}")
            return False

whatsapp_service = WhatsAppService()