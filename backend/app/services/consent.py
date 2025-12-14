"""
Consent inference service - handles natural language consent detection
"""
from typing import Tuple
import re

class ConsentService:
    
    # Strong consent indicators
    STRONG_CONSENT = [
        "sure", "ok", "okay", "yes", "yep", "yeah", "sounds good", 
        "go ahead", "do it", "please", "that's fine", "alright", 
        "cool", "perfect", "great"
    ]
    
    # Weak/ambiguous consent
    WEAK_CONSENT = ["maybe", "i guess", "fine", "whatever"]
    
    # Clear rejection
    REJECTION = ["no", "nope", "nah", "don't", "stop", "never"]
    
    def infer_consent(self, message: str) -> Tuple[bool, float, str]:
        """
        Infer consent from natural language.
        
        Returns:
            (has_consent, confidence, interpretation)
        """
        msg_lower = message.lower().strip()
        
        # Check for rejection first
        if any(word in msg_lower for word in self.REJECTION):
            return (False, 0.95, "rejection")
        
        # Check for strong consent
        if any(phrase in msg_lower for phrase in self.STRONG_CONSENT):
            return (True, 0.9, "strong_consent")
        
        # Check for weak consent
        if any(phrase in msg_lower for phrase in self.WEAK_CONSENT):
            return (True, 0.6, "weak_consent")
        
        # Ambiguous
        return (False, 0.3, "ambiguous")
    
    def should_ask_clarification(self, confidence: float) -> bool:
        """Determine if we should ask for clarification"""
        return 0.5 <= confidence < 0.8

consent_service = ConsentService()
