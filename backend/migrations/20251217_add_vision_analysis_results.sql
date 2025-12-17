-- Ensure vision_analysis_results table exists for /api/vision endpoints
CREATE TABLE IF NOT EXISTS public.vision_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id VARCHAR(100) NOT NULL,
    contact_id INTEGER REFERENCES public.contacts(id),
    order_id INTEGER REFERENCES public.orders(id),
    analysis_type VARCHAR(50) NOT NULL,
    media_url TEXT NOT NULL,
    analysis JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vision_business ON public.vision_analysis_results(business_id);
CREATE INDEX IF NOT EXISTS idx_vision_contact ON public.vision_analysis_results(contact_id);
