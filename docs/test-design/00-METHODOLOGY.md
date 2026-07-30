# Why this test set is designed the way it is

> **Read this first.** The other files in `docs/test-design/` are the list of work. This one is the
> reason. Skip it and you will still write the right number of tests, but they will not protect anything —
> and that failure mode is hard to spot, because it looks exactly like success.
>
> No prior knowledge needed. If you have never heard of `mutation testing` or `DST`, this is the right
> place to start.

## Where each question is answered

Read it end to end once. After that, use this:

| If you are asking | Go to |
|---|---|
| Why should I not trust a suite that is 98% green? | §1, and the CI log in it |
| What are the ways green means nothing? | §2 — four of them, each with a real example from this repo |
| I use AI to write tests. What does it get wrong? | §3 — the mechanism, and the four shapes it produces |
| What is *coverage*, and why is `line coverage` not it? | §4 |
| What is `na:` versus `todo:`, and why does the difference matter? | §4, last part |
| **How do I choose axes on a project nobody has done this for?** | **§4.1 — the method, and the four traps, with measurements** |
| What is *mutation testing* and why is it not a score? | §5 |
| What is *DST*, and why can mutation testing never find ordering bugs? | §6 |
| Who decides a cell's band? | §7 — nobody decides it; it is derived |
| Why does a passing test sometimes need to be changed? | §7.2 — pin-tests assert decisions, not behaviour |
| Why three layers instead of one good one? | §8 |
| What do I actually do on Monday? | §9 |
| What does that word mean? | §10 |

Sections 1–3 are the argument. Sections 4–6 are the three instruments. Sections 7–9 are the rules you work
under. If you only have twenty minutes, read §1, §2, and §9.

---

## 1. Start with this repo's own numbers

On 2026-07-30, running the kit's whole suite on a dev machine:

```
260 tests collected
203 passed, 51 skipped, 2 xfailed, 3 xpassed, 1 failed
```

Skim it and you see **98% green**. For a project on Day 9 that sounds fine.

Read it properly and it says something else.

**51 skipped**, all for the same reason: `STUDIO_DATABASE_URL_ADMIN not set`. They include
`test_rls_framework`, `test_spine_live`, `test_trace_reader`, `test_wb_schema`, `test_queue`,
`test_schema`, `test_trace_writer` — that is, the entire fence against cross-tenant leakage. The one
thing the brief calls a hard AC (`leakage = 0`) does not run.

And the blind spot is wider than "my laptop":

| Where | Do the 43 DB tests run? |
|---|---|
| dev machine, `pytest` | no — no DSN exported |
| dev machine, `make test-int` | **no** — the target starts the DB but exports no DSN (`Makefile:12-14`) |
| GitLab CI | **no** — `.gitlab-ci.yml:31-36` deliberately starts no Postgres |
| GitHub CI, push to a branch with no PR | **no** — `ci.yml:9-13` triggers only on `main` and PRs |
| GitHub CI, `main` or a PR | yes |

So you can push a branch, see two green check marks, and never once have exercised the fence. The other
8 skips are unconditional `pytest.skip` in `tests/e2e/test_lifecycle.py` and never run anywhere.

**3 xpassed.** `xpass` means a test marked "expected to fail" passed instead. With `strict=False` that
does not turn the suite red — so the signal "this marker is now stale" is thrown away. One of the three,
`test_wiring_d5::test_workbench_recipe_emits_trace_events_via_interpreter`, is the *only* case watching
trace ordering and `ts`. It is in a blocking zone, and its result is being discarded.

### The strongest evidence is not in those numbers — it is in a CI log

The kit has a CI job called `leak-test`. Its only job is to prove `leakage = 0`. Here is its log from the
most recent run on `main` (`run 30515170845`, 30/07 04:55 UTC):

```
env:
  STUDIO_DATABASE_URL: ***localhost:5433/studio_test
  STUDIO_DATABASE_URL_ADMIN: ***localhost:5433/studio_test

$ uv run pytest packages/kb/tests/test_leak.py -q
xx                                                         [100%]
2 xfailed in 0.14s
```

