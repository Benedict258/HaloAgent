from fastapi import APIRouter, HTTPException, Depends
from app.db.supabase_client import supabase
import logging
from app.api.auth import require_business_user

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(require_business_user)):
    """Get dashboard statistics"""
    try:
        business_id = current_user["business_id"]
        # Get total orders
        orders = supabase.table("orders").select("*", count="exact").eq("business_id", business_id).execute()
        total_orders = orders.count
        
        # Get total contacts
        contacts = supabase.table("contacts").select("*", count="exact").eq("business_id", business_id).execute()
        total_contacts = contacts.count
        
        # Get pending orders
        pending = (
            supabase
            .table("orders")
            .select("*", count="exact")
            .eq("business_id", business_id)
            .eq("status", "pending")
            .execute()
        )
        pending_orders = pending.count
        
        # Get total revenue
        completed = (
            supabase
            .table("orders")
            .select("total_amount")
            .eq("status", "completed")
            .eq("business_id", business_id)
            .execute()
        )
        total_revenue = sum(order.get("total_amount", 0) for order in completed.data)
        
        return {
            "total_orders": total_orders,
            "total_contacts": total_contacts,
            "pending_orders": pending_orders,
            "total_revenue": total_revenue
        }
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/recent-orders")
async def get_recent_orders(limit: int = 10, current_user: dict = Depends(require_business_user)):
    """Get recent orders"""
    try:
        business_id = current_user["business_id"]
        result = supabase.table("orders")\
            .select("*, contacts(name, phone)")\
            .eq("business_id", business_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    except Exception as e:
        logger.error(f"Recent orders error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/inventory")
async def get_inventory(current_user: dict = Depends(require_business_user)):
    """Get inventory for a business"""
    try:
        business_id = current_user["business_id"]
        result = supabase.table("businesses")\
            .select("inventory")\
            .eq("business_id", business_id)\
            .single()\
            .execute()
        return result.data.get("inventory", [])
    except Exception as e:
        logger.error(f"Inventory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
