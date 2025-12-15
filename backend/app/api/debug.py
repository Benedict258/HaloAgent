from fastapi import APIRouter
from app.services.agent.supabase_tools import supabase_tools
from app.services.media import media_service

router = APIRouter()

@router.get("/debug/inventory/{business_id}")
async def debug_inventory(business_id: str):
    """Check what inventory AI sees"""
    result = await supabase_tools.get_business_inventory(business_id)
    return {"raw_result": result}

@router.post("/debug/send-image")
async def debug_send_image(phone: str, business_id: str = "sweetcrumbs_001"):
    """Test sending product image"""
    import json
    
    # Get inventory
    inventory_result = await supabase_tools.get_business_inventory(business_id)
    inventory_data = json.loads(inventory_result)
    
    if inventory_data.get("status") != "success":
        return {"error": "No inventory found"}
    
    products = inventory_data.get("inventory", [])
    
    if not products:
        return {"error": "No products in inventory"}
    
    # Try sending first product
    product = products[0]
    success = await media_service.send_product_image(phone, product, "whatsapp")
    
    return {
        "product": product,
        "sent": success,
        "has_image_url": bool(product.get("image_url"))
    }

@router.get("/debug/business/{business_id}")
async def debug_business(business_id: str):
    """Check if business exists"""
    from app.services.business import business_service
    business = await business_service.get_business_by_id(business_id)
    return {"business": business}

@router.get("/debug/contact/{phone}")
async def debug_contact(phone: str, business_id: str = "sweetcrumbs_001"):
    """Check if contact exists"""
    result = await supabase_tools.get_contact(phone, business_id)
    return {"raw_result": result}
