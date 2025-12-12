from supabase import create_client, Client
from app.core.config import settings

def get_supabase() -> Client:
    """Get Supabase client instance"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_supabase_admin() -> Client:
    """Get Supabase admin client instance"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

# For backward compatibility
supabase = get_supabase()
supabase_admin = get_supabase_admin()