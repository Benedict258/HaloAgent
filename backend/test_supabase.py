from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Test connection
try:
    result = supabase.table("users").select("*").limit(1).execute()
    print("✅ Supabase connection successful!")
    print(f"Tables accessible: {len(result.data) >= 0}")
except Exception as e:
    print(f"❌ Connection error: {e}")
    print("Create tables manually in Supabase dashboard")