**Job conclusion: `success`.** Green on the Actions page.

Three lines side by side:

| What you see | What it actually means |
|---|---|
| job `leak-test` → `success` | anyone opening Actions concludes `leakage = 0` has been checked |
| `2 xfailed` | **no assertion was evaluated.** `xfail` means "expected to fail, do not count it" |
| `0.14s` | these two cases are supposed to seed two tenants into Postgres and call `search()`. 0.14 s is far too fast for that |

**One correction, because getting it right changes the fix.** My first draft of this section said the job
was insulated by three layers, then four. That was overcounting. What is actually true:

- `test_leak.py` runs on **two** CI paths — the `test` matrix job (`agentcore-studio-kb`) and the dedicated
  `leak-test` job. Only the second has `continue-on-error: true`.
- Both paths are neutralised by **one thing**: `@pytest.mark.xfail(strict=False)` at `test_leak.py:35`
  and `:55`.

So this is two enforcement paths defeated by a single marker. That is worse news about the marker and
better news about CI, and it means the cheapest real fix is removing one marker — not dismantling four
mechanisms.

### And the suite actively defends the hole

`tests/test_ops.py:145-155`:

```python
def test_leak_job_continue_on_error() -> None:
    """KHÓA (F5): CI job `leak-test` là continue-on-error — đỏ-by-design KHÔNG chặn merge."""
    ...
    assert leak_job.get("continue-on-error") is True
```

There is a green, passing test whose job is to **assert that the leak test must never block a merge**.
Make `leak-test` blocking and this test goes red.

Nobody did anything wrong here either. Every individual decision was reasonable: `xfail` so the suite is
not red while a seam is unfinished; `continue-on-error` so an in-progress fence does not block merges;
`test_ops` so nobody silently reverts that intent. Stack them and you get a permanently green job carrying
the exact name of the thing it does not check, plus a test that keeps it that way.

That is the mechanism this whole acceptance set exists to stop: **the name says one thing, the evidence
says another, and nothing compares the two.**

> **Rule, applied to every grid cell:** a cell in a blocking zone does not count as covered if its test
> is `xfail`, `skip`, or inside a `continue-on-error` job. Acceptance reads **per-assertion results**, not
> job colour.

### One more hole that shows up in no count at all

Open `test_leak.py`, case T6 (`:56-69`):

```python
results = await service.search(query="doc", tenant_id=TENANT_A,
                               section_roles=["confidential"], top_k=10)
result_chunk_ids = {item.chunk_id for item in results}
assert "chunk-confidential" not in result_chunk_ids
```

This **passes** if `search()` returns `[]`. An empty list contains no `chunk-confidential`. It also passes
if `search()` returns garbage, as long as that one chunk is not in the garbage.

Here is the part worth sitting with: **the same file, in case T1 directly above, documents this exact
trap**:

> *"Positive inclusion FIRST — the requesting tenant's own matching chunk MUST come back. Without this, a
> lazy/broken impl that returns an empty list would false-pass the exclusion assertion below."*

The author knew. Wrote it down. Then did not apply it to the next case one screen later.

This repo already has a name for that outcome — `test_pg_kb.py` calls it **"xanh giả"** (false green).
That is the term used from here on.

---

## 2. What green means

**Green does not mean the code is correct. Green means: of the assertions that ran, none was violated.**

Four ways a suite is green while protecting nothing:

| Way | What it looks like | Real example in this repo |
|---|---|---|
| **It did not run** | `skipped`, `xfail`, `continue-on-error` | 43 DB tests skipped on 4 of 5 paths; `leak-test` green in 0.14 s |
| **It ran, but the assertion is always true** | any code passes — false green | T6 passes with `search()` returning `[]` |
| **It ran correctly but never entered the risky case** | passing, high coverage | no test exists for "tenant unset" + "role unauthorized" + "via owner pool" |
| **It entered the case but the bug needs a specific ordering** | passes 9999 times in 10000 | tenant leak through a recycled pooled connection — §6 |

