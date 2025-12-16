-- Create businesses table for multi-business support
CREATE TABLE IF NOT EXISTS public.businesses (
    id SERIAL PRIMARY KEY,
    business_id VARCHAR(255) UNIQUE NOT NULL,
    business_name VARCHAR(255) NOT NULL,
    whatsapp_number VARCHAR(50) UNIQUE NOT NULL,
    owner_user_id INTEGER REFERENCES public.users(id),
    default_language VARCHAR(10) DEFAULT 'en',
    supported_languages JSONB DEFAULT '["en"]'::jsonb,
    inventory JSONB DEFAULT '[]'::jsonb,
    payment_instructions JSONB DEFAULT '{}'::jsonb,
    business_hours JSONB,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure legacy tables gain payment instructions column
ALTER TABLE public.businesses
ADD COLUMN IF NOT EXISTS payment_instructions JSONB DEFAULT '{}'::jsonb;

-- Create index on whatsapp_number for fast lookups
CREATE INDEX IF NOT EXISTS idx_businesses_whatsapp ON public.businesses(whatsapp_number);
CREATE INDEX IF NOT EXISTS idx_businesses_business_id ON public.businesses(business_id);

-- Update contacts table to link to businesses
ALTER TABLE public.contacts 
ADD COLUMN IF NOT EXISTS business_id VARCHAR(255) REFERENCES public.businesses(business_id);

-- Create index for contact lookups by business
CREATE INDEX IF NOT EXISTS idx_contacts_business_phone ON public.contacts(business_id, phone_number);

-- Add consent fields to contacts
ALTER TABLE public.contacts 
ADD COLUMN IF NOT EXISTS opt_in BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'unconsented',
ADD COLUMN IF NOT EXISTS consent_phrase TEXT,
ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS order_count INTEGER DEFAULT 0;

-- Update orders table to link to businesses
ALTER TABLE public.orders 
ADD COLUMN IF NOT EXISTS business_id VARCHAR(255) REFERENCES public.businesses(business_id);

-- Insert demo business
INSERT INTO public.businesses (
    business_id,
    business_name,
    whatsapp_number,
    default_language,
    supported_languages,
    inventory,
    payment_instructions,
    active
) VALUES (
    'sweetcrumbs_001',
    'SweetCrumbs Cakes',
    '+14155238886',
    'en',
    '["en", "yo"]'::jsonb,
    '[
        {"name": "Chocolate Cake", "price": 5000, "available": true, "description": "Rich chocolate cake"},
        {"name": "Vanilla Cake", "price": 4500, "available": true, "description": "Classic vanilla"},
        {"name": "Red Velvet Cake", "price": 5500, "available": true, "description": "Smooth red velvet"}
    ]'::jsonb,
    '{
        "bank": "GTBank",
        "account_name": "SweetCrumbs Cakes",
        "account_number": "0123456789",
        "notes": "Send a quick WhatsApp message once you transfer so we can confirm."
    }'::jsonb,
    true
) ON CONFLICT (business_id) DO NOTHING;

-- Grant permissions
GRANT ALL ON public.businesses TO authenticated;
GRANT ALL ON public.businesses TO anon;
