-- Migration: Add is_superuser field to users table
-- Date: 2025-01-15
-- Description: Adds is_superuser boolean field for cross-tenant super admin access

-- Add the is_superuser column with default false
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;

-- Create index for quick superuser lookups
CREATE INDEX IF NOT EXISTS idx_users_superuser ON users(is_superuser) WHERE is_superuser = TRUE;

-- Note: To make a user a superuser, run:
-- UPDATE users SET is_superuser = TRUE WHERE email = 'your-admin@example.com';