These four are not substitutes for one another, and each needs a different instrument. That is why this
set has three layers rather than one.

---

## 3. AI-written tests fail in their own specific way

You will use AI to write tests. Nobody is banning that. But you need to know the failure mode, because it
differs from a human's.

The mechanism is mundane: **an AI reads the code that exists and writes assertions that match the
behaviour that exists.** If that behaviour is a bug, the assertion pins the bug down as the spec. It does
not check the behaviour against the requirement, because it is reading code, not requirements.

Four concrete consequences, and you will hit all four:

1. **The assertion gets lowered to fit the code.** Code returns `None` on some branch, so the test says
   `assert result is None`. A bug just became a specification.
2. **Only safe things get asserted.** `assert isinstance(x, list)`, `assert len(x) >= 0`,
   `assert response.status_code in (200, 400)`. Not wrong. Not measuring anything either. This repo has 9
   such cases at the root (`test_docs_note.py`, `test_readme_onboarding.py`, half of `test_ops.py`) — for
   example `assert "out" in text.lower()`, which is true of almost any English text.
3. **`pytest.raises(NotImplementedError)` used as a behaviour test.** It passes precisely while the feature
   is missing. Implement the feature and it goes red, so somebody deletes it — and now that spot has no
   test at all.
4. **The test reads the implementation back.** The AI sees `if score >= threshold` and writes a test using
   `>=`. If `>=` was the bug and `>` was correct, the test has locked the bug in forever.

**The rule here: whoever writes a test does not get to grade it.** Not because AI is untrustworthy — anyone
writing tests has an incentive to make the scoreboard look good, including you at 6 pm on a Friday. So a
cell's band is **derived from evidence**, never self-declared. See §7.

---

## 4. Coverage — and why `line coverage` is the wrong denominator

`line coverage` answers: *"what percentage of code lines did the tests execute?"*

That measures **code**. What we need to measure is **risk**. The gap is larger than it sounds.

The fence in this kit has 5 variables that actually decide whether a chunk escapes:

| Variable | Values |
|---|---|
| `tenant_scope` | same tenant · different tenant · **unset** · client-declared |
| `section_role` | authorized · unauthorized |
| `entry_path` | `studio_app` pool (non-owner) · `studio_owner` pool (owner + `FORCE RLS`) |
| `provider` | fixtures stub · real gateway |
| `kb_state` | stub 5 docs · real ingest · post re-index · post consent-purge |

Multiply: 4 × 2 × 2 × 2 × 4 = **128 cases**.

Say you write 6 tests. They hit 6 cases and may touch **95% of the lines** in `search.py`, because all 128
cases run through nearly the same code. The tool reports 95%. That number is **correct**, and it says
nothing about the other 122 cases.

> **The point:** `line coverage` has no denominator for risk. Its denominator is the set of lines the
> tests happened to touch.

**The grid is that denominator.** It lists the 128 cells, weights each zone by risk, and produces a
verdict. Two rules matter most:

- **Roll up by taking the MINIMUM of each zone, never the average.** An average lets one strong cell hide
  an empty one. A zone with 40 good cells and 1 empty one is an **empty** zone.
- **A cell in a blocking zone with no evidence becomes `unknown`, and `unknown` blocks acceptance.**
  `unknown` is not `LOW`. `LOW` means "looked at it, it is thin". `unknown` means "nobody looked". The
  second is far more dangerous.

**The grid does not ask you to write 128 tests.** It exists so you **know what you are not looking at**.
Choosing `t=2` — every pair of values must appear together at least once — cuts 128 cells to a few dozen
rows while guaranteeing no **pair** of variables has gone untried. Blocking zones use `t=3`, every triple.

**Why blocking zones need `t=3`:** some bugs need three things at once. Take *tenant unset* +
*role unauthorized* + *via owner pool*. Every pair among those three already has a passing test. The
triple has never been tried. `FORCE ROW LEVEL SECURITY` is in the schema precisely because of that
triple.

### Two kinds of "not applicable", and why the difference is load-bearing

A cell you are not going to fill needs a marker, and there are two honest markers:

