-- Link users table to businesses table
ALTER TABLE users ADD COLUMN IF NOT EXISTS business_id VARCHAR(100);

-- Create a business for existing users (if any)
-- You'll need to run this after creating businesses for each user
-- For now, link to demo business
UPDATE users SET business_id = 'sweetcrumbs_001' WHERE business_id IS NULL;

-- Add foreign key constraint
ALTER TABLE users ADD CONSTRAINT fk_user_business 
  FOREIGN KEY (business_id) REFERENCES businesses(business_id);
