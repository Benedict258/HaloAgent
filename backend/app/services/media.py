"""
Media service for sending images via WhatsApp
"""
import httpx
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class MediaService:
    
    async def send_product_image(self, to_number: str, product: dict, channel: str = "whatsapp"):
        """
        Send product with image via WhatsApp
        
        Product format:
        {
            "name": "Chocolate Cake",
            "price": 5000,
            "description": "Rich chocolate cake",
            "image_url": "https://..."
        }
        """
        
        if channel == "whatsapp":
            return await self._send_whatsapp_image(to_number, product)
        elif channel == "twilio":
            return await self._send_twilio_image(to_number, product)
    
    async def _send_whatsapp_image(self, to_number: str, product: dict):
        """Send image via Meta WhatsApp Business API"""
        try:
            url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Build caption
            caption = f"*{product['name']}*\n\n"
            caption += f"{product.get('description', '')}\n\n"
            caption += f"Price: ₦{product['price']:,}"
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "image",
                "image": {
                    "link": product.get("image_url"),
                    "caption": caption
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    logger.info(f"Image sent to {to_number}: {product['name']}")
                    return True
                else:
                    logger.error(f"Failed to send image: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending WhatsApp image: {e}")
            return False
    
    async def _send_twilio_image(self, to_number: str, product: dict):
        """Send image via Twilio WhatsApp"""
        try:
            from twilio.rest import Client
            
            if not settings.TWILIO_ACCOUNT_SID:
                return False
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            sandbox = settings.TWILIO_PHONE_NUMBER
            
            # Build message body
            body = f"*{product['name']}*\n\n"
            body += f"{product.get('description', '')}\n\n"
            body += f"Price: ₦{product['price']:,}"
            
            # Twilio supports media URLs
            message = client.messages.create(
                from_=f"whatsapp:{sandbox}",
                to=f"whatsapp:{to_number}",
                body=body,
                media_url=[product.get("image_url")]
            )
            
            logger.info(f"Twilio image sent: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Twilio image: {e}")
            return False
    
    async def send_multiple_products(self, to_number: str, products: list, channel: str = "whatsapp"):
        """Send multiple products as separate messages"""
        sent_count = 0
        
        for product in products:
            if product.get("image_url"):
                success = await self.send_product_image(to_number, product, channel)
                if success:
                    sent_count += 1
                    # Small delay between messages
                    import asyncio
                    await asyncio.sleep(1)
        
        return sent_count

media_service = MediaService()