| Marker | Meaning | Counts as covered? | Blocks acceptance? |
|---|---|---|---|
| `na:<rule-id>` | structurally impossible — can never occur | yes | no |
| `todo:<seam-id>` | possible, but the code does not exist yet | **no** | **yes, if in a blocking zone** |
| nothing | forgotten | no | yes |

This distinction was added after Grid 4 came back with 31 of 36 cells marked N/A — of which **30 were not
impossible, just unbuilt**. Marking those the same way silently converts *"nobody built the dashboard"*
into *"the dashboard does not need testing"*. An `na:` with no matching rule id, or a `todo:` with no named
seam, counts as `unknown`.

---

### 4.1 How to choose axes — the part you will have to do yourself

Everything above tells you what a grid *is*. This tells you how to build one, because on your next project
nobody will hand you the axes.

**An axis is a variable the subject's behaviour causally depends on.** That is the whole test, and it is
stricter than it sounds. For each candidate, name the line of code where changing its value changes what
happens. If you cannot name one, it is not an axis — it is a label.

Four traps, all of which I walked into while building this set. They are documented with the measurements
because a rule you have seen fail is worth more than a rule you have been told.

#### Trap 1 — making an OUTPUT an axis

My first Grid 3 had `verdict {PASS, FAIL}` and `threshold {above, at, below}` as independent axes. But
`verdict` is *computed from* the score and the threshold. It is an output.

The symptom: 12 of 24 cells were impossible **by definition**, and the one cell that looked most valuable —
"score above threshold, verdict FAIL" — could only be filled by hand-constructing `Gate(verdict="FAIL")`.
That is manufacturing a false green and then counting it as coverage. **A wrongly chosen axis actively
produces the defect the grid exists to detect.**

The fix is always the same shape: demote the output to an **oracle column** (the expected result), and find
the real inputs. Grid 3 became `rel_success × rel_citation` — where each score sits relative to its own
threshold — which are genuinely independent and bought four cells that distinguish AND from OR semantics.

Then I added Grid 5 with `grounding × answer_shape` and **reproduced the identical defect one section later**:
`executors.py:251` computes `"refused": not citations`, so at the stub `answer_shape` is a pure function of
`grounding`. Knowing the rule is not the same as applying it. **Check every new grid against it explicitly.**

> **The tell:** if filling a cell requires constructing the thing you are supposed to be measuring, that
> coordinate is an output.

#### Trap 2 — bolting the same axis onto every grid

I added `provider` and `kb_state` to all five grids at once, reasoning that `t`-wise needs a thick grid to do
any work. The arithmetic said the set went from 66 cells to 300.

Then I computed the row set. Across **all 45 live rows**, `provider` took exactly **one** value, because every
`real-gateway` cell was waiting on unbuilt code. An axis with one value in the live rows discriminates
nothing. It had inflated the denominator by 234 cells and the numerator by zero.

**Test each grid separately:** does *this* grid's subject vary with *this* axis? For the fence, the answer was
no — the fence is SQL, and the embedding provider never touches the policy expression. For provenance, the
answer was yes — real tokens versus a hardcoded `0.0` is precisely the provenance question.

#### Trap 3 — writing exclusion rules after seeing which cells are empty

Rules that mark a combination impossible must be **frozen before any cell is filled**. Write them afterwards
and you are converting "nobody did this" into "nobody needs to do this", one cell at a time, with a
justification that feels reasonable each time.

Related, and it cost a whole zone here: **"impossible" and "not built yet" are different facts.** Grid 4 came
back with 31 of 36 cells marked N/A — of which **30 were merely unbuilt**. Marking them the same way turned
"nobody wrote the dashboard" into "the dashboard needs no testing". Hence three markers, not one: `na:`,
`todo:`, `defer:` (§4, last part).

#### Trap 4 — quoting a size you have not computed

I estimated this grid's size three times and was wrong three times, always the same way: multiplying axis
values without applying the exclusion rules. Claimed 110–140 rows over ~300 cells; the generator produced 45
real cells and 37 rows.

