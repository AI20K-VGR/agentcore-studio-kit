# Foundation — read once, applies to all four guides

> Everything in here is measured on the pinned baseline, not inferred. Where documentation and code
> disagree, this file says so and the code wins.
>
> Read `00-METHODOLOGY.md` first if you have not. Then this. Then your own quadrant's guide.

---

## 1. Before anything else: how to not destroy someone's data

The test fixtures `TRUNCATE` tables. The guard that is supposed to stop you pointing them at the wrong
database has a hole, so read this before you export a DSN.

`conftest.py` runs `_truncate_all` on every test that requests `admin_pool` or `pool`. It dynamically
queries `pg_tables` and issues `TRUNCATE TABLE <schema>.<table> CASCADE` for every table in
`kb, wb, obs, eval, core`. No confirmation, no dry run.

The guard (`conftest.py:51-70`):

```python
port_ok   = parsed.port == 5433
dbname_ok = parsed.path.lstrip("/") == "studio_test"
if not (port_ok or dbname_ok):
    raise pytest.UsageError(...)
```

**That is `or`, not `and`, and neither branch checks the host.** Its own docstring says
*"port-only was not enough, hence + DB-name"* — which reads like tightening, while `or` actually creates
two independent ways through. Both of these DSNs pass the guard:

| DSN | Passes because | What happens |
|---|---|---|
| `postgresql://u:p@shared-host:5433/anything` | `port_ok` | truncates 5 schemas on someone else's database |
| `postgresql://u:p@shared-host:5432/studio_test` | `dbname_ok` | truncates `studio_test` on a shared host, not your container |

**Rule: only ever export a DSN that satisfies all three of** `localhost` **and** port `5433` **and** db
`studio_test`. Do not rely on the guard.

If two of you share one Postgres in the lab to save memory and map it to `5433`, one person's `pytest`
run wipes the other's ingested Callisto corpus and the guard stays silent.

---

## 2. How to actually run the DB tests

There is no working documented path. `make test-int` looks like the path and is not:

```make
test-int:
	docker compose -f docker-compose.test.yml up -d --wait
	uv run pytest
```

It starts the database and **exports no DSN**. `conftest.py:44-48` reads `os.environ` and skips when the
DSN is absent. The skip message even tells you to run `docker compose up -d` — which you just did.

`.env` does not help either: only `settings.py:12` reads `.env` (via `pydantic-settings`). The conftest
fixtures read `os.environ` directly. Two separate environment paths that are not connected.

**What works:**

```bash
docker compose -f docker-compose.test.yml up -d --wait

export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test
export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test

.venv/bin/python -m pytest -q                      # whole workspace
.venv/bin/python -m pytest -q packages/kb/tests    # one package
```

Check you actually enabled them. **Count the skips, do not grep the message:**

```bash
.venv/bin/python -m pytest -q 2>&1 | tail -1
# with no DSN:     51 skipped
# with the DSN:     8 skipped   <- the 8 unconditional e2e skips, and nothing else
```

The obvious check — grepping for the skip reason — under-counts. Measured breakdown of the 51:

| count | skip reason | population |
|---|---|---|
| 41 | `STUDIO_DATABASE_URL_ADMIN not set — DB tests need docker compose …` | DB-gated |
| 2 | `STUDIO_DATABASE_URL(_ADMIN) not set — needs docker-compose.test.yml up` | DB-gated, **different wording** |
| 8 | `e2e pending — owner fills after 4 quadrants land` | unconditional, never runs anywhere |

So `grep -c "STUDIO_DATABASE_URL_ADMIN not set"` returns **41**, not 43 — and 41 is close enough to 43 that
you would not notice two tests sitting out. A check that under-reports by a plausible margin is worse than no
check: it sells confidence. Count the total instead; it is unambiguous.

Run that check every time. It is the difference between "my fence test passes" and "my fence test did not
run".

---

## 3. Where your tests do and do not run

| Path | 43 DB-gated tests | 8 e2e tests | `test_leak.py` |
|---|---|---|---|
| `pytest` locally, no DSN | skip | skip | skip |
| `make test-int` | **skip** | skip | skip |
| local, DSN exported as above | run | skip | runs, but `xfail` |
| GitLab CI | **skip** — `.gitlab-ci.yml:31-36` starts no Postgres | skip | skip |
| GitHub CI, branch push without a PR | **does not trigger** — `ci.yml:9-13` is `main` + PR only | — | — |
| GitHub CI, `main` or PR | run (`ci.yml:55-56`, `:71-83`) | skip | runs, but `xfail`, and its job is `continue-on-error` |

