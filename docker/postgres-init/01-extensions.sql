-- pgvector extension for `kb.chunks`' vector column (Decision #2, Postgres-everything). Must run
-- as the `postgres` superuser at initdb time — CREATE EXTENSION is deliberately NOT part of any
-- quadrant's `ddl()` (both app-facing roles, studio_owner and studio_app, are NOSUPERUSER and
-- cannot run it at boot).
CREATE EXTENSION IF NOT EXISTS vector;
