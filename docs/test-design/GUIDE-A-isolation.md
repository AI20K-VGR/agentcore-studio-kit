# GUIDE A — Isolation (Grid A)

**Owner: DE.** Read `00-METHODOLOGY.md` and `01-FOUNDATION.md` first. You do not need the other guides.

This grid covers the one AC the brief calls hard and non-negotiable: **`leakage = 0`**. It is also the
only grid where two blocking zones overlap, so it has the strictest evidence rules in the set.

---

## 1. What this grid is measuring

| Axis | Values | Where the value comes from |
|---|---|---|
| `tenant_scope` | `same` · `cross` · `unset` · `client-declared` | which tenant the caller is scoped to, relative to the data |
| `section_role` | `authorized` · `unauthorized` | whether the caller's resolved role covers the chunk's `section_role` |
| `entry_path` | `app-pool` · `admin-pool` | `pool` fixture (`studio_app`, non-owner) vs `admin_pool` (`studio_owner`, owner + `FORCE RLS`) |
| `kb_state` | `stub-5doc` · `real-ingest` · `post-reindex` · `post-purge` | what has happened to the KB before the query |

4 × 2 × 2 × 4 = **64 cells**. After the exclusion rules:

| | count | |
|---|---|---|
| `na:` — impossible, will never be testable | **18** | 3 rules, §2 |
| `todo:` — possible, seam not built yet | **22** | 2 seams, §3 |
| **real** — the policy is testable today | **24** | but see the warning below |
| **rows to write now** (`t=3`, blocking) | **16** | §5 |

**Do not read "16 rows" as "the fence is 75% untested".** Read it as: 16 rows are testable at the policy
today, 22 more unlock when a seam lands, and 18 will never exist.

> ### ⚠️ These 16 rows test the POLICY. They do not test the service, because the service does not exist.
>
> `KbSearchService.search` raises `NotImplementedError` (`search.py:49`). An earlier draft of this guide called
> all 16 rows "buildable against code that exists today" and named only one seam. That was wrong, and the way
> it was wrong is worth understanding, because it would have produced a green zone certifying nothing.
>
> Every mutant this guide requires — `M-R#1`, `M-R#4` — is a **pure RLS-policy mutant**, killable with raw SQL
> against `kb.chunks` through the `pool` fixture. So all 16 rows can honestly reach HIGH, the gate exits 0,
> and blocking zone Z1 reports covered — while `search()` is later implemented over `get_admin_pool()`. That
> is mutant `M-R#5`, measured at **0 tests red** before this work and still 0 after Z1 says HIGH. `leakage = 0`
> would be signed off by a zone that never touched the request path.
>
> **So Z1 carries a second obligation, `todo:kb-search`, which does not clear when the 16 rows are done.**
> Each of the 16 must be re-run through `KbSearchService.search` once it exists, and the guide's mutant map
> gains `M-R#5` (paired with `M-R#3`, per §7.1) at that point. Until then, every one of these cells is at most
> **MEDIUM**, not HIGH, no matter how good the SQL-level test is — the ceiling is stated in §6, and it is not
> a comment on your work.

> **There is no `provider` axis here, deliberately.** The fence is SQL and RLS; the embedding provider never
> touches the policy expression, so varying it would multiply cells without discriminating anything. One
> genuine gateway-specific leak class does exist — a shared embedding cache across tenants — and it gets a
> single dedicated pilot cell (`A-P1`, §11) rather than a whole column.

---

## 2. `na:` rules — frozen before any cell was filled

The ordering matters. If these rules were written *after* seeing which cells were empty, they would be
turning "nobody did it" into "nobody needs to do it". They were frozen first, and each one is grounded in
code, not in "this is awkward to test".

