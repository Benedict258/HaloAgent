"""
Create demo business for testing
"""
import asyncio
from app.services.business import business_service

async def create_demo():
    print("Creating demo business: SweetCrumbs Cakes...\n")
    
    business_data = {
        "business_id": "sweetcrumbs_001",
        "business_name": "SweetCrumbs Cakes",
        "whatsapp_number": "+14155238886",  # Twilio WhatsApp Sandbox
        "default_language": "en",
        "supported_languages": ["en", "yo"],
        "inventory": [
            {
                "name": "Chocolate Cake",
                "price": 5000,
                "available": True,
                "description": "Rich chocolate cake"
            },
            {
                "name": "Vanilla Cake",
                "price": 4500,
                "available": True,
                "description": "Classic vanilla"
            },
            {
                "name": "Red Velvet Cake",
                "price": 5500,
                "available": True,
                "description": "Smooth red velvet"
            }
        ],
        "active": True
    }
    
    business = await business_service.create_demo_business(business_data)
    
    if business:
        print("✅ Business created successfully!")
        print(f"\nBusiness ID: {business['business_id']}")
        print(f"Name: {business['business_name']}")
        print(f"WhatsApp: {business['whatsapp_number']}")
        print(f"\nInventory ({len(business['inventory'])} items):")
        for item in business['inventory']:
            print(f"  - {item['name']}: ₦{item['price']}")
        
        print("\n📱 Next Steps:")
        print("1. Send a WhatsApp message to:", business['whatsapp_number'])
        print("2. Customer contact will auto-create")
        print("3. AI will handle the conversation")
        print("4. Check dashboard for orders")
    else:
        print("❌ Failed to create business")

if __name__ == "__main__":
    asyncio.run(create_demo())