Write the generator first. It is fifty lines, it is deterministic, and it makes the numbers diffable when an
axis changes. Every counting error in this design came from a hand-maintained number drifting away from the
axes it was supposed to describe.

#### The checklist

1. List every variable the subject could depend on.
2. For each, name the code path where its value changes behaviour. No path ⇒ drop it.
3. For each, ask: is this an **input** or a **computed result**? Results become oracle columns.
4. Do steps 2–3 **per grid**. An axis that earns its place in one grid is decoration in another.
5. Freeze the exclusion rules, with ids and reasons, **before** filling anything.
6. Separate "impossible forever" from "not built yet".
7. Generate the row set with a script. Read the numbers off the output, never off your own arithmetic.
8. Look at the live rows: does every axis take more than one value? If not, it is not doing work yet — say so
   rather than letting it pad the denominator.

---

## 5. Mutation testing — an instrument, not a scoreboard

**The question it answers:** *"does my test suite catch bugs?"*

**How:** change one thing in the production code (create a `mutant`), then run the suite.
- Suite goes red ⇒ **mutant killed**. The tests do something there.
- Suite stays green ⇒ **mutant survived**. The tests do not protect that spot, even at 100% coverage.

Concrete example — the RLS policy on `kb.chunks`
(`packages/kb/src/studio_kb/schema.py:52-58`):

```sql
ALTER TABLE kb.chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb.chunks FORCE ROW LEVEL SECURITY;

CREATE POLICY kb_chunks_tenant_isolation ON kb.chunks
    USING      (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
```

> ⚠️ `docs/system-architecture.md` §4.3 quotes this policy **without `NULLIF(...)::uuid`** — that version
> predates D-13 (tenant identity became a UUID). **The code wins.** If doc and code disagree elsewhere,
> trust `schema.py`. The three fail-closed layers live inside that expression; the docstring at
> `schema.py:7-10` explains each one.

Six mutants against the fence, each one a way this system could actually have broken. The right-hand
column is **measured**, not predicted:

| Mutant | Change | Tests that go red today |
|---|---|---|
| `M-R#1` | drop the `USING` clause | **5** |
| `M-R#2` | replace `WITH CHECK` with `WITH CHECK (true)` | **1** |
| `M-R#3` | drop `FORCE ROW LEVEL SECURITY` | **1** (the same test as `M-R#2`) |
| `M-R#4` | drop `NULLIF(...)` → `COALESCE(..., tenant_id)`, i.e. **fail-open** | **4** |
| `M-R#5` | request path switches to `get_admin_pool()` | **0** |
| `M-R#6` | `SET LOCAL` → `SET` in `middleware.py` | **0** at the middleware |

Two of six are completely unguarded. That is the kind of fact you cannot get from a coverage report.

**A detail worth knowing, because it will bite you:** the obvious form of `M-R#2` — deleting `WITH CHECK`
entirely — is probably an **equivalent mutant**. Postgres falls back to the `USING` expression for writes
when `WITH CHECK` is absent, so nothing observable changes and the mutant looks unkillable when the tests
are fine. You have to write `WITH CHECK (true)` to actually open the write path. Same story for `M-R#5`:
`FORCE RLS` neutralises it, so it only means anything as a **second-order** mutant applied together with
`M-R#3`.

**And one special mutant, `M-E`, which measures the tests rather than the code:** make `search()` return
`[]` unconditionally. Every test with only an **exclusion** assertion passes. That is how the T6 hole in
§1 gets caught mechanically, without anyone having to be sharp-eyed.

### Mutation testing is not a scoreboard

This is the most common misreading. Suppose `mutation score = 92%`. That is **92% of the mutants planted
in the code the tests already execute**. It has no idea the other 122 cases from §4 exist. It has no
concept of the "tenant unset + unauthorized role + owner pool" branch if no test has ever gone there.

> **The point:** mutation testing is an instrument **inside one cell**, not the scoreboard for the grid.
> Here it is demoted to a **single condition**: a cell in a blocking zone may reach band **HIGH** only with
> evidence that a real mutant died. Without that evidence it caps at **MEDIUM**.

