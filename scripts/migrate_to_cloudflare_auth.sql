-- Migrate user schema: username/password → Cloudflare email auth
-- Backup first: docker exec rri_postgres pg_dump -U rri_user rri_orchestrator > backup.sql
-- WARNING: Drops username, hashed_password, full_name, is_admin

BEGIN;

-- Add new columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'researcher';

-- Migrate data
UPDATE users 
SET display_name = COALESCE(full_name, username, 'User')
WHERE display_name IS NULL;

UPDATE users 
SET role = CASE 
    WHEN is_admin = true THEN 'admin' 
    ELSE 'researcher' 
END;

ALTER TABLE users ALTER COLUMN display_name SET NOT NULL;

-- Drop old columns
ALTER TABLE users DROP COLUMN IF EXISTS username;
ALTER TABLE users DROP COLUMN IF EXISTS hashed_password;
ALTER TABLE users DROP COLUMN IF EXISTS full_name;
ALTER TABLE users DROP COLUMN IF EXISTS is_admin;

-- Verify
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'users'
ORDER BY ordinal_position;

SELECT id, email, display_name, role, is_active, created_at
FROM users;

COMMIT;
-- To rollback: ROLLBACK;
