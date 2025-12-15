"""
Quick insert demo business directly to Supabase
"""
from app.db.supabase_client import supabase

business_data = {
    "business_id": "sweetcrumbs_001",
    "business_name": "SweetCrumbs Cakes",
    "whatsapp_number": "+14155238886",
    "default_language": "en",
    "supported_languages": ["en", "yo"],
    "inventory": [
        {"name": "Chocolate Cake", "price": 5000, "available": True, "description": "Rich chocolate cake", "image_url": "https://example.com/chocolate-cake.jpg"},
        {"name": "Vanilla Cake", "price": 4500, "available": True, "description": "Classic vanilla", "image_url": "https://example.com/vanilla-cake.jpg"},
        {"name": "Red Velvet Cake", "price": 5500, "available": True, "description": "Smooth red velvet", "image_url": "https://example.com/red-velvet-cake.jpg"}
    ],
    "active": True
}

try:
    result = supabase.table("businesses").insert(business_data).execute()
    print("SUCCESS! Business created:")
    print(result.data)
except Exception as e:
    print(f"Error: {e}")
    print("\nIf table doesn't exist, run create_businesses_table.sql in Supabase first!")
