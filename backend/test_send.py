import asyncio
from app.services.whatsapp import whatsapp_service

async def test_send():
    phone = "2349048377499" # The user's number
    print(f"Attempting to send test message to {phone}...")
    
    success = await whatsapp_service.send_text(phone, "Hello! This is a direct test from HaloAgent backend.")
    
    if success:
        print("[SUCCESS] Message request sent successfully!")
    else:
        print("[FAILED] Message request failed. Check logs for details.")

if __name__ == "__main__":
    asyncio.run(test_send())
