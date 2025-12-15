"""
Upload product images to Supabase Storage
"""
from app.db.supabase_client import supabase
import requests

def upload_image_from_url(image_url: str, filename: str):
    """Download image from URL and upload to Supabase"""
    
    # Download image
    response = requests.get(image_url)
    image_data = response.content
    
    # Upload to Supabase Storage
    result = supabase.storage.from_('product-images').upload(
        filename,
        image_data,
        file_options={"content-type": "image/jpeg"}
    )
    
    # Get public URL
    public_url = supabase.storage.from_('product-images').get_public_url(filename)
    
    return public_url

# Example: Upload sample images
if __name__ == "__main__":
    # Using placeholder images for demo
    images = [
        {
            "url": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800",
            "filename": "chocolate-cake.jpg",
            "product": "Chocolate Cake"
        },
        {
            "url": "https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=800",
            "filename": "vanilla-cake.jpg",
            "product": "Vanilla Cake"
        },
        {
            "url": "https://images.unsplash.com/photo-1586985289688-ca3cf47d3e6e?w=800",
            "filename": "red-velvet-cake.jpg",
            "product": "Red Velvet Cake"
        }
    ]
    
    print("Uploading product images to Supabase Storage...\n")
    
    uploaded_urls = {}
    
    for img in images:
        try:
            print(f"Uploading {img['product']}...")
            public_url = upload_image_from_url(img['url'], img['filename'])
            uploaded_urls[img['product']] = public_url
            print(f"✓ {img['product']}: {public_url}\n")
        except Exception as e:
            print(f"✗ Error uploading {img['product']}: {e}\n")
    
    # Update business inventory with real URLs
    print("\nNow update your business inventory with these URLs:")
    print("\nSQL:")
    print(f"""
UPDATE businesses 
SET inventory = '[
  {{"name": "Chocolate Cake", "price": 5000, "description": "Rich chocolate cake", "image_url": "{uploaded_urls.get('Chocolate Cake', '')}", "available": true}},
  {{"name": "Vanilla Cake", "price": 4500, "description": "Classic vanilla", "image_url": "{uploaded_urls.get('Vanilla Cake', '')}", "available": true}},
  {{"name": "Red Velvet Cake", "price": 5500, "description": "Smooth red velvet", "image_url": "{uploaded_urls.get('Red Velvet Cake', '')}", "available": true}}
]'::jsonb
WHERE business_id = 'sweetcrumbs_001';
""")
