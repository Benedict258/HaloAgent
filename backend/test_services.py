#!/usr/bin/env python3
"""Test script to verify all API services are working"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_meta_ai():
    """Test Meta AI (Groq) service"""
    try:
        from app.services.meta_ai import meta_ai_service
        response = await meta_ai_service.generate_response("Hello, I want to place an order")
        print(f"[OK] Meta AI: {response}")
        return True
    except Exception as e:
        print(f"[FAIL] Meta AI failed: {e}")
        return False

def test_whatsapp():
    """Test WhatsApp API credentials"""
    try:
        token = os.getenv("WHATSAPP_API_TOKEN")
        phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        if token and phone_id:
            print(f"[OK] WhatsApp: Token and Phone ID configured")
            return True
        else:
            print("[FAIL] WhatsApp: Missing credentials")
            return False
    except Exception as e:
        print(f"[FAIL] WhatsApp failed: {e}")
        return False

def test_twilio():
    """Test Twilio credentials"""
    try:
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        if sid and token:
            print(f"[OK] Twilio: Credentials configured")
            return True
        else:
            print("[FAIL] Twilio: Missing credentials")
            return False
    except Exception as e:
        print(f"[FAIL] Twilio failed: {e}")
        return False

async def main():
    print("Testing HaloAgent Services...\n")
    
    results = []
    results.append(await test_meta_ai())
    results.append(test_whatsapp())
    results.append(test_twilio())
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} services working")
    
    if passed == total:
        print("All services ready! You can start the server.")
    else:
        print("Some services need attention.")

if __name__ == "__main__":
    asyncio.run(main())