| Rule id | Combination | Why it can never happen |
|---|---|---|
| `na:client-declared-implies-app-pool` | `tenant_scope=client-declared` × `entry_path=admin-pool` | "Client-declared" only has meaning on a request path. `admin_pool` is the boot/DDL path (`_db.py:46`) — no client, nothing to declare. 8 cells |
| `na:unset-never-reaches-service` | `tenant_scope=unset` × `entry_path=admin-pool` | The unset case is specifically "a request arrived and no `app.tenant_id` got set". The admin path never sets it and never intends to; testing it there measures the pool, not the fence. 8 cells |
| `na:same-tenant-hides-role-axis-post-purge` | `tenant_scope=same` × `section_role=unauthorized` × `kb_state=post-purge` | After a consent purge there is no chunk left whose `section_role` can be unauthorized *within your own tenant*. The role axis has nothing to discriminate. 2 cells |

**A cell marked `na:` without one of these three ids counts as `unknown`, which blocks.** Prose saying "not
applicable here" does not count — that sentence is equally true of a genuinely impossible cell and a
forgotten one.

---

## 3. `todo:` seams — both of them yours

| Seam id | Cells | What has to exist | Owner | ETA |
|---|---|---|---|---|
| `todo:kb-pipeline` | 22 | `KbPipeline.re_index` and `KbPipeline.consent_purge` — both `NotImplementedError` (`pipeline.py:51`, `:46`) | **DE (you)** | **Day 20** |
| `todo:kb-search` | **all 16 live rows, as a second pass** | `KbSearchService.search` — `NotImplementedError` (`search.py:49`). This seam does not block writing the rows; it caps them at MEDIUM until the service path is exercised | **DE (you)** | **Day 20** |

All 22 blocked cells are blocked by **your own** unbuilt pipeline. That is a schedule, not an excuse — and
it is the reason the ETA is stated. A `todo:` in a blocking zone that has not landed by Day 20 escalates to
a sign-or-descope decision; it does not sit quietly until Day 30.

One thing you must not do: substitute `FakeEmbedding` or a hand-rolled purge and call the cell covered.
`FakeEmbedding`'s own docstring says it is a CI fixture and explicitly **not** a deliverable.

At Day 30, a `todo:` cell is judged like this: seam landed and cell filled ⇒ covered. Seam landed and cell
still `todo:` ⇒ **blocks**. Seam formally descoped through the INV-7 ladder with a recorded decision ⇒ becomes
`defer:<decision-id>`, which does **not** block and does **not** count as covered — a descoped cell is a cell
nobody looked at, and it must never be added to a coverage total. Seam neither landed nor descoped ⇒ blocks, and what is blocked is the *feature*.

---

## 4. Things you must know before writing a single test

These are measured facts about the current tree. Each one changes what a correct test looks like.

### 4.1 The fence is not wired into the path it protects

`get_request_connection()` is **defined** at `middleware.py:31` and called **nowhere** — zero call sites
across `packages`, `apps`, and `tests`. Meanwhile `interpreter.py:219` overwrites `node.params["tenant_id"]`
with `recipe.tenant_id`, and `:271` passes `recipe.tenant_id` down to `kb.search`.

So the tenant that governs retrieval is **whatever the recipe declares**, and nothing compares it against
the server-resolved tenant. The connection carrying `SET LOCAL app.tenant_id` — the only thing RLS governs —
is never obtained on the retrieval path.

Nothing leaks today, because `KbSearchService.search` still raises `NotImplementedError`. It becomes a real
leak the day you implement `search`, unless something validates `recipe.tenant_id`. **That is why cells
`A11`, `A12`, `A15`, `A16` (`tenant_scope=client-declared`) exist, and why they are the highest-value rows in
this guide.** A recipe declaring another tenant's UUID is exactly the `client-declared` case.

### 4.2 `SET LOCAL` is inside a transaction by accident

`middleware.py:80` runs `SET LOCAL app.tenant_id = ...`. It takes effect only because the `SELECT` at
`:62` already emitted a `BEGIN`. The docstring at `:51-56` plans to replace that query with JWT parsing.
When that happens, `SET LOCAL` will emit a warning and be discarded — and **no current test fails**.

The `unset` rows (`A09`, `A10`, `A13`, `A14`) are the ones that should catch this. Write them so they would.

### 4.3 Two existing tests specify contradictory behaviour

