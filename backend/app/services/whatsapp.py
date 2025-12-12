import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

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
                if response.status_code != 200:
                    logger.error(
                        "WhatsApp send_text failed (%s): %s",
                        response.status_code,
                        response.text
                    )
                    return False
                return True
        except Exception as e:
            logger.exception("WhatsApp send_text exception: %s", e)
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
                if response.status_code != 200:
                    logger.error(
                        "WhatsApp send_template failed (%s): %s",
                        response.status_code,
                        response.text
                    )
                    return False
                return True
        except Exception as e:
            logger.exception("WhatsApp send_template exception: %s", e)
            return False

whatsapp_service = WhatsAppService()