"""
Test conversational flow with HaloAgent
"""
import asyncio
from app.services.agent.core import agent

async def test_conversation():
    phone = "+2349012345678"
    
    print("=== Testing HaloAgent Conversational Flow ===\n")
    
    # Test 1: Natural consent
    print("User: sure")
    response = await agent.run("sure", phone, "First time user")
    print(f"Agent: {response}\n")
    
    # Test 2: Order request
    print("User: I want jollof rice")
    response = await agent.run("I want jollof rice", phone, "Phone: +2349012345678")
    print(f"Agent: {response}\n")
    
    # Test 3: Order details
    print("User: 2 plates, deliver to Ikeja")
    response = await agent.run("2 plates, deliver to Ikeja", phone, "Phone: +2349012345678")
    print(f"Agent: {response}\n")
    
    # Test 4: Confirmation
    print("User: yes")
    response = await agent.run("yes", phone, "Phone: +2349012345678")
    print(f"Agent: {response}\n")
    
    # Test 5: Check points
    print("User: how many points do I have?")
    response = await agent.run("how many points do I have?", phone, "Phone: +2349012345678")
    print(f"Agent: {response}\n")

if __name__ == "__main__":
    asyncio.run(test_conversation())