`test_leak.py:69` and `test_pg_kb.py:171` assert opposite things about the same situation. If you follow the
un-ratchet checklist in `postgres.py:9-13`, `test_t6_label_spoof` goes permanently red and cannot be fixed
from inside `packages/kb`.

**Do not resolve this by weakening either test.** Raise it — it is a contract question about who resolves
`section_roles`, and it is on the open list (§8 Q2).

### 4.4 `test_t6_label_spoof` currently passes on an empty result

`test_leak.py:56-69` has only an exclusion assertion, so `search()` returning `[]` passes it. Case T1 above
it documents this exact trap and does not apply it. Every cell in this guide that involves exclusion
therefore requires an inclusion assertion too — see §6.

### 4.5 RLS protects 1 of 11 tables

Only `kb.chunks` has `ENABLE ROW LEVEL SECURITY` (`packages/kb/src/studio_kb/schema.py:52`).
`obs.trace_events` stores chunk text with no policy at all. So a fence that holds at `kb.search` can still
leak the same content through trace. The `cross` rows (`A05`–`A08`) must assert on
**both** surfaces, not just the return value.

---

## 5. The 16 rows

Zone column: **Z1** = cross-tenant/cross-role leakage · **Z2** = fail-open when tenant is unresolved.
Both are blocking. Target band is the band a complete cell reaches, not a promise.

| id | tenant_scope | section_role | entry_path | kb_state | Zone | Target | §6 |
|---|---|---|---|---|---|---|---|
| A01 | same | authorized | app-pool | stub-5doc | — | MEDIUM | 6.1 |
| A02 | same | authorized | admin-pool | real-ingest | — | MEDIUM | 6.1 |
| A03 | same | unauthorized | app-pool | real-ingest | Z1 | HIGH | 6.1 |
| A04 | same | unauthorized | admin-pool | stub-5doc | Z1 | HIGH | 6.1 |
| A05 | cross | authorized | app-pool | real-ingest | **Z1** | HIGH | 6.2 |
| A06 | cross | authorized | admin-pool | stub-5doc | **Z1** | HIGH | 6.2 |
| A07 | cross | unauthorized | app-pool | stub-5doc | **Z1** | HIGH | 6.2 |
| A08 | cross | unauthorized | admin-pool | real-ingest | **Z1** | HIGH | 6.2 |
| A09 | unset | authorized | app-pool | stub-5doc | **Z2** | HIGH | 6.3 |
| A10 | unset | unauthorized | app-pool | real-ingest | **Z2** | HIGH | 6.3 |
| A13 | unset | authorized | app-pool | real-ingest | **Z2** | HIGH | 6.3 |
| A14 | unset | unauthorized | app-pool | stub-5doc | **Z2** | HIGH | 6.3 |
| A11 | client-declared | authorized | app-pool | stub-5doc | **Z1** | HIGH | 6.4 |
| A12 | client-declared | unauthorized | app-pool | real-ingest | **Z1** | HIGH | 6.4 |
| A15 | client-declared | authorized | app-pool | real-ingest | **Z1** | HIGH | 6.4 |
| A16 | client-declared | unauthorized | app-pool | stub-5doc | **Z1** | HIGH | 6.4 |

Ids are not renumbered when rows are regrouped — `A13`/`A14` sit with the `unset` group and `A11`/`A12` with
`client-declared` because the generator emitted them in coverage order, not in reading order. The id is the
stable handle; the ordering in this table is for humans.

**14 of 16 rows are in a blocking zone.** That is not zone inflation:
`tenant_scope ∈ {cross, unset, client-declared}` *is* the definition of both zones, and it covers 3 of the 4
axis values. The two non-blocking rows exist to make mutant `M-E` killable — see §6.1.

---

## 6. What each row must prove

Grouped by `tenant_scope`, because the proof obligation is the same within a group and the differences are
mechanical.

### 6.1 `same` — A01, A02, A03, A04

**Must prove:** an authorized caller in their own tenant **does get their data back**, and role scoping still
applies inside their own tenant.