---

## 6. DST — the bug class mutation testing structurally cannot reach

Some bugs live in code where **every line is correct**.

Real example in this kit:

`middleware.py` takes one connection from the pool per request, runs
`SET LOCAL app.tenant_id = '<uuid>'`, and keeps that connection in a `ContextVar` for the request's
lifetime. `SET LOCAL` only applies inside the current transaction and resets when it ends, so the
connection returns to the pool carrying no stale tenant.

That reads fine. Now ask three questions:

- If the middleware does not open a transaction, when does `SET LOCAL` reset?
- If an exception is raised inside `call_next()`, what state does the connection return in?
- If the next request, for a different tenant, gets that same connection, what does it see?

If such a path exists, **tenant B reads tenant A's data**. `leakage = 0` falls. And **every single-request
test stays green**, because each one opens a clean connection for itself.

This one is not hypothetical, and the measured answer is more uncomfortable than the question:
`SET LOCAL` at `middleware.py:80` *is* inside a transaction today — **by accident**. The `SELECT` at
`:62` already emitted a `BEGIN`. Remove that query, which the docstring at `:51-56` explicitly plans when
it switches to JWT, and `SET LOCAL` emits a warning and is discarded. The fence disappears with no test
failing.

**Why mutation testing cannot solve this:**

Mutation testing changes **code**. This bug is in no line of code — every line is right. It lives in
**execution order**, decided by the event loop and the pool, not by anything you wrote. You cannot plant a
mutant in something that is not code.

Worse: suppose you *do* plant a mutant in a function involved here. Run the suite — green, mutant survived.
Mutation testing concludes *"your tests are weak here"*. **That diagnosis is wrong:** the tests are not
weak, they have simply never been run in the order that exposes the bug.

**The fix is to take control of the ordering.** Instead of waiting to get unlucky (1 in 10,000), you
**force** it. Put an `asyncio.Event` in as a `barrier`: hold request A right after it takes its connection,
let request B run through, then release A. That test is **deterministic** — same result every run.

That is the core idea of **DST (Deterministic Simulation Testing)**: one `seed` decides every branch point,
so a run reproduces bit for bit. This set does not build a full DST engine. It uses the part that pays off
immediately — **a deterministic barrier to force ordering** — for four specific flows (`S1`–`S4` in the
guide files).

Note what you are starting from: the repo currently contains **zero** barriers. `asyncio.Event`: 0
occurrences. Advisory locks: 0. `asyncio.gather`: 1. Every ordering test is new construction.

> Worth knowing for later: a serious DST engine does **not** use `random.Random(seed)`; it uses a sha256
> counter stream. `random.Random` only guarantees reproducibility **within one CPython build**, and
> evidence has to reproduce on another machine, another Python, next year. For four barrier-driven flows
> that does not matter. If you extend into randomised exploration, it will.

---

## 7. A cell's band is DERIVED, never declared

The most important rule in the set, and the easiest to break without noticing.

**You do not get to write "this cell is well covered".** You supply **evidence**; the band follows from the
evidence by a written rule.

Example — cell `cross tenant × authorized role × app pool`, in a blocking zone:

```
REQUIRED (missing any line ⇒ cell = unknown ⇒ blocks acceptance)
  [1] an INCLUSION assertion  — tenant A's own matching chunk must come back
  [2] an EXCLUSION assertion  — no chunk belonging to tenant B
  [3] goes through the non-owner pool — otherwise RLS does not apply
  [4] evidence that mutants M-R#1 AND M-R#4 were killed

DERIVED BAND
  all of [1..4]  ⇒ HIGH
  missing [4]    ⇒ MEDIUM
  missing [1]    ⇒ unknown   (NOT low)
```

Look at the last line. Without the inclusion assertion the cell **measures nothing** — that is exactly
case T6. It is not "thinly covered", it is "not covered". Calling it `LOW` is lying to yourself.

**Three things that never count as evidence:**

