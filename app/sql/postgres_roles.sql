-- EXAMPLE least-privilege roles for PostgreSQL. Adapt it; don't run it blindly.
-- Run as a superuser, e.g.:
--   psql -h <db-host> -U postgres -d campus -v admin_pw="'...'" -v rw_pw="'...'" -v ro_pw="'...'" -f postgres_roles.sql
-- Passwords come from your secret manager, never from this file.

-- Enforce a password policy on the server too (PostgreSQL has no built-in
-- length rule: use the passwordcheck module, or check before you set it).
SET password_encryption = 'scram-sha-256';

CREATE ROLE admin   LOGIN PASSWORD :admin_pw CREATEROLE;
CREATE ROLE app_rw  LOGIN PASSWORD :rw_pw   CONNECTION LIMIT 50;
CREATE ROLE app_ro  LOGIN PASSWORD :ro_pw   CONNECTION LIMIT 10;

REVOKE ALL ON DATABASE campus FROM PUBLIC;
GRANT CONNECT ON DATABASE campus TO admin, app_rw, app_ro;

-- PostgreSQL 15+ no longer lets PUBLIC create objects in "public".
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO admin;
GRANT USAGE ON SCHEMA public TO app_rw, app_ro;

-- The app creates its tables on startup, so app_rw also needs CREATE once;
-- in a hardened setup the tables are created by admin (migrations) instead.
GRANT CREATE ON SCHEMA public TO app_rw;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_rw;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_ro;

-- Tables created later by app_rw are readable by app_ro as well.
ALTER DEFAULT PRIVILEGES FOR ROLE app_rw IN SCHEMA public GRANT SELECT ON TABLES TO app_ro;