```
REQUIRED
  [1] INCLUSION — the caller's own matching chunk comes back
  [2] for section_role=unauthorized (A03, A04): the chunk whose section_role
      the caller does not hold is ABSENT, while [1] still holds for a chunk
      they do hold
  [3] the pool named in the row (app-pool vs admin-pool)

DERIVED BAND
  [1]+[3]                    ⇒ MEDIUM
  [1]+[2]+[3] + mutant M-E   ⇒ HIGH
  missing [1]                ⇒ unknown
```

These rows look like the easy ones and they carry the whole grid: without them, **every** exclusion
assertion elsewhere is satisfiable by returning nothing. `A01` and `A02` are the rows that make mutant `M-E` killable — which is why they are in the set at all despite not being in a blocking zone.

### 6.2 `cross` — A05, A06, A07, A08 (Z1, blocking)

**Must prove:** no chunk belonging to another tenant leaves `kb.search`, and the caller's own data still
comes back.

```
REQUIRED
  [1] INCLUSION — tenant A's own matching chunk is present
  [2] EXCLUSION — no chunk of tenant B, by chunk_id AND by tenant_id field
  [3] the pool named in the row
  [4] for every cross row — also assert the same exclusion on obs.trace_events
      (§4.5: trace has no RLS, so a fenced search can still leak via trace)
  [5] mutation evidence: M-R#1 and M-R#4 both killed

DERIVED BAND
  all of [1..5]  ⇒ HIGH
  missing [5]    ⇒ MEDIUM
  missing [1]    ⇒ unknown   (NOT low — this is the T6 defect)
  missing [4]    ⇒ MEDIUM, and record why
```

`A06` and `A08` use `admin-pool`. They are not redundant with the `app-pool` rows: they are the only rows
that exercise `FORCE ROW LEVEL SECURITY`. Seed through `admin_pool` **with `app.tenant_id` set**, or you are
testing the absence of the setting rather than the policy.

### 6.3 `unset` — A09, A10, A13, A14 (Z2, blocking)

**Must prove:** when `app.tenant_id` is not set, the result is **zero rows** — never "everything".

```
REQUIRED
  [1] EXCLUSION — zero rows, for a query that provably matches seeded data
  [2] the "provably matches" half: the SAME query, run WITH the tenant set,
      returns a non-empty result. Without this you cannot distinguish
      "the fence worked" from "the query matched nothing"
  [3] a separate case for app.tenant_id = '' (empty string), which the
      NULLIF layer handles and which is NOT the same as unset —
      see 01-FOUNDATION.md §7
  [4] mutation evidence: M-R#4 killed (the fail-open mutant)

DERIVED BAND
  all of [1..4]  ⇒ HIGH
  missing [3]    ⇒ MEDIUM
  missing [2]    ⇒ unknown
```

Requirement [2] is the whole cell. "Zero rows" is trivially true of a broken query, a wrong table name, an
empty database, and a working fence. Only the paired run separates them.

#### These four cells cannot be built through `search()`. Build them at the connection.

An execution dry-run of this guide found that the obvious construction is impossible, so here is the correct
one before you waste an afternoon on it.

`PgKbSearch.search` **always** binds the session variable and **always** carries `WHERE tenant_id = %s`
(`postgres.py:70`, and `_bind_tenant` at `:88-101` issues `set_config('app.tenant_id', …)`). There is no
argument, and no combination of arguments, that expresses "no tenant is set" — the API is built so that state
cannot be reached through it. That is good design and it makes this cell unreachable from where you would
naturally start.

The working precedent is `packages/kb/tests/test_rls_framework.py::test_no_tenant_zero_rows`: take a
connection from the `pool` fixture, do **not** set `app.tenant_id`, and query `kb.chunks` directly.

```
A09/A10/A13/A14 CONSTRUCTION
  seed   through admin_pool, with SET LOCAL app.tenant_id set per insert
  call 1 pool connection, NO SET LOCAL, SELECT from kb.chunks   -> expect 0 rows
  call 2 same connection, SET LOCAL app.tenant_id = TENANT_A,
         same SELECT                                            -> expect >= 1 row
  call 3 same connection, SET LOCAL app.tenant_id = '',
         same SELECT                                            -> expect 0 rows
```

