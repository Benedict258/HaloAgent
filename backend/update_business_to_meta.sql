-- Update business to use Meta WhatsApp Business API instead of Twilio
UPDATE public.businesses 
SET whatsapp_number = '+909862845543640'
WHERE business_id = 'sweetcrumbs_001';

-- Verify update
SELECT business_id, business_name, whatsapp_number 
FROM public.businesses;
