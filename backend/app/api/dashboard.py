from fastapi import APIRouter, HTTPException
from app.db.supabase_client import supabase
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Get total orders
        orders = supabase.table("orders").select("*", count="exact").execute()
        total_orders = orders.count
        
        # Get total contacts
        contacts = supabase.table("contacts").select("*", count="exact").execute()
        total_contacts = contacts.count
        
        # Get pending orders
        pending = supabase.table("orders").select("*", count="exact").eq("status", "pending").execute()
        pending_orders = pending.count
        
        # Get total revenue
        completed = supabase.table("orders").select("total_amount").eq("status", "completed").execute()
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
async def get_recent_orders(limit: int = 10):
    """Get recent orders"""
    try:
        result = supabase.table("orders")\
            .select("*, contacts(name, phone)")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    except Exception as e:
        logger.error(f"Recent orders error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/inventory")
async def get_inventory(business_id: str = "sweetcrumbs_001"):
    """Get inventory for a business"""
    try:
        result = supabase.table("businesses")\
            .select("inventory")\
            .eq("business_id", business_id)\
            .single()\
            .execute()
        return result.data.get("inventory", [])
    except Exception as e:
        logger.error(f"Inventory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
