#!/usr/bin/env python3
"""Quick test script to verify server startup and API functionality"""

import asyncio
import httpx
from app.services.whatsapp import whatsapp_service
from app.services.meta_ai import meta_ai_service

async def test_services():
    print("🧪 Testing HaloAgent Services...")
    
    # Test Meta AI
    print("\n1. Testing Meta AI (Groq)...")
    try:
        response = await meta_ai_service.generate_response("Hello, how are you?")
        print(f"✅ Meta AI Response: {response[:100]}...")
    except Exception as e:
        print(f"❌ Meta AI Error: {e}")
    
    # Test WhatsApp API structure (won't actually send)
    print("\n2. Testing WhatsApp Service...")
    try:
        # This will fail but shows if service is properly configured
        result = await whatsapp_service.send_text("test", "test message")
        print(f"✅ WhatsApp Service: Configured correctly")
    except Exception as e:
        if "Invalid phone number" in str(e) or "400" in str(e):
            print(f"✅ WhatsApp Service: API configured (expected error for test number)")
        else:
            print(f"❌ WhatsApp Error: {e}")
    
    print("\n🎉 Service tests completed!")

if __name__ == "__main__":
    asyncio.run(test_services())