- `pytest.raises(NotImplementedError)` — proves the feature is **absent**, not that it is right
- `xfail` / `skip` — a test that did not run is not evidence
- a sentence in a daily note or PR description saying "tested thoroughly"

### 7.1 The rule above has a hole, and here is the patch

The template in §7 mandates an **inclusion** assertion so that an exclusion cell cannot be satisfied by an
empty result. That works for leak cells. It does **nothing** for cells where the correct answer *is* empty —
and a whole blocking zone is made of those.

Consider the cell "tenant not set ⇒ 0 rows". The required outcome is an empty result, so:

```python
assert results == []
```

goes green against: an empty database, a migration that never ran, a broken fixture, a `search()` that still
raises, and a typo in the query. Mutant `M-E` cannot help here either — returning `[]` is the *expected*
answer, so the mutant that catches false-green everywhere else is blind in exactly this zone.

**Every cell whose expected result is empty additionally requires:**

```
(a) a PAIRED POSITIVE CONTROL in the same test — the same query, the same corpus,
    but with the tenant set, returning N > 0 rows. This is what separates
    "the fence worked" from "there was nothing to find".
(b) kill evidence for the mutant that actually flips this cell's outcome —
    M-R#4, the fail-open COALESCE. Not M-E.

Missing either ⇒ unknown, not LOW.
```

Read (a) again, because it is the whole cell: "zero rows" is trivially true of a working fence and of five
kinds of broken setup. Only running the same thing twice, once each way, tells them apart.

### 7.2 A pin-test asserts a decision, not a behaviour

You will hit this, so know the rule before you do.

This repo has a `KHÓA` idiom: green tests whose job is to pin the *current configuration* in place. There are
more than ten of them. `tests/test_ops.py:145-155` is one — it asserts `continue-on-error is True` for the
`leak-test` job, which means fixing the biggest hole in the suite turns a passing test red.

That is not sabotage. It is a decision, recorded as a test so nobody reverts it by accident.

**The rule:** a pin-test asserts a *decision*. When the decision changes, the pin-test changes **in the same
commit**, with a reference to the decision. Doing that is not weakening a gate.

Every must-fix row in your guide lists its **pinned-by** tests for this reason. If you find a pin-test the
guide did not list, that is a gap in the guide — report it. Do not route around it in either direction: not
by silently deleting the pin, and not by deciding the fix is impossible.

---

## 8. Three layers, none of which substitutes for another

| Layer | Question it answers | Bug class it catches | What it **cannot** catch |
|---|---|---|---|
| **Grid** (`t`-wise) | which risky cases has nobody tested? | untried configuration combinations | ordering bugs; false-green tests |
| **Mutation** | does my suite catch bugs? | weak assertions, false green, misleading `line coverage` | untested cases; ordering bugs |
| **Deterministic ordering** (DST-lite) | what happens on that specific interleaving? | races, leaks via recycled state, operations stepping on each other | everything the two above handle |

```
mutation testing  →  "does your suite catch bugs?"        →  a number
                                    │
                                    ▼
this acceptance set →  "which risky cases has nobody tested?"  →  BLOCK / PASS
                     ├─ grid      = the list of cases + risk weights   (denominator)
                     ├─ mutation  = instrument gating HIGH in blocking zones
                     ├─ ordering  = fills what tests normally cannot reach
                     └─ derived bands = whoever writes a test does not grade it
```

**This set does not end in a score. It ends in a verdict**, and the verdict may be **block**. That is the
difference from every measurement tool you have used: a measuring tool may return a number and go home;
something that decides has to hold up against the person it blocks.

---

## 9. What you actually do

1. Read your **own quadrant's** guide (`GUIDE-A` … `GUIDE-D`) plus `01-FOUNDATION.md`. You do not need to
   read anyone else's.
2. Every row in a guide is a grid cell with an id (for example `A1-03`). Your test must **carry that id in
   its docstring**, so it can be reconciled later.
3. Cells in a **blocking zone** need mutation evidence: plant the mutant from the guide's map, run the
   test, record **which assertion line went red**, then remove the mutant. If it went red on a different
   line than expected, that is also a signal — write it down.
4. Flows `S1`–`S4` need deterministic barriers. The guide names the insertion point.
5. If a guide is wrong, or a cell cannot be built: **say so, do not work around it.** A wrong guide is
   ordinary. A test bent to fit a wrong guide is the bad outcome.

**Three things never to do:**

- ❌ Loosen an assertion to get green
- ❌ Add `skip` / `xfail` to keep the suite green. If you must, record the cell id, the reason, and the
  condition for removal, right there in the code
- ❌ Use `pytest.raises(NotImplementedError)` as the test for a grid cell

---

## 10. Glossary

| Term | Meaning |
|---|---|
| **assertion** | a claim inside a test; if false, the test goes red |
| **band** | a cell's grade: `HIGH` · `MEDIUM` · `LOW` · `unknown` · `stub` |
| **barrier** | a hold point that keeps one task at a chosen spot so ordering happens the way you want |
| **blocking zone** | a high-risk zone; one cell lacking evidence there blocks the whole acceptance run |
| **coverage** | here it always means covering the **risk space**, not covering code lines |
| **DST** | Deterministic Simulation Testing — reruns identically because you own the ordering, not the OS |
| **equivalent mutant** | a mutant that changes nothing observable, so it looks unkillable when the tests are actually fine |
| **fail-closed** | missing information ⇒ **deny** (0 rows). The opposite, `fail-open`, lets it through |
| **flaky** | passes and fails on unchanged code |
| **grid** | the table of case combinations that must be tested, with risk weights |
| **interleaving** | the order in which concurrent work is stitched together |
| **`leakage`** | one tenant's data reaching another tenant |
| **mutant** | a copy of the code with one thing deliberately changed, used to test the tests |
| **mutation testing** | planting mutants to grade the **test suite**, not to find real bugs |
| **`na:` vs `todo:`** | impossible-forever vs not-built-yet. `todo:` does not count as coverage |
| **race** | two operations stepping on each other; the result depends on ordering |
| **seed** | the number driving every "random" choice; same seed, same run |
| **`t`-wise** | covering every **pair** (`t=2`) or every **triple** (`t=3`) of variable values |
| **unknown** | "nobody tested this cell". Different from `LOW` = "tested, and it is thin" |
| **xanh giả** (false green) | a passing test whose assertion is true regardless of the code — the repo's own term, from `test_pg_kb.py` |

---

## 11. Further reading

- `sdlc-harness/docs/research/feature/tot-grid-coverage/README.md` — the machine this method comes from.
  Read §1–§5.
- `document-intake/docs/retention/test-guide/` — **the direct predecessor of this set.** Six files, same
  method, different system (a data-retention feature). Worth reading for two things:

  **What was reused unchanged:** the file layout (one common foundation + one guide per owner + one matrix),
  the "a band is derived, never declared" rule, the frozen-before-filling exclusion rules with `rule:` ids,
  and the three-layer split of grid / ordering / mutation.

  **What was deliberately changed, and why** — this is the more useful half, because each change is a defect
  that set shipped with:

  | There | Here | Because |
  |---|---|---|
  | one `N/A` marker | three: `na:` / `todo:` / `defer:` | one marker let "nobody built it yet" and "this can never happen" produce the same number |
  | four acceptance conditions, prose-checked | seven, each naming a command | two of the four turned out to be satisfiable without checking anything — the same trap this set walked into again and had to fix in round 5 |
  | bands derived by hand | `tools/derive_bands.py` | ~60 cells cannot be hand-derived in gate week, and what does not get done gets improvised |
  | cell ids reconciled by reading | `tools/xcheck_cell_ids.py` | ids drift silently between the two tiers, and silent drift always fails toward "looks covered" |
  | ordering scenarios with no band | ordering flows banded like any other cell | unbanded scenarios made the acceptance condition covering them vacuous |

  If you ever build one of these yourself, read that set first and this table second. Most of what is
  different here exists because something over there did not hold.
- `docs/requirements/00-orientation/umbrella-contract.md` §3 and §7 — the source of every hard AC this set
  enforces.
