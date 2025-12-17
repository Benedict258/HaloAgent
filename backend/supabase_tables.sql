-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    phone_number VARCHAR(32) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    business_name VARCHAR(200),
    business_id VARCHAR(255) REFERENCES public.businesses(business_id),
    account_type VARCHAR(20) NOT NULL DEFAULT 'business',
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
    last_login TIMESTAMP WITH TIME ZONE,
    UNIQUE (email, account_type),
    UNIQUE (phone_number, account_type)
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);
CREATE INDEX IF NOT EXISTS idx_users_business_id ON users(business_id);
CREATE INDEX IF NOT EXISTS idx_users_account_type ON users(account_type);

-- Businesses table
CREATE TABLE businesses (
    id SERIAL PRIMARY KEY,
    business_id VARCHAR(255) UNIQUE NOT NULL,
    business_name VARCHAR(255) NOT NULL,
    whatsapp_number VARCHAR(50) UNIQUE NOT NULL,
    owner_user_id INTEGER REFERENCES users(id),
    description TEXT,
    brand_voice TEXT,
    default_language VARCHAR(10) DEFAULT 'en',
    supported_languages JSONB DEFAULT '["en"]'::jsonb,
    inventory JSONB DEFAULT '[]'::jsonb,
    payment_instructions JSONB DEFAULT '{}'::jsonb,
    settlement_account JSONB DEFAULT '{}'::jsonb,
    business_hours JSONB,
    pickup_address TEXT,
    pickup_instructions TEXT,
    settings JSONB DEFAULT '{}'::jsonb,
    integration_preferences JSONB DEFAULT '{}'::jsonb,
    webhook_url TEXT,
    sandbox_code VARCHAR(60),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_businesses_whatsapp ON businesses(whatsapp_number);
CREATE INDEX IF NOT EXISTS idx_businesses_business_id ON businesses(business_id);

-- Contacts table
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    phone_number VARCHAR(32) NOT NULL,
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

-- Orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    contact_id INTEGER REFERENCES contacts(id),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    items TEXT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    delivery_address TEXT,
    delivery_phone VARCHAR(32),
    notes TEXT,
    payment_method VARCHAR(50) DEFAULT 'bank_transfer',
    payment_instructions_sent BOOLEAN DEFAULT FALSE,
    payment_receipt_url TEXT,
    payment_receipt_uploaded_at TIMESTAMP WITH TIME ZONE,
    payment_receipt_analysis JSONB,
    payment_confirmed_at TIMESTAMP WITH TIME ZONE,
    payment_notes TEXT,
    payment_reference VARCHAR(50),
    payment_reference_generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ready_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    fulfillment_type VARCHAR(20) DEFAULT 'pickup',
    channel VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_payment_reference ON orders(payment_reference) WHERE payment_reference IS NOT NULL;

-- Messages table
CREATE TABLE message_logs (
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

-- Feedback table
CREATE TABLE feedback (
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

-- Rewards table
CREATE TABLE rewards (
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

-- Notification read receipts
CREATE TABLE notification_reads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id VARCHAR(100) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    read_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (business_id, notification_type, entity_id)
);

-- Vision analysis logs
CREATE TABLE vision_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id VARCHAR(100) NOT NULL,
    contact_id INTEGER REFERENCES contacts(id),
    order_id INTEGER REFERENCES orders(id),
    analysis_type VARCHAR(50) NOT NULL,
    media_url TEXT NOT NULL,
    analysis JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vision_business ON vision_analysis_results(business_id);
CREATE INDEX IF NOT EXISTS idx_vision_contact ON vision_analysis_results(contact_id);

-- Customer escalations table
CREATE TABLE escalations (
    id SERIAL PRIMARY KEY,
    business_id VARCHAR(255) NOT NULL,
    contact_id INTEGER REFERENCES contacts(id),
    phone_number VARCHAR(32),
    issue_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_escalations_business ON escalations(business_id);
CREATE INDEX IF NOT EXISTS idx_escalations_status ON escalations(status);