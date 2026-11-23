-- =============================================================================
-- Converge AI — PostgreSQL Database & Two-Role Provisioning Script (GAP-02)
-- Run this script as a PostgreSQL superuser (e.g. postgres)
-- =============================================================================

-- 1. Create Migration/DDL Owner Role (converge_ai_owner)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'converge_ai_owner') THEN
        CREATE ROLE converge_ai_owner WITH LOGIN PASSWORD 'local_owner_secret' NOSUPERUSER NOCREATEDB NOCREATEROLE;
        RAISE NOTICE 'Role converge_ai_owner created';
    ELSE
        RAISE NOTICE 'Role converge_ai_owner already exists';
    END IF;
END
$$;

-- 2. Create Runtime Application Role (converge_ai_app) - Least Privilege (DML only)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'converge_ai_app') THEN
        CREATE ROLE converge_ai_app WITH LOGIN PASSWORD 'local_app_secret' NOSUPERUSER NOCREATEDB NOCREATEROLE;
        RAISE NOTICE 'Role converge_ai_app created';
    ELSE
        RAISE NOTICE 'Role converge_ai_app already exists';
    END IF;
END
$$;

-- 3. Create Application Database (converge_ai_db) owned by converge_ai_owner
SELECT 'CREATE DATABASE converge_ai_db WITH OWNER = converge_ai_owner ENCODING = ''UTF8'''
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'converge_ai_db')\gexec

-- 4. Create Isolated Test Database (converge_ai_test) owned by converge_ai_owner
SELECT 'CREATE DATABASE converge_ai_test WITH OWNER = converge_ai_owner ENCODING = ''UTF8'''
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'converge_ai_test')\gexec

-- 5. Revoke Public creation on both databases and grant Connect to converge_ai_app
\c converge_ai_db
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE converge_ai_db TO converge_ai_app;

\c converge_ai_test
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE converge_ai_test TO converge_ai_app;
