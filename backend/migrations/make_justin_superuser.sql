-- Migration: Make weilbach@gmail.com a superuser
-- Date: 2025-01-15
-- Description: Sets is_superuser to TRUE for the admin user in Lavacake tenant

-- Update the user to be a superuser (only for Lavacake tenant)
UPDATE users
SET is_superuser = TRUE,
    first_name = 'Justin',
    last_name = 'Weilbach'
WHERE email = 'weilbach@gmail.com'
  AND tenant_id = (SELECT id FROM tenants WHERE slug = 'lavacake' OR name ILIKE '%lavacake%' LIMIT 1);

-- Verify the update
SELECT u.id, u.email, u.first_name, u.last_name, u.role, u.is_superuser, t.name as tenant_name
FROM users u
JOIN tenants t ON u.tenant_id = t.id
WHERE u.email = 'weilbach@gmail.com';
