-- Three-role Postgres fence (F1/F2, Decision #3): studio_owner OWNS every schema/table this kit
-- creates (via get_admin_pool/ensure_all_schemas), so `FORCE ROW LEVEL SECURITY` (added at the
-- table-owning quadrant phase) bites the owner too instead of silently letting it bypass RLS.
-- studio_app is a NON-owner, DML-only role — grant_app_privileges() (apps/studio/src/studio_app/
-- core/schema.py) is the ONLY place that gives it privileges, centrally, right after
-- ensure_all_schemas() runs (F6 — never scattered per-owner grants).
--
-- Runs as the `postgres` superuser at container initdb time (docker-entrypoint-initdb.d, in
-- filename lexical order — this file first, 01-extensions.sql second).
--
-- studio_scorer is the THIRD role (evalhub#37, GAP-1 fallout). It exists for exactly one job:
-- evalhub's cross-tenant scoring readers (`read_run_unscoped` / `list_runs_all_tenants`), which
-- deliberately do NOT set `app.tenant_id` because they must SEE events from every tenant. Once
-- `app#40` put `ENABLE`+`FORCE ROW LEVEL SECURITY` on `obs.trace_events`, those two readers
-- matched 0 rows and returned `[]` SILENTLY — indistinguishable from "no runs yet".
--
-- Why a separate role rather than granting BYPASSRLS to studio_owner: `FORCE ROW LEVEL SECURITY`
-- binding the owner is a deliberate, tested property (`packages/kb/tests/test_rls_framework.py::
-- test_force_rls_and_with_check`). Handing studio_owner BYPASSRLS would undo it for every table
-- at once — the opposite of what F1/F2 buys. studio_scorer keeps the blast radius to one role
-- that only ever holds SELECT on `obs.trace_events`.
--
-- Why not "loop per tenant with SET LOCAL" instead of a bypass role at all: `read_run_unscoped`
-- exists so `tenant_scope_ok` (studio_evalhub/harness.py) can catch a run whose first node carries
-- tenant A and whose later node carries tenant B. Scoping the read to one tenant makes RLS hide
-- precisely the foreign events that check is hunting for — the check would pass on a genuinely
-- broken run. That is a security regression, not a fix. See DEC-D26-01.
--
-- All three roles are NOSUPERUSER: none can bypass RLS via superuser privilege. studio_owner CAN
-- still bypass RLS via table ownership by default — that gap is closed by `FORCE ROW LEVEL
-- SECURITY` on each table (added when the owning quadrant creates it), not by anything here.
-- studio_scorer bypasses RLS by explicit BYPASSRLS attribute, which is the whole point of it;
-- it is fenced by privilege instead (SELECT on one table, granted by grant_scorer_privileges()
-- in apps/studio/src/studio_app/core/schema.py — never CREATE, never DML, never other schemas).

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'studio_owner') THEN
        CREATE ROLE studio_owner NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN PASSWORD 'changeme';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'studio_app') THEN
        CREATE ROLE studio_app NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN PASSWORD 'changeme';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'studio_scorer') THEN
        CREATE ROLE studio_scorer NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS LOGIN PASSWORD 'changeme';
    END IF;
    -- Idempotent for a role that already exists from an OLDER copy of this file (see the
    -- "existing volumes" note at the bottom): CREATE above is skipped, so set the attribute here.
    ALTER ROLE studio_scorer BYPASSRLS;
END
$$;

-- CONNECT is needed on whichever database this init-script runs against (the default `studio`
-- compose profile, or `studio_test` under docker-compose.test.yml) — resolved dynamically via
-- current_database() so this one script works unmodified for both.
DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO studio_owner, studio_app, studio_scorer', current_database());
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

-- ⚠️ EXISTING VOLUMES DO NOT RE-RUN THIS FILE. `docker-entrypoint-initdb.d` only executes on an
-- EMPTY data directory, so a teammate whose `studio_pgdata`/`studio_pgdata_test` volume predates
-- studio_scorer will not have the role, and evalhub's scoring CLI will keep failing closed
-- (`UnscopedReadUnavailable`). There is no in-app migration path for this: `ensure_all_schemas()`
-- runs as studio_owner, which is NOCREATEROLE and cannot create it. Apply by hand once —
-- this whole file is idempotent, so re-running it is safe:
--
--     docker exec -i <pg-container> psql -U postgres -d studio_test \
--         < docker/postgres-init/00-roles.sql
--
-- CI is unaffected: `.github/workflows/ci.yml` starts a fresh container per run with this
-- directory mounted, so initdb executes normally there.
