ALTER TABLE businesses
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS brand_voice TEXT,
    ADD COLUMN IF NOT EXISTS supported_languages JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS settings JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS integration_preferences JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS twilio_phone VARCHAR(32),
    ADD COLUMN IF NOT EXISTS sandbox_code VARCHAR(32),
    ADD COLUMN IF NOT EXISTS webhook_url TEXT;