Two consequences worth stating plainly:

- These cells test the **policy**, not `KbSearchService`. That is the right subject — the policy is what
  fails open if `NULLIF` is dropped — but say so in the docstring, or a reviewer will reasonably ask why the
  service under test never appears.
- `test_rls_framework.py` already covers a piece of this and is **green, not red-by-design**. Do not duplicate
  it; extend it. In particular it has no `app.tenant_id = ''` case, and that is the gap the `NULLIF` layer
  exists to close.

### 6.4 `client-declared` — A11, A12, A15, A16 (Z1, blocking, highest value)

**Must prove:** what the caller declares about their own scope is **ignored**. This is T6 label-spoof, and
per §4.1 it is also the shape of the `recipe.tenant_id` hole.

```
REQUIRED
  [1] INCLUSION — a chunk the caller genuinely IS entitled to comes back
  [2] EXCLUSION — the chunk they declared entitlement to, but are not
      entitled to, is absent
  [3] the declared value must be one that WOULD change the result if it were
      honoured. Declaring a role you already hold proves nothing
  [4] two declaration surfaces, not one:
        (a) section_roles passed in the call
        (b) tenant_id carried on the recipe (§4.1)
      Surface (b) is the one no existing test touches
  [5] mutation evidence: M-E killed at this call site

DERIVED BAND
  all of [1..5]      ⇒ HIGH
  missing [4b]       ⇒ MEDIUM, and say so explicitly — (b) is the live hole
  missing [1] or [3] ⇒ unknown
```

Requirement [3] is where `test_t6_label_spoof` fails today. It declares `section_roles=["confidential"]`
against a tenant that owns a confidential chunk, then asserts absence — with no inclusion assertion and no
demonstration that honouring the declaration would have changed anything.

---

## 7. Mutation evidence

For a blocking-zone cell to reach **HIGH**, you must show a mutant died. Procedure: plant it, run the
named test, record **which assertion line went red**, remove it. Red on an unexpected line is itself a
finding — write it down.

| Mutant | Change | Measured today | Required by |
|---|---|---|---|
| `M-R#1` | drop the `USING` clause from `kb_chunks_tenant_isolation` | 5 tests red | §6.2 |
| `M-R#2` | `WITH CHECK` → `WITH CHECK (true)` | 1 test red | §7.1 |
| `M-R#3` | drop `FORCE ROW LEVEL SECURITY` | 1 test red (the same one) | §7.1 |
| `M-R#4` | drop `NULLIF(...)`, or `COALESCE(..., tenant_id)` — **fail-open** | 4 tests red | §6.2, §6.3 |
| `M-R#5` | request path switches to `get_admin_pool()` | **0 tests red** | §7.1 |
| `M-R#6` | `SET LOCAL` → `SET` in `middleware.py` | **0 tests red** at the middleware | §7.2 |
| `M-E` | `search()` returns `[]` unconditionally | 7 / 4 / 1 at three sites | §6.1, §6.4 |

`M-R#5` and `M-R#6` being unguarded is the measured state, not an accusation. Two of six fence mutants have
nothing watching them.

### 7.1 Two mutants that need care, or you will misread the result

**Do not write `M-R#2` as "delete `WITH CHECK`".** Postgres falls back to the `USING` expression for writes
when `WITH CHECK` is absent, so deleting it likely changes nothing observable — an **equivalent mutant**. It
will look unkillable while your tests are perfectly fine. Write `WITH CHECK (true)` to actually open the
write path.

**`M-R#5` alone is neutralised by `FORCE RLS`** and is unkillable for a boring reason. It only means anything
as a **second-order** mutant: apply `M-R#3` and `M-R#5` together. A cell claiming to kill `M-R#5` on its own
is claiming something impossible.

### 7.2 `M-R#6` needs the pool to hand the connection back

