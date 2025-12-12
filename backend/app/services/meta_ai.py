import httpx
from app.core.config import settings
from typing import Optional

class MetaAIService:
    def __init__(self):
        self.api_key = settings.META_AI_API_KEY
        self.endpoint = settings.META_AI_ENDPOINT
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_response(self, message: str, context: str = "") -> Optional[str]:
        """Generate AI response using Llama 3"""
        try:
            prompt = f"""You are HaloAgent, a helpful CRM assistant for Nigerian small businesses.
Context: {context}
Customer message: {message}

Respond helpfully and professionally. If it's an order, ask for details. If it's a complaint, be empathetic."""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.endpoint}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 150,
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                return "I'm here to help! Please tell me more about what you need."
                
        except Exception as e:
            print(f"Meta AI error: {e}")
            return "I'm here to help! Please tell me more about what you need."

meta_ai_service = MetaAIService()