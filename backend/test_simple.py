"""
Simple test to verify agent responses are natural
"""
import asyncio
from app.services.agent.core import agent

async def test_simple():
    phone = "+2349012345678"
    
    print("=== Testing Natural Responses ===\n")
    
    # Test 1: Greeting
    print("User: hi")
    response = await agent.run("hi", phone, "First time user")
    print(f"Agent: {response}\n")
    
    # Verify no technical language
    bad_words = ["tool_call", "intent_classifier", "action", "parameters", "JSON"]
    has_technical = any(word.lower() in response.lower() for word in bad_words)
    
    if has_technical:
        print("❌ FAILED: Technical language detected in response")
    else:
        print("✅ PASSED: Response is natural and conversational")

if __name__ == "__main__":
    asyncio.run(test_simple())
