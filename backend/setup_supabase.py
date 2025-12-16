from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

def create_tables():
    """Create database tables in Supabase"""
    
    # Users table
    users_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        phone_number VARCHAR(20) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        business_name VARCHAR(200),
        preferred_language VARCHAR(10) DEFAULT 'en',
        is_active BOOLEAN DEFAULT true,
        is_verified BOOLEAN DEFAULT false,
        whatsapp_phone_number_id VARCHAR(50),
        whatsapp_business_account_id VARCHAR(50),
        whatsapp_access_token TEXT,
        whatsapp_webhook_verify_token VARCHAR(100),
        notification_preferences TEXT,
        business_hours TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        last_login TIMESTAMP WITH TIME ZONE
    );
    """
    
    # Businesses table
    businesses_sql = """
    CREATE TABLE IF NOT EXISTS businesses (
        id SERIAL PRIMARY KEY,
        business_id VARCHAR(255) UNIQUE NOT NULL,
        business_name VARCHAR(255) NOT NULL,
        whatsapp_number VARCHAR(50) UNIQUE NOT NULL,
        owner_user_id INTEGER REFERENCES users(id),
        default_language VARCHAR(10) DEFAULT 'en',
        supported_languages JSONB DEFAULT '["en"]'::jsonb,
        inventory JSONB DEFAULT '[]'::jsonb,
        payment_instructions JSONB DEFAULT '{}'::jsonb,
        business_hours JSONB,
        active BOOLEAN DEFAULT true,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_businesses_whatsapp ON businesses(whatsapp_number);
    CREATE INDEX IF NOT EXISTS idx_businesses_business_id ON businesses(business_id);
    """

    # Contacts table
    contacts_sql = """
    CREATE TABLE IF NOT EXISTS contacts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        phone_number VARCHAR(20) NOT NULL,
        name VARCHAR(200),
        preferred_language VARCHAR(10) DEFAULT 'en',
        loyalty_points INTEGER DEFAULT 0,
        total_orders INTEGER DEFAULT 0,
        total_spent DECIMAL(10,2) DEFAULT 0.00,
        last_order_date TIMESTAMP WITH TIME ZONE,
        consent_given BOOLEAN DEFAULT false,
        consent_date TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Orders table
    orders_sql = """
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        contact_id INTEGER REFERENCES contacts(id),
        order_number VARCHAR(50) UNIQUE NOT NULL,
        items TEXT NOT NULL,
        total_amount DECIMAL(10,2) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        delivery_address TEXT,
        delivery_phone VARCHAR(20),
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Messages table
    messages_sql = """
    CREATE TABLE IF NOT EXISTS message_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        contact_id INTEGER REFERENCES contacts(id),
        message_id VARCHAR(100),
        direction VARCHAR(10) NOT NULL,
        message_type VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        status VARCHAR(20) DEFAULT 'sent',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Feedback table
    feedback_sql = """
    CREATE TABLE IF NOT EXISTS feedback (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        contact_id INTEGER REFERENCES contacts(id),
        order_id INTEGER REFERENCES orders(id),
        rating INTEGER CHECK (rating >= 1 AND rating <= 5),
        comment TEXT,
        sentiment VARCHAR(20),
        resolved BOOLEAN DEFAULT false,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Rewards table
    rewards_sql = """
    CREATE TABLE IF NOT EXISTS rewards (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        contact_id INTEGER REFERENCES contacts(id),
        reward_type VARCHAR(50) NOT NULL,
        points_earned INTEGER DEFAULT 0,
        points_redeemed INTEGER DEFAULT 0,
        description TEXT,
        expires_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    tables = [
        ("users", users_sql),
        ("businesses", businesses_sql),
        ("contacts", contacts_sql),
        ("orders", orders_sql),
        ("message_logs", messages_sql),
        ("feedback", feedback_sql),
        ("rewards", rewards_sql)
    ]
    
    for table_name, sql in tables:
        try:
            result = supabase.rpc('exec_sql', {'sql': sql}).execute()
            print(f"✅ Created table: {table_name}")
        except Exception as e:
            print(f"❌ Error creating {table_name}: {e}")

if __name__ == "__main__":
    print("Setting up Supabase database...")
    create_tables()
    print("Database setup complete!")