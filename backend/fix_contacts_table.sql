-- Fix contacts table schema for business onboarding
-- Add missing columns that contact service expects

ALTER TABLE public.contacts 
ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS business_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS opt_in BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'unconsented',
ADD COLUMN IF NOT EXISTS consent_phrase TEXT,
ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS order_count INTEGER DEFAULT 0;

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_contacts_business_phone ON public.contacts(business_id, phone_number);

-- Verify columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'contacts' 
ORDER BY ordinal_position;
