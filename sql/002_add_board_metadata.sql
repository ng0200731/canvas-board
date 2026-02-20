-- Add metadata fields to boards table
ALTER TABLE boards ADD COLUMN sales_team TEXT DEFAULT '';
ALTER TABLE boards ADD COLUMN customer TEXT DEFAULT '';
ALTER TABLE boards ADD COLUMN brand_site TEXT DEFAULT '';
ALTER TABLE boards ADD COLUMN category TEXT DEFAULT '';
