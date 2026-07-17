-- Two-role Postgres fence (F1/F2, Decision #3): studio_owner OWNS every schema/table this kit
-- creates (via get_admin_pool/ensure_all_schemas), so `FORCE ROW LEVEL SECURITY` (added at the
-- table-owning quadrant phase) bites the owner too instead of silently letting it bypass RLS.
-- studio_app is a NON-owner, DML-only role — grant_app_privileges() (apps/studio/src/studio_app/
-- core/schema.py) is the ONLY place that gives it privileges, centrally, right after
-- ensure_all_schemas() runs (F6 — never scattered per-owner grants).
--
-- Runs as the `postgres` superuser at container initdb time (docker-entrypoint-initdb.d, in
-- filename lexical order — this file first, 01-extensions.sql second).
--
-- Both roles are NOSUPERUSER: neither can bypass RLS via superuser privilege. studio_owner CAN
-- still bypass RLS via table ownership by default — that gap is closed by `FORCE ROW LEVEL
-- SECURITY` on each table (added when the owning quadrant creates it), not by anything here.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'studio_owner') THEN
        CREATE ROLE studio_owner NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN PASSWORD 'changeme';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'studio_app') THEN
        CREATE ROLE studio_app NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN PASSWORD 'changeme';
    END IF;
END
$$;

-- CONNECT is needed on whichever database this init-script runs against (the default `studio`
-- compose profile, or `studio_test` under docker-compose.test.yml) — resolved dynamically via
-- current_database() so this one script works unmodified for both.
DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO studio_owner, studio_app', current_database());
END
$$;

-- studio_owner additionally needs CREATE ON DATABASE — `ensure_all_schemas()` (core/schema.py)
-- runs `CREATE SCHEMA IF NOT EXISTS ...` as studio_owner, which Postgres refuses without this
-- (CONNECT alone only lets a role log in and read objects it already has access to; creating a
-- new schema in the database needs the database-level CREATE privilege). studio_app never gets
-- this — it stays DML-only, granted per-schema by grant_app_privileges() (F6), never CREATE.
DO $$
BEGIN
    EXECUTE format('GRANT CREATE ON DATABASE %I TO studio_owner', current_database());
END
$$;
