import httpx
import asyncio
from app.core.config import settings
from typing import Optional
import time
import os

class MetaAIService:
    def __init__(self):
        # Check if we should use OpenRouter as fallback
        self.use_openrouter = os.getenv("USE_OPENROUTER", "false").lower() == "true"
        
        if self.use_openrouter:
            self.api_key = os.getenv("OPENROUTER_API_KEY")
            self.endpoint = "https://openrouter.ai/api/v1"
            self.model = "meta-llama/llama-3.1-8b-instruct:free"
        else:
            self.api_key = settings.META_AI_API_KEY
            self.endpoint = settings.META_AI_ENDPOINT
            self.model = "llama-3.3-70b-versatile"  # Smaller, faster, higher free limits
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.last_request_time = 0
        self.min_request_interval = 6  # 6 seconds between requests
    
    async def chat_completion(self, messages: list, temperature: float = 0.7) -> Optional[str]:
        """Generic chat completion using Llama 3"""
        try:
            # Rate limiting: wait if needed
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - elapsed)
            
            self.last_request_time = time.time()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.endpoint}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 800,
                        "temperature": 0.3
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                
                # Handle rate limit
                if response.status_code == 429:
                    print(f"Meta AI Rate Limit: {response.text}")
                    return "I'm experiencing high demand right now. Please try again in a few minutes! 🙏"
                
                print(f"Meta AI Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Meta AI error: {e}")
            return None

    async def generate_response(self, message: str, context: str = "") -> Optional[str]:
        """Legacy method for backward compatibility - simpler prompt"""
        prompt = f"""You are HaloAgent, a helpful CRM assistant.
Context: {context}
Customer message: {message}"""
        
        return await self.chat_completion([{"role": "user", "content": prompt}])

meta_ai_service = MetaAIService()