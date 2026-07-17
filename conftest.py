"""Root pytest config — DB test-safety guard (F11) + admin/app pool fixtures shared across the
whole workspace test suite.

Copies the document-intake pattern (R-DI §9 conftest.py:23-48,82-92): a hard guard against
truncating a live dev/teammate database, and a TRUNCATE-before-yield reset — adapted here for
this kit's schema-per-quadrant layout (kb, wb, obs, eval, core) instead of a single-schema table
list (dynamic `pg_tables` loop, not a hardcoded table list, since kb/wb/eval are still
stub-empty `ddl()` until P5/P7/P8).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from urllib.parse import urlsplit

import pytest
import pytest_asyncio
from psycopg import sql
from psycopg_pool import AsyncConnectionPool
from studio_app.core._db import Pool

TEST_DB_PORT = 5433
TEST_DB_NAME = "studio_test"

_SCHEMAS = ("kb", "wb", "obs", "eval", "core")


async def _truncate_all(admin: Pool) -> None:
    """TRUNCATE every table across the 5 kit schemas, dynamically (not a hardcoded table list —
    kb/wb/eval are still stub-empty `ddl()` until P5/P7/P8, so which tables exist changes as
    phases land). A bind parameter referenced only inside a `DO $$ ... $$` body is unreliable in
    Postgres (raises `could not determine data type of parameter $1`), so this queries
    `pg_tables` as a plain parameterized SELECT in Python, then issues one quoted TRUNCATE per
    row — no DO block needed."""
    async with admin.connection() as conn:
        cur = await conn.execute(
            "SELECT schemaname, tablename FROM pg_tables WHERE schemaname = ANY(%s::text[])",
            (list(_SCHEMAS),),
        )
        rows = await cur.fetchall()
        for schemaname, tablename in rows:
            await conn.execute(
                sql.SQL("TRUNCATE TABLE {}.{} CASCADE").format(sql.Identifier(schemaname), sql.Identifier(tablename))
            )


def _require_dsn(env_var: str) -> str:
    value = os.environ.get(env_var)
    if not value:
        pytest.skip(f"{env_var} not set — DB tests need `docker compose -f docker-compose.test.yml up -d`")
    return value


def pytest_configure(config: pytest.Config) -> None:
    """F11 — fail LOUD (never just skip) when the admin DSN points somewhere that is neither
    port 5433 NOR database `studio_test`. Backstory (R-DI §9): a wrong DSN here TRUNCATEs a real
    dev/teammate database, not a disposable one — port-only was not enough, hence + DB-name.
    """
    del config
    admin_url = os.environ.get("STUDIO_DATABASE_URL_ADMIN")
    if not admin_url:
        return  # no DB configured at all — individual fixtures will skip, not fail loud
    parsed = urlsplit(admin_url)
    port_ok = parsed.port == TEST_DB_PORT
    dbname_ok = parsed.path.lstrip("/") == TEST_DB_NAME
    if not (port_ok or dbname_ok):
        raise pytest.UsageError(
            f"STUDIO_DATABASE_URL_ADMIN={admin_url!r} is neither port {TEST_DB_PORT} nor "
            f"database {TEST_DB_NAME!r}. Refusing to run DB tests — this guard exists because a "
            "wrong DSN here TRUNCATEs a real dev/teammate database, not a disposable test one. "
            "Point STUDIO_DATABASE_URL_ADMIN/STUDIO_DATABASE_URL at docker-compose.test.yml's "
            "postgres-test service (port 5433, db studio_test) before running these tests."
        )


@pytest_asyncio.fixture
async def admin_pool() -> AsyncIterator[Pool]:
    """studio_owner pool — bootstraps schema+grants, TRUNCATEs all 5 schemas, then yields (mirrors
    R-DI conftest.py:82-92, adapted to multi-schema)."""
    from studio_app.core.schema import ensure_all_schemas, grant_app_privileges

    dsn = _require_dsn("STUDIO_DATABASE_URL_ADMIN")
    admin: Pool = AsyncConnectionPool(dsn, min_size=1, max_size=4, open=False)
    await admin.open(wait=True, timeout=10)
    await ensure_all_schemas(admin)
    await grant_app_privileges(admin)
    await _truncate_all(admin)
    yield admin
    await admin.close()


@pytest_asyncio.fixture
async def pool(admin_pool: Pool) -> AsyncIterator[Pool]:
    """studio_app pool — depends on `admin_pool` so schema+grants exist before runtime DML/RLS
    tests connect as the non-owner role."""
    del admin_pool  # ordering dependency only — schema/grants must exist first
    dsn = _require_dsn("STUDIO_DATABASE_URL")
    app_pool: Pool = AsyncConnectionPool(dsn, min_size=1, max_size=8, open=False)
    await app_pool.open(wait=True, timeout=10)
    yield app_pool
    await app_pool.close()