Read the second and fourth rows together: **you can push a branch, see two green marks, and never have
run the fence.** If your quadrant's evidence depends on a DB test, open a PR — a branch push is not
evidence.

---

## 4. Fixtures you have

| Fixture | What it gives you | Notes |
|---|---|---|
| `admin_pool` | pool as `studio_owner` (table owner). Runs `ensure_all_schemas` + `grant_app_privileges` + `_truncate_all`, then yields | **Seed data through this.** RLS still applies because tables are `FORCE ROW LEVEL SECURITY`, so set `app.tenant_id` before inserting |
| `pool` | pool as `studio_app` (non-owner). Depends on `admin_pool` for ordering | **Assert through this.** This is the only pool where RLS genuinely governs the request path |

The two-pool dance is the point, not overhead: seeding through `admin_pool` and asserting through `pool`
is what makes an isolation test mean anything. A test that seeds and asserts through the same pool proves
much less.

`asyncio_mode = "auto"` is set in `pyproject.toml:69`, so `async def test_*` needs no marker.

---

## 5. Gates you will trip

| Gate | Command | Trap |
|---|---|---|
| `ruff` | `uv run ruff check .` | `main` is currently red on **7** errors, mostly `W293 Blank line contains whitespace` in `packages/workbench/tests/test_wiring_d7.py`. Three are `--fix`-able. Fix yours; do not add to it |
| `mypy` strict | `uv run mypy packages apps` | `studio_engine` and `studio_app` have no `py.typed`, so cross-package imports of those need care |
| `import-linter` | `uv run lint-imports` | If `tests/test_workspace.py::test_import_linter_passes` fails with `FileNotFoundError`, the binary is installed but **not on your `PATH`** — `PATH=.venv/bin:$PATH .venv/bin/python -m pytest` gives `204 passed, 0 failed`. **An environment problem, not a regression.** Do not "fix" it by weakening the test |
| NDA denylist | pre-commit | Blocks any path containing `mentor`, `rubric`, `answer-key`, `solution`, `grading` — case-insensitive, substring. Name test files carefully |

The four layers of import boundary are real: a quadrant package may import `studio_contracts` and nothing
else. If your test needs another quadrant's concrete class, that is a signal the test belongs at the
composition layer, not in your package.

---

## 6. Things the existing tests do not guard, so do not assume they do

Measured, not guessed. This matters because "there is already a test for that" is the most common reason a
cell goes unfilled.

| You might assume | Actually |
|---|---|
| `test_leak.py` proves `leakage = 0` | Both its cases are `xfail(strict=False)`. Its dedicated CI job is `continue-on-error`. It runs in the `test` job too, but the marker neutralises that path as well |
| `test_t6_label_spoof` proves role-scoping | It has only an exclusion assertion, so `search()` returning `[]` passes it |
| `test_leak_meta.py` stops anyone faking green | It is a string grep. Rename `test_t1_idor` to `_t1_idor` and 0 cases collect while the meta test stays green |
| `test_node_type_closed.py` locks the dispatch table | `interpreter.py:161-168` builds the dispatch dict inline (looked up at `:237`). `registry.REGISTRY` is a second copy. Removing a key from the real one turns no test red — even though `registry.py:1-2` claims to be *"the ONLY place `NodeType` maps to a concrete executor"* |
| `test_queue.py` locks `SKIP LOCKED` | `:52` asserts `job_a.id != job_b.id`, which holds with or without `SKIP LOCKED`. `:71` asserts `requeued_count >= 1`, which holds even if the lease-expiry predicate is deleted |
| The monotonic `ts` guard is tested | Real `ts` deltas measured at 10–156 µs against a 1 µs comparison at `interpreter.py:263-264`, so the branch never runs and deleting the guard turns no test red. Killing that mutant requires `monkeypatch.setattr(interpreter, "datetime", …)` — possible because of the `:33` import |
| `obs.trace_events` is fenced like `kb.chunks` | RLS exists on **1 of 11** tables — and more tellingly, **1 of the 6 that hold tenant-scoped data** — only `kb.chunks` has `ENABLE ROW LEVEL SECURITY` (`packages/kb/src/studio_kb/schema.py:52`). `obs.trace_events` stores chunk content with no policy. `core.jobs` has no `WHERE` clause. `wb.*` stores tenant data as `tenant TEXT`, not `tenant_id UUID`, with full DML granted and no RLS |
| A pooled connection is reset between requests | `_db.py:46,59` construct both pools with `min_size`/`max_size`/`open` and **no `reset=`** argument, so `RESET ALL` never runs. That is what makes the `SET LOCAL` → `SET` mutant leak for real — and it leaks into **one specific tenant**, which is worse than leaking to none |
| There is one golden set | There are **two tables**: `eval.golden_sets` (AIE-2's schema) and `obs.golden_sets` (DE's schema). The brief says one doc-factory feeds both KB and golden set, and `citation_accuracy` is supposed to be read from trace as a single source. Two tables named the same thing in two owners' schemas is exactly where "one number, one source" quietly stops being true — check which one your test reads |
| The 3-surface cost invariant is meaningful | Only the `trace` surface exists. There is **no HTTP route in the kit at all** (`app.py:42-47`). `obs.costs` is a shell of `id` + `created_at` with no writer. And `interpreter.py:63,278` sets `cost = _NO_COST = 0.0` constant, so all surfaces agree trivially |
| 9 root tests contribute coverage | `test_docs_note.py` and `test_readme_onboarding.py` check documentation prose (e.g. `assert "out" in text.lower()`); half of `test_ops.py` greps config. Exclude them from coverage counts |

