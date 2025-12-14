-- Add state tracking columns to contacts table
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS current_stage VARCHAR(50) DEFAULT 'NONE',
ADD COLUMN IF NOT EXISTS last_intent VARCHAR(50) DEFAULT 'UNKNOWN',
ADD COLUMN IF NOT EXISTS last_interaction_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS context_data JSONB DEFAULT '{}';

-- Or create a separate table if preferred, but extending contacts is cleaner for CRM state.
-- context_data will store things like 'draft_order_items' or 'pending_feedback'.
