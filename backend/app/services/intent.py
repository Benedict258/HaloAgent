from typing import Dict, Any, List
from app.services.meta_ai import meta_ai_service
import json
import logging

logger = logging.getLogger(__name__)

class IntentService:
    def __init__(self):
        self.keywords = {
            "ORDER": ["buy", "order", "want", "need", "purchase", "get", "price", "cost", "how much"],
            "STATUS": ["status", "track", "where", "delivery", "arrive", "not recieved"],
            "FEEDBACK": ["bad", "good", "love", "hate", "issue", "complain", "broken", "wrong"],
            "HELP": ["help", "support", "agent", "human", "speak", "talk", "start", "hello", "hi"],
        }

    async def identify_intent(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classify intent using Keyword Heuristics + AI Fallback.
        Returns: { "intent": "...", "confidence": float, "source": "keyword|ai" }
        """
        text_lower = text.lower().strip()
        
        # 1. Keyword Check (Fast)
        for intent, words in self.keywords.items():
            if any(w in text_lower for w in words):
                 # Simple heuristic: if match found, return. Refine later.
                 # "how much" -> ORDER. "where is my order" -> STATUS.
                 # Overlap handling: "order status" -> STATUS (priority?)
                 # For now, return first match.
                 if intent == "ORDER" and "status" in text_lower:
                     return {"intent": "STATUS", "confidence": 0.9, "source": "keyword"}
                 
                 return {"intent": intent, "confidence": 0.8, "source": "keyword"}

        # 2. AI Fallback (Robust)
        # We usage Meta AI to classify strict intents.
        try:
            prompt = f"""
            Classify the intent of this message into user categories:
            CATEGORIES: [ORDER, STATUS, FEEDBACK, HELP, UNKNOWN]
            
            MESSAGE: "{text}"
            
            Respond with valid JSON only: {{"intent": "CATEGORY", "confidence": 0.0-1.0}}
            """
            
            response_text = await meta_ai_service.chat_completion(prompt)
            # Parse JSON
            try:
                # Meta AI might add "Here is the JSON..." wrapper, need to clean?
                # Using our robust core parsing logic or simple extracting of {...}
                if "{" in response_text:
                    json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
                    result = json.loads(json_str)
                    result["source"] = "ai"
                    return result
            except:
                pass # JSON fail
                
            return {"intent": "UNKNOWN", "confidence": 0.5, "source": "fallback"}
            
        except Exception as e:
            logger.error(f"Intent AI failed: {e}")
            return {"intent": "UNKNOWN", "confidence": 0.0, "source": "error"}

intent_service = IntentService()