`_db.py:46,59` construct both pools with no `reset=` argument, so `RESET ALL` never runs. That is what makes
`SET LOCAL` → `SET` leak for real — and it leaks into **one specific tenant**, which is worse than leaking to
none. Killing this mutant requires two sequential requests over the same connection, which is flow `S1`.

---

## 8. Ordering flows you own

### S1 — tenant leak via a recycled pooled connection (blocking)

**Must prove:** request A (tenant X) returning its connection to the pool cannot let request B (tenant Y)
see X's setting or X's data.

Build it with two **sequential** requests, `min_size=1` so the pool has one connection to hand back, and an
`httpx` ASGITransport client. No product code changes. Add a third case where an exception is raised inside
`call_next`, since that is the path where the reset is least certain.

The repo has **no barrier precedent** — `asyncio.Event`: 0 occurrences, advisory locks: 0. You are building
the first one. Two sequential requests are enough here; you do not need concurrency to prove this.

> ⚠️ One unresolved risk before you start: `middleware.py` holds connection #1 for the whole request while
> `search` borrows #2 from the same pool (`max_size=8`). At 8 concurrent requests that deadlocks, and it may
> block a concurrent construction of `S1`. The sequential construction above avoids it. If you find the
> deadlock is real, that is a finding worth its own report — not something to work around silently.

### S4b — consent-purge racing an in-flight search — `todo:kb-pipeline`

**Must prove:** a purge that lands after retrieval has taken a `chunk_id` does not leave a citation pointing
at deleted data.

**Not buildable today, and the reason is worth understanding** — an earlier draft of this guide said it was.
`KbPipeline.consent_purge` raises `NotImplementedError` (`pipeline.py:46`). So a test written now would be a
**doubled search racing a doubled purge**: both sides fake, no product code in the loop. That test
choreographs itself and then proves its own choreography. It would be green, it would look like an ordering
test, and it would measure nothing.

This is the same defect class as an exclusion-only assertion, just at the level of a whole scenario — and it
is easy to miss precisely because writing a barrier feels like hard work, so the result feels earned.

Design the barrier now (a `KbSearch` double held after it returns `chunk_id`s, purge, release) and build it
the day `consent_purge` lands. Note that `citations` is `JSONB` with no foreign key, so the database will
never complain on your behalf — the assertion is entirely yours.

### S4a — re-index racing an in-flight search — `todo:kb-pipeline`

`KbPipeline.re_index` also raises `NotImplementedError` (`pipeline.py:51`). Same rule: do not fake it.

Both S4a and S4b are blocked on **your** seam, with you as named owner and an ETA no later than Day 20 — if
the seam is not landed by then, this escalates to a sign-or-descope decision rather than sitting silently as
a `todo:`.

---

## 9. Things that never count as evidence for a cell in this guide

- `pytest.raises(NotImplementedError)` — proves the seam is absent, not that the fence works
- `xfail` or `skip` in any form. `test_leak.py`'s two cases are `xfail(strict=False)` today, which is why a
  CI job named `leak-test` reports green in 0.14 s. Do not extend that pattern
- an exclusion assertion with no matching inclusion assertion (§4.4)
- a test that seeds and asserts through the **same** pool — that does not exercise RLS
- `test_leak_meta.py` passing. It is a string grep: renaming `test_t1_idor` to `_t1_idor` collects zero
  cases while the meta test stays green

---

## 10. Open questions blocking parts of this guide

Do not guess these. They change what a correct test asserts.

| id | Question | Which rows it blocks |
|---|---|---|
| **Q2** | Who resolves `section_roles` — server-side from the session, or does the recipe's `kb_binding.scope` get to decide? `executors.py:96-106` states the rule and `:134` does the opposite, self-labelled as a stub. `test_leak.py:69` and `test_pg_kb.py:171` encode opposite answers | all of §6.4, and the `[2]` requirement in §6.1 |
| **Q6** | Is `ts` strictly monotonic, or may two events share one? | the `obs.trace_events` half of §6.2 `[4]` |
| **Q7** | Is `recipe.tenant_id` validated against the session-resolved tenant, and by whom? If nobody, §4.1 is an architecture decision, not a test gap | §6.4 `[4b]` |

