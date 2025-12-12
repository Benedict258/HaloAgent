from typing import Dict, Optional

class LanguageService:
    def __init__(self):
        self.translations = {
            "welcome": {
                "en": "Welcome to HaloAgent! How can I help you today?",
                "yo": "Kaabo si HaloAgent! Bawo ni mo se le ran e lowo loni?",
                "ha": "Maraba da zuwa HaloAgent! Yaya zan iya taimaka muku yau?",
                "ig": "Ndewo na HaloAgent! Kedu ka m ga-enyere gị aka taa?"
            },
            "order_received": {
                "en": "Thank you for your order! We'll process it shortly.",
                "yo": "E se fun order yin! A o se e laipe.",
                "ha": "Na gode da odar ku! Za mu sarrafa shi nan ba da jimawa ba.",
                "ig": "Daalụ maka order gị! Anyị ga-edozi ya n'oge na-adịghị anya."
            },
            "complaint_acknowledged": {
                "en": "I understand your concern. Let me help resolve this issue.",
                "yo": "Mo ye ohun ti e n so. Je ki n ran yin lowo lati yanju oro yi.",
                "ha": "Na fahimci damuwar ku. Bari in taimaka wajen magance wannan matsala.",
                "ig": "Aghọtara m ihe na-echegbu gị. Ka m nyere gị aka idozi nsogbu a."
            }
        }
    
    def detect_language(self, text: str) -> str:
        """Simple language detection based on keywords"""
        text_lower = text.lower()
        
        # Yoruba indicators
        if any(word in text_lower for word in ["bawo", "se", "emi", "won", "nibo"]):
            return "yo"
        
        # Hausa indicators  
        elif any(word in text_lower for word in ["yaya", "ina", "mu", "ku", "wannan"]):
            return "ha"
        
        # Igbo indicators
        elif any(word in text_lower for word in ["kedu", "ndewo", "m", "gi", "nke"]):
            return "ig"
        
        # Default to English
        return "en"
    
    def translate(self, key: str, language: str = "en") -> str:
        """Get translation for a key in specified language"""
        if key in self.translations and language in self.translations[key]:
            return self.translations[key][language]
        return self.translations.get(key, {}).get("en", key)

language_service = LanguageService()