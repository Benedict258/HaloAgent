ALTER TABLE users
    ALTER COLUMN phone_number TYPE VARCHAR(32);

ALTER TABLE contacts
    ALTER COLUMN phone_number TYPE VARCHAR(32);

ALTER TABLE orders
    ALTER COLUMN delivery_phone TYPE VARCHAR(32);