---

## 11. Grid D — number provenance and order (also DE)

You own a second grid. It is small, and it got small on purpose.

### 11.1 Why blocking zone 4 was re-scoped before you ever saw it

The cross-cutting invariant in umbrella §3.2 is *"`cost` at UI test == trace == dashboard — one source, one
number. Divergence = fail."* Measured against the pinned tree, that invariant is **currently vacuous**, for
two independent reasons:

- **Only 1 of 3 surfaces exists.** `trace` is real (write `obs/trace_writer.py:43`, read
  `trace_reader.py:326`). The `UI test` surface has no Test button, no `fetch`, and **the kit has no HTTP
  route at all** (`app.py:42-47`). The `dashboard` surface has no code; `obs.costs` is a shell of `id` +
  `created_at` with no writer.
- **`cost` is the constant `0.0`.** `interpreter.py:63,278` set `cost = _NO_COST = 0.0`. Three surfaces
  comparing three zeroes agree even if all three formulas are wrong.

So the original 20-odd cells covering UI and dashboard are marked **`defer:cost-dashboard-unowned`** — a
mentor-signed descope, recorded in the decision register, that does **not** block. They are not `todo:`,
because a `todo:` needs a named owner and there is none: "who makes `cost` real, and who writes the HTTP
routes" are both open questions with no assignee.

That leaves a gate someone can actually pass or fail: **is the one surface that exists internally
consistent, and is its ordering trustworthy?**

### 11.2 The 3 rows

| id | trace_state | cost_surface | provider | Zone | Target |
|---|---|---|---|---|---|
| D01 | 0-gap | trace | fixtures-stub | **Z4** | HIGH |
| D02 | missing-event | trace | fixtures-stub | **Z4** | HIGH |
| D03 | ts-out-of-order | trace | fixtures-stub | **Z4** | HIGH |

`na:provider-carries-no-token-signal` (3 cells): `real-gateway` × `trace` is impossible because
`LLM.complete -> str` carries no token usage back, so a real gateway produces the same `0.0` as the stub. If
that signature ever widens to return usage, these 3 cells become real — reopen the rule rather than quietly
filling them.

### 11.3 D03 is the one that matters, and the obvious version of it is a tautology

**Do not write `assert ts == sorted(ts)` on interpreter output.** It is a tautology — but not for the reason
an earlier draft of this guide gave, and the difference is worth two sentences because it is checkable in one
command.

The draft said the guard at `interpreter.py:263-264` *forces* monotonicity. It does not: measured over 200
real runs, consecutive `ts` deltas are **10–156 µs**, far above the 1 µs the guard compares, so the branch
never executes. The ordering is monotonic because the clock already is, not because anything enforces it.
(The branch is not unreachable in principle — with no work at all between two timestamps, `datetime.now()`
returns the same value roughly 2 times in 3. It is unreachable on the interpreter's path, which is what
matters here.)

Either way the assertion measures nothing, and deleting the guard turns **no test** red.

Two measured facts to build on instead:

- The guard being defended is **untested**, not dead: real `ts` deltas measure 10–156 µs against a 1 µs
  comparison, so nothing exercises it, and deleting it turns **no test** red. Killing that mutant requires
  `monkeypatch.setattr(interpreter, "datetime", …)` — possible because of the `:33` import. **This test is
  mandatory**, or zone 4 keeps a permanent hole.
- The real ordering defect is on the **reader** side. `ts` is compared as a string on a `TEXT` column:
  measured, `+07:00` versus `+00:00` orders **incorrectly**, and `ORDER BY ts` inherits that. Separately,
  mixing naive and aware `ts` raises a bare `TypeError` rather than the typed `TraceTimestampError`, because
  `trace_reader.py:185` sits outside the `try`.

