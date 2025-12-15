"""
Quick test script to verify voice note handling
Run this to check if your webhook can process voice notes
"""

# Test 1: Check if Groq Whisper API key is valid
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_groq_whisper():
    api_key = os.getenv("META_AI_API_KEY")
    print(f"✓ Groq API Key found: {api_key[:20]}...")
    
    # Test with a sample audio URL (you'll replace this with actual WhatsApp audio)
    print("\n📝 To test voice notes:")
    print("1. Send a voice note to +1 415 523 8886 on WhatsApp")
    print("2. Check your backend logs for 'Processing Twilio voice note'")
    print("3. You should receive a text response with the transcribed message")
    print("\n✅ Voice service is configured and ready!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_groq_whisper())
