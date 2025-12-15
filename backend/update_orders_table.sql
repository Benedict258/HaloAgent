-- Add new columns to orders table for complete workflow
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50) DEFAULT 'bank_transfer';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_instructions_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_receipt_url TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_confirmed_at TIMESTAMP;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_notes TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS ready_at TIMESTAMP;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivery_address TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS fulfillment_type VARCHAR(20) DEFAULT 'pickup';

-- Update status enum to include all workflow states
-- Note: PostgreSQL doesn't allow ALTER TYPE easily, so we'll use VARCHAR
ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR(50);

-- Add business_id if not exists
ALTER TABLE orders ADD COLUMN IF NOT EXISTS business_id VARCHAR(100);
UPDATE orders SET business_id = 'sweetcrumbs_001' WHERE business_id IS NULL;