---

## 7. Two places the documentation is wrong

Not pedantry — both will make you write the wrong test.

**`system-architecture.md` §4.3 quotes an outdated RLS policy.** It shows
`USING (tenant_id = current_setting('app.tenant_id', true))`. The code
(`packages/kb/src/studio_kb/schema.py:57-58`) is:

```sql
USING      (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
```

The doc version omits `NULLIF`, which is the third fail-closed layer. Write tests from the doc and you skip
the `app.tenant_id = ''` case — empty string is **not** the same as unset, and the code treats them
differently on purpose.

**`system-architecture.md` §6 still lists `resolve_tenant` as an empty seam.** It is implemented
(`packages/workbench/src/studio_workbench/tenant_wall.py`) with 14 passing cases in
`test_wiring_d8.py`. A third of the SWE quadrant's work is invisible if you trust that table.

---

## 8. One structural warning about which tree you are testing

`git clone --recursive` gives you the submodule commits that **kit main records**, and two of those are
behind the submodules' own `main`:

| Submodule | kit main records | submodule `origin/main` |
|---|---|---|
| `packages/engine` | `a65c9d69` | `a6967a24` |
| `packages/workbench` | `afa805dc` | `134fc262` |

So AIE-1 and SWE can have a test passing in their own repo against code the kit does not contain. Before
claiming evidence for a cell, check which commit the kit is actually building:

```bash
git submodule status
```

---

## 9. Writing a test that counts as evidence

Four mechanical requirements. A test missing any of them does not fill its cell, regardless of whether it
passes.

1. **The cell id is in the docstring, written exactly as the guide writes it.** Two shapes exist and the
   reconciliation gate matches only these:

   | Shape | Examples | Used for |
   |---|---|---|
   | grid letter + **two** digits | `A05`, `C09`, `F07`, `D03` | generated grid rows |
   | grid letter + `-` + kind letter + digits | `A-P1`, `B-S01`, `C-R01`, `E-M7` | flows, pilots, ratchets, mutant cells |

   ```python
   """Cell: A05 — cross tenant, authorized role, app pool.

   Assertions: inclusion=L1 exclusion=L2 pool-path=pool trace-surface=L4
   Mutants: M-R#1->L2 M-R#4->L2 M-E->L1
   """
   ```

   `A5`, `A-05`, and `A1-03` all fail to match and score as no credit. The `Cell:` keyword and the
   colon are both required — a bare mention of an id anywhere else in the file is a cross-reference, not a
   claim, and is deliberately not counted. The block under the title is the
   machine-extractable evidence block — the band-derivation script reads it; see `02-MATRIX.md` §4.

   One more rule that exists because it bit the tooling: when you cite a **decision** id, hyphenate it
   (`D-19`, not `D19`). Unhyphenated it is indistinguishable from a Grid-D cell id and it poisons the parity
   check with a phantom cell.
2. **Both assertion directions where the guide asks for them.** Where a cell requires an INCLUSION and an
   EXCLUSION assertion, exclusion alone is a false green — see `00-METHODOLOGY.md` §1.
3. **Through the pool the guide names.** Asserting through `admin_pool` when the cell says `pool` tests a
   different thing.
4. **No `xfail`, no `skip`, no `pytest.raises(NotImplementedError)`** for a blocking-zone cell. If the seam
   does not exist yet, the cell is marked `todo:<seam-id>` in the guide — that is the honest state, and it
   is not something you patch over with a marker.

For blocking-zone cells you also record mutation evidence: plant the mutant from the guide's map, run,
capture **which assertion line went red**, remove the mutant. If it went red somewhere unexpected, write
that down — it usually means the test is coupled to something you did not intend.