```
D03 REQUIRED
  [1] rows written DIRECTLY through PgTraceWriter with mixed timezone offsets
      — not produced by the interpreter, which would sanitise them
  [2] ordering asserted through trace_reader, not through interpreter output
  [3] the typed-error case: naive mixed with aware raises TraceTimestampError,
      not a bare TypeError
  [4] mutant kill: delete the interpreter.py:263-264 monotonic guard, via the
      datetime monkeypatch. Record which assertion line goes red

DERIVED BAND
  all of [1..4]  ⇒ HIGH
  missing [4]    ⇒ MEDIUM
  missing [2]    ⇒ unknown   (asserting on interpreter output is the tautology)
```

### 11.4 D01 and D02 — one INSERT, and nothing clever inside it

`PgTraceWriter.write()` is contractually a single plain `INSERT`; its docstring **forbids** cost aggregation
and dedup inside it. That prohibition is enforced by nothing today: `M-N#1` has three variants —
`ON CONFLICT (event_id) DO NOTHING`, a read-before-write, and aggregation into a side table — and **all three
survive** `test_trace_writer.py:71`.

```
D01 (0-gap) REQUIRED
  [1] every node of a run emits exactly one event, read back in order
  [2] a POSITIVE CONTROL for "0-gap": a run whose event count is known
      independently of the reader, so "no gaps" is not just "the reader
      returned what the reader wrote"
  [3] mutant kill: at least two of the three M-N#1 variants

D02 (missing-event) REQUIRED
  [1] a run with one event deliberately absent is DETECTED, not silently
      rendered as a shorter timeline
  [2] the run-broke-midway case is distinguishable from the event-lost case.
      Today it is not — see §11.5

DERIVED BAND (both)
  all required ⇒ HIGH · missing the mutant kill ⇒ MEDIUM · missing the
  positive control ⇒ unknown
```

### 11.5 One open question blocks part of D02

There is no recorded way to represent "this run broke halfway". So a run that crashed and a run that lost an
event look identical on read. Deciding that touches frozen contract #2 (`trace-event schema`), which means a
mini-RFC with four signatures — not something to settle inside a test. Register §12 carries it; leave the
second requirement of D02 marked until it is answered.

### 11.6 Pinned-by

| Row | Pin-test that must flip in the same commit | Why |
|---|---|---|
| D01, D02 | `test_trace_writer.py:71` | It currently passes with all three `M-N#1` variants in place, so it is pinning the absence of the check |
| D03 | none found | If you find one, report it — a pin-test the guide missed is a gap in the guide |

---

## 12. A-P1 — the one gateway pilot cell

`provider` is not an axis in Grid A (§1), because the fence is SQL and the embedding provider never touches
the policy expression. There is exactly one gateway-specific leak class that the RLS policy genuinely cannot
see, and it gets one cell rather than a column.

**A-P1 — shared embedding cache across tenants.** `todo:embedding-gateway`, owner AIE-1.

The leak does not go through `kb.chunks` at all. If a gateway-backed `EmbeddingService` caches vectors keyed
only by text, then tenant B querying the same phrase as tenant A gets a cache hit computed from A's corpus.
Nothing crosses the RLS boundary, every policy holds, and information still moves between tenants — through
timing, through vector reuse, or through whatever the cache returns alongside the vector.

```
A-P1 REQUIRED
  [1] two tenants, same query text, gateway provider
  [2] evidence that the second call did NOT reuse the first tenant's
      computed result — by cache-key inspection or by a call counter on the
      service, not by comparing output vectors (identical text legitimately
      yields identical vectors, so vector equality proves nothing either way)
  [3] the cache key includes tenant_id, asserted directly

DERIVED BAND
  all of [1..3] ⇒ HIGH · missing [2] ⇒ unknown (this is the whole cell)
```

Requirement [2] is where this cell will most likely be filled dishonestly: comparing the two returned vectors
looks like the obvious assertion and is worthless, because equal input text *should* produce equal vectors
whether or not a cache was involved. The observable that distinguishes them is whether the provider was
called, not what it returned.

Do not build this against `FakeEmbedding`. Its docstring says it is a CI fixture and explicitly not the AIE-1
deliverable, and it has no cache — so the cell would pass by the absence of the thing under test.
