-- Add pickup logistics + settlement account columns to businesses
ALTER TABLE public.businesses
    ADD COLUMN IF NOT EXISTS pickup_address TEXT,
    ADD COLUMN IF NOT EXISTS pickup_instructions TEXT,
    ADD COLUMN IF NOT EXISTS settlement_account JSONB DEFAULT '{}'::jsonb;

-- Ensure pickup + settlement data replicate to demo row
UPDATE public.businesses
SET pickup_address = COALESCE(pickup_address, '12 Adebisi Street, Lekki Phase 1, Lagos'),
    pickup_instructions = COALESCE(pickup_instructions, 'Pickup window 10am-6pm Tue-Sun. Call ahead for rush orders.'),
    settlement_account = CASE
        WHEN settlement_account IS NULL OR settlement_account = '{}'::jsonb THEN jsonb_build_object(
            'bank', 'GTBank',
            'account_name', business_name,
            'account_number', '0123456789',
            'notes', 'Send a WhatsApp message once you transfer so we can confirm.'
        )
        ELSE settlement_account
    END
WHERE business_id = 'sweetcrumbs_001';
