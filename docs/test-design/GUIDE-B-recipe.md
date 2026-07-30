# GUIDE B — Recipe lifecycle (Grid B)

**Owner: SWE.** Read `00-METHODOLOGY.md` and `01-FOUNDATION.md` first. You do not need the other guides.

This grid covers `graph_lint`, `publish`, `rollback` — money-shot step 7. Two of those three functions do
not exist yet, so most of this guide is a **schedule**: what you can build today, what unlocks when your own
seam lands, and what is not a test gap at all but a missing schema.

You also own two rows that belong to no grid: the **pool / connection** rows of surface 5 (§11) and the
ordering flow `S1` (§8). Surface 5 was owned by "nobody" until the escalation review; the register assigned
the pool half to you (CP-2.8).

---

## 1. What this grid is measuring

| Axis | Values | Where the value comes from |
|---|---|---|
| `recipe_validity` | `valid` · `node-outside-6` · `cycle` · `dangling-edge` · `tool-outside-whitelist` · `when-never-true` · `entry-unreachable` · `duplicate-node-id` | how the `Recipe` handed to `graph_lint` breaks (or does not break) one of the 4 rules in `validator.py:7-19` |
| `publish_state` | `unpublished` · `v1-live` | **endpoint** state at the moment of the assertion — which version the named endpoint serves, not the state of the recipe being submitted (`rule:publish-state-means-endpoint`, register §3) |

8 × 2 = **16 cells**. After the exclusion rules:

| | count | |
|---|---|---|
| `na:` — impossible, will never be testable | **7** | 1 rule, §2 |
| `todo:` — possible, seam not built yet | **1** | 1 seam, §3 |
| **real** — buildable against code that exists today | **8** | |
| **rows to write now** (`t=2`, non-blocking grid) | **8** | §5 |

"Buildable today" means the **test** is buildable today, not that it passes today. `graph_lint` raises
`NotImplementedError` (`validator.py:41-43`), so 7 of the 8 rows are **red until you implement it**. Red for
that reason is correct and is the whole point of writing them first. What is not allowed is making them green
with a marker — see §4.2, which is the single worst trap in this quadrant.

> **There is no `provider` axis and no `kb_state` axis here, deliberately.** `graph_lint(recipe)` takes one
> frozen value object (`validator.py:32`; `Recipe` is `frozen=True` at `recipe.py:86`),
> `publish(recipe, scorecard)` takes two (`publish.py:34`, with `Scorecard` frozen at `scorecard.py:59`), and `studio_workbench` imports nothing but `studio_contracts` (`builder.py:10`,
> `publish.py:31`, `validator.py:29`) because `.importlinter:15-21` forbids more. No provider and no KB state
> can reach these three functions, so varying them would multiply cells without discriminating anything.
> One exception exists and it has no home in the grid — see §10, Q11.

**This grid is not in a blocking zone** (generator header, the generator output, Grid B: `blocking=False`).
Your blocking-zone work is elsewhere: `publish`/`rollback` returning the wrong version is **zone 3**
(register §4), and the pool rows in §11 sit in **zones 1 and 2**. Do not read "non-blocking" as "cheap": the
8 rows here are the only thing standing between a mutated `graph_lint` and the interpreter.

---

## 2. `na:` rules — and one place where this rule and the register disagree

| Rule id | Combination | Why it can never happen |
|---|---|---|
| `na:invalid-recipe-cannot-be-live` | the 7 invalid `recipe_validity` values × `publish_state=v1-live` | `publish.py:6-8` runs `graph_lint` **first** and states *"a recipe that fails graph-lint is never published"*. A recipe that cannot be published can never be the version an endpoint serves, and can never be a version `rollback` restores to. 7 cells |

**Read that rule again, because it encodes the opposite reading of `publish_state` from the one §1 states.**

- Register §3 froze `rule:publish-state-means-endpoint`: `publish_state` describes the **endpoint**, and
  `recipe_validity` describes the recipe being **submitted**. Under that reading, "submit a broken recipe
  while v1 is live" is a perfectly possible cell — and it is the money-shot step-7 cell.
- The generator marks those 7 cells `na:`, which is only true under the **other** reading (the
  recipe under test is itself the live one).

The generated rows are the rows; this guide does not invent or renumber them. But the disagreement is
recorded here rather than smoothed over, because the cell it removes is the most valuable one in the grid,
and turning "nobody built `publish` yet" into "this need not be tested" is the exact failure mode the two
markers exist to prevent (`00-METHODOLOGY.md` §4). **If the mentor confirms the endpoint reading, those 7
cells are `todo:publish-seam`, not `na:`** — 8 cells on that seam instead of 1. Raise it; do not decide it.

**A cell marked `na:` without that rule id counts as `unknown`, which blocks.** Prose saying "not applicable"
does not count — it is equally true of an impossible cell and a forgotten one.

---

## 3. `todo:` cells — 1 today, and the seam is yours

| Seam id | Cells | What has to exist | Owner | ETA |
|---|---|---|---|---|
| `todo:publish-seam` | 1 (`valid × v1-live`) | three things, not one: **(X-1)** a `publish` body that reads `scorecard.gate.verdict` and branches (`publish.py:42-44` is `NotImplementedError` today; the field exists — `scorecard.py:51`, `Literal["PASS","FAIL"]`); **(X-2)** somewhere that expresses *"this version is live"* — no column, no table, nothing (§4.6); **(X-3)** a `rollback` body that reads `wb.recipe_versions` (`publish.py:53-55` is `NotImplementedError`) | **SWE (you)** | **Day 20** |

The ETA is Day 20, not Day 30, and the reason is mechanical: this seam gates a **blocking zone 3** cell plus
both `M-G` mutants in §7 plus flow `S3` in §8. A `todo:` in a blocking zone that has not landed by Day 20
auto-escalates to a sign-or-descope decision (register CP-2.3); it does not sit quietly until Day 30.

At Day 30 a `todo:` cell is judged like this: seam landed and cell filled ⇒ covered. Seam landed and cell
still `todo:` ⇒ **blocks**. Seam formally descoped through the INV-7 ladder with a recorded decision ⇒ becomes
`defer:<decision-id>`, which does **not** block and does **not** count as covered. Seam neither landed nor
descoped ⇒ blocks, and what is blocked is the *feature*.

One thing you must not do: satisfy X-2 by hand-inserting `status='published'` into `wb.recipes`
(`schema.py:34`). **No code reads that column** — the docstring says the state machine is *"spec-only for
now"* (`schema.py:10-11`) and there is no `CHECK` constraint, so the column accepts any string. An assertion
about a value nothing consumes is anchored to nothing.

---

## 4. Things you must know before writing a single test

Measured facts about the current tree. Each one changes what a correct test looks like.

### 4.1 One of your three seams is already built, and it is the model to copy

The register and `docs/system-architecture.md:22,99,260` all list `resolve_tenant` as an empty spec seam.
**That is stale.** `tenant_wall.py:71-139` is a real implementation with four fail-closed branches, and
`test_wiring_d8.py` holds **17** cases, none skipped, none `xfail`, all green — measured
(`17 passed in 0.02s`) on `packages/workbench afa805dc`. The quadrant deep-dive says 14; the number of record
is 17. It has symmetric pass/fail pairs
and matches on the error message.

Read that file before writing anything here. It is the only place in your quadrant where the shape this guide
asks for already exists. Its one weak case is instructive too: `test_wiring_d8.py:129-142` is named
*"ignores client-declared tenant in body"* but never passes the attacker body into the function
(`:137` builds it and drops it), so `assert result != OTHER_ID` (`:142`) is true no matter what the function
does. That is a mild false green (**xanh giả**) inside the strongest test file in the quadrant.

`graph_lint` (`validator.py:41-43`), `publish` (`publish.py:42-44`) and `rollback` (`publish.py:53-55`) are
all still `NotImplementedError`. `publish` and `rollback` have **no test at all** — not even a stub-pinning
one.

### 4.2 `test_graph_lint.py` cannot report red in any code state — measured, not argued

Both of the file's cases carry `@pytest.mark.xfail(strict=False)` (`test_graph_lint.py:64` and `:73`), and
`xfail_strict` is not set in `pyproject.toml` (`[tool.pytest.ini_options]` is at `:68`).

Measured today, `2026-07-30`, on the pinned tree:

```
$ .venv/bin/python -m pytest packages/workbench/tests/test_graph_lint.py -q -p no:cacheprovider -rsxX
XFAIL packages/workbench/tests/test_graph_lint.py::test_lint_rejects_bad_graph
XPASS packages/workbench/tests/test_graph_lint.py::test_graph_lint_not_implemented
1 xfailed, 1 xpassed in 0.10s
```

`0 failed`. Under `strict=False` **both** outcomes are non-failing, so the file reports the same verdict in
three different worlds:

| `graph_lint` body | case 1 (`raises NotImplementedError`) | case 2 (the 4 rules) | suite |
|---|---|---|---|
| today's stub | XPASS | XFAIL | `0 failed` |
| correct, all 4 rules | XFAIL | XPASS | `0 failed` |
| `def graph_lint(recipe): return None` | XFAIL | XFAIL | `0 failed` |

A correct implementation and an empty one produce the identical result. This is the `xanh giả` class one level
up from the assertion: not *an assertion that is always true*, but *an outcome that is always green*.

**Consequence for you:** none of your 8 rows may live in a file where a marker can absorb the result. Your
rows go in a new file with no `xfail` anywhere, and the two existing cases get flipped as described in §5.1 —
in the same commit as the implementation, with the decision reference (`00-METHODOLOGY.md` §7.2).

### 4.3 The builder in your own package produces a recipe that violates rule 4

`builder.py:174` (in `create_recipe_d4`) and `builder.py:250` (in `create_recipe_d6`) both read:

```python
params={"tool": tool_whitelist[0] if tool_whitelist else "kb_search"},
```

Measured by running it:

```
create_recipe_d4(agent_id='a', kb_id='k', scope='ankor/public', tool_whitelist=[])
  -> agent_config.tool_whitelist == []
  -> dag.nodes[2] == ('n3', 'tool-call', tool='kb_search')
```

So the `else` branch fabricates a tool name that is not in the whitelist — exactly what rule 4
(`validator.py:17-19`) forbids. `create_recipe_d6(..., tool_whitelist=[], ...)` does the same.
`builder.py:136-138` only substitutes the default when `tool_whitelist is None`, so `[]` passes straight
through.

Two consequences. First, **the mutant that drops rule 4 already has a victim recipe waiting inside your own
package** (§7.3). Second, when you implement `graph_lint`, your own builder starts producing recipes your own
validator rejects. That is not a bug in the validator. Do not "fix" it by loosening rule 4.

No existing test catches this: `test_builder.py:35-65` passes `tool_whitelist=[]` but builds no `tool-call`
node, and `test_wiring_d6.py:88-103` checks the whitelist-driven tool only with a non-empty whitelist.

### 4.4 The 4 rules are bundled into one test function, so per-rule mutants are indistinguishable

`test_lint_rejects_bad_graph` (`test_graph_lint.py:74-151`) checks all four rules in one body: rule 1 at
`:96`, rule 2 at `:114`, rule 3 at `:126`, rule 4 at `:150`. `pytest` stops at the first failing assertion, so
rule 1 masks the other three. A mutant that removes only rule 4 is not distinguishable from one that removes
only rule 1.

**Every row in §5 is its own test function** (or its own `parametrize` case with its own id). This is not
style; it is what makes the mutant map in §7 measurable at all.

### 4.5 `publish` and `rollback` have no legal path to Postgres, and the cheapest illegal one destroys the fence

`publish.py:18-19` requires writing to `wb.recipes` + `wb.recipe_versions`, and `publish.py:21-22` requires
`rollback` to read `wb.recipe_versions`. But:

- neither signature takes a pool or a connection — `publish(recipe, scorecard)` (`publish.py:34`),
  `rollback(agent_id, tenant, *, to_version)` (`publish.py:47`);
- `.importlinter:15-21` puts `studio_workbench` on a layer that cannot import `studio_app`, where
  `get_pool()` lives (`apps/studio/src/studio_app/core/_db.py:52`);
- `studio_contracts.protocols` defines exactly three protocols — `EmbeddingService`, `LLM`, `TraceWriter`
  (`protocols.py:17,27,36`). There is **no protocol for a recipe store or a pool**.

Three ways out, and each one breaks something: importing `studio_app` trips the import-fence job; opening your
own `psycopg` connection inside `studio_workbench` passes the fence but writes on a connection that never ran
`SET LOCAL app.tenant_id` (`middleware.py:80`), which silently removes RLS from the publish path; changing the
signature is the architecturally correct move but changes a seam that is being graded, and `publish.py:24-26`
says this module *"only specifies the wiring contract"*.

**This is open question Q5 (§10) and you must not pick a lane on your own.** It also produces a mandatory
assertion class in §11: whatever the answer, `publish` must be shown to write through the **same** connection
that carries the request's `SET LOCAL app.tenant_id`.

### 4.6 `wb.*` holds tenant data with no RLS, and its tenant column is the wrong type

`schema.py:28-48` has no `ENABLE ROW LEVEL SECURITY`, no `FORCE`, and no `CREATE POLICY`. Compare
`packages/kb/src/studio_kb/schema.py:52-58`, which has all three on `kb.chunks`. And `wb` is the only schema
whose tenant column is `tenant TEXT` (`schema.py:31`, `:43`) rather than `tenant_id UUID` — contrast
`studio_kb/schema.py:40` and `apps/studio/src/studio_app/obs/schema.py:23`.

Meanwhile `apps/studio/src/studio_app/core/schema.py:124-136` grants `SELECT, INSERT, UPDATE, DELETE` on all
tables of all five schemas to `studio_app`. So the moment `publish` starts writing recipes, the app pool can
read every tenant's `agent_config.instructions` and `kb_binding.scope` out of `wb.recipes` with nothing to
stop it. Nothing exploits this today because no code selects from `wb.recipes` — it is a DDL hole waiting for
your seam, which is why it is specified here ahead of the code.

Whether `wb.*` must carry RLS is **Q7**; whether the column type must change is **Q6** (an INV-5 breaking DDL
change if yes). Both are in §10.

### 4.7 `wb.recipe_versions` is not the append-only history its docstring claims

`schema.py:13-14` calls it *"append-only history … so `publish.rollback()` has something to roll back TO"*.
Two independent defects:

- `schema.py:41` is `recipe_id UUID NOT NULL REFERENCES wb.recipes (id) ON DELETE CASCADE`. Deleting one
  `wb.recipes` row deletes that agent's entire version history. A table someone else can empty is not
  append-only — and `conftest.py` `_truncate_all` issues `TRUNCATE … CASCADE` per table between DB tests.
- it has **no** `UNIQUE (agent_id, tenant, version)`, while `wb.recipes:36` does. Two rows with the same
  `(agent_id, tenant, version)` and different content can coexist, which makes
  `rollback(..., to_version=N)` non-deterministic — there is no `created_at` tie-break in the spec.

Your `rollback` rows (§7.2) must therefore assert on **content**, not only on a version number.

### 4.8 The kit has no HTTP route, and that changes how you build `S1`

`create_app()` (`app.py:42-47`) registers the lifespan and `tenant_context_middleware` and **nothing else** —
no router, no endpoint. So a request-path test cannot call a product route, because there is none. Mount a
route inside your test on the app returned by `create_app()`, and say so in the docstring: the route is test
scaffolding, the middleware and the pool are the product code under test. Do not add a route to `apps/studio`
to make a test possible — that is a product change, and route ownership is Q5 in the register (§12).

---

## 5. The 8 rows

All 8 are the `publish_state=unpublished` column: they call `graph_lint` directly, with no endpoint and no
database. Target band is the band a complete cell reaches, not a promise. **Pinned-by** lists the `KHÓA`
pin-tests that must be flipped in the same commit as the work this row depends on (`00-METHODOLOGY.md` §7.2).

| id | `recipe_validity` | `publish_state` | Target | §6 | Pinned-by |
|---|---|---|---|---|---|
| B01 | valid | unpublished | HIGH | 6.1 | `test_graph_lint.py:64` (`KHÓA`, `:66`) |
| B02 | node-outside-6 | unpublished | HIGH | 6.2 | `test_graph_lint.py:73` (`KHÓA`, `:75`) · `test_roundtrip.py:152` |
| B03 | cycle | unpublished | **MEDIUM** (capped, Q1) | 6.3 | `test_graph_lint.py:73` |
| B04 | dangling-edge | unpublished | HIGH | 6.2 | `test_graph_lint.py:73` |
| B05 | tool-outside-whitelist | unpublished | HIGH | 6.4 | `test_graph_lint.py:73` · `test_wiring_d6.py:88` |
| B06 | when-never-true | unpublished | **unknown until Q8** | 6.5 | — |
| B07 | entry-unreachable | unpublished | **unknown until Q8** | 6.5 | — |
| B08 | duplicate-node-id | unpublished | **unknown until Q8** | 6.5 | — |

Ids come from the generator and are not renumbered when rows are regrouped. The id is the stable
handle; the ordering here is for humans.

**Three of the eight axis values violate none of the four rules `graph_lint` is specified to enforce.**
`validator.py:7-19` lists exactly four: closed node type, no forbidden cycle, resolvable edge destination,
tool in whitelist. Nothing anywhere in the kit forbids a duplicate node id, requires the entry node to be
reachable, or evaluates `Edge.when` — `Dag` is two plain lists (`recipe.py:48-54`) and
`interpreter.py:10,79` records `Edge.when` as *"still unevaluated"*. The axis was widened from 5 values to 8 by the
register's §11 widening ruling, without a matching rule being added anywhere. So B06, B07 and B08 have **no oracle**: nobody
has said whether a correct `graph_lint` rejects them, warns, or accepts them. That is Q8 in §10, it is a
finding rather than an inconvenience, and it is why those three rows carry `unknown` rather than a band.

### 5.1 Must-be-green-before-Day-30 rows, and what pins them

The `L2-xx` ids are this quadrant's measured holes, numbered by the deep-dive that found them
(`round2-deepdive-2-recipe.md` §5) so the two documents can be read against each other.

| Row | What must change | Pinned-by — flip in the same commit | Why the pin is not sabotage |
|---|---|---|---|
| **L2-01** — `test_graph_lint.py` can never report red (§4.2) | split `test_lint_rejects_bad_graph` into 4 per-rule tests with no `xfail`; retire the stub-pinning case when the body lands | `test_graph_lint.py:64` and `:73` (both `KHÓA` docstrings, `:66`, `:75`) | Both markers record a real Day-7 decision: do not punish partial progress. Once `graph_lint` exists, the decision has changed, so the tests change with it |
| **L2-02** — the stale `xfail` on `test_wiring_d5.py:26` | remove the marker; the seam it waits on landed at Day 7 | `test_wiring_d5.py:26` | Its reason string says *"pending upstream engine release"*, and `test_wiring_d7.py:123` asserts `len(trace_writer.events) == 4` unconditionally and is green — so the seam is here. This is your only case watching trace node ordering, and it is in blocking zone 4 |
| **L2-09** — assertions behind an `if` in `test_wiring_d6.py:139` and `:179` | make both assertion blocks unconditional | `test_wiring_d6.py:107`, `:148` | Not a decision at all — just a guard that disables the thing it claims to check. See §9 |
| **L2-03** — the builder fabricates an out-of-whitelist tool (§4.3) | decide and record: reject `tool_whitelist=[]` with a `tool-call` node, or stop defaulting the tool name | `test_wiring_d6.py:88` | That test pins the whitelist-driven tool selection for a non-empty whitelist. Adding the empty-whitelist case does not weaken it |

Do not route around a pin in either direction: not by deleting it quietly, and not by concluding the fix is
impossible. If you find a pin-test this table does not list, that is a gap in this guide — report it.

---

## 6. What each row must prove

Grouped by proof obligation. Every row is its own test function (§4.4). Every test carries its cell id in the
docstring (`01-FOUNDATION.md` §9).

**One rule applies to all seven rejection rows, and it is the analogue of the empty-expected rule in
`00-METHODOLOGY.md` §7.1.** A cell whose expected result is *"the call raises"* is green against a
`graph_lint` that raises for **every** recipe — including valid ones. `assert results == []` and
`pytest.raises(...)` fail in the same way. So every rejection row requires a **paired positive control**: the
same lint call, in the same test, on a recipe that differs only in the one thing the row is about, which must
pass cleanly. B01 alone is not that control; it is a separate cell, and a rejection row that leans on it
proves nothing about *its own* fixture.

### 6.1 `valid` — B01

**Must prove:** a recipe that breaks none of the four rules passes `graph_lint` cleanly, and passing means
returning normally rather than returning a truthy report object.

```
REQUIRED
  [1] ACCEPTANCE — the call completes and returns None (validator.py:35-36:
      "never returns a boolean/error-list")
  [2] the accepted recipe is built through the ordinary constructors, not
      through model_construct — otherwise the row proves nothing about the
      path a real recipe takes
  [3] the recipe exercises a shape no existing fixture covers: a DAG with a
      branch or a join. All three builders emit a straight 4-node chain
      (builder.py:179-183, :255-259), so "valid" is today only ever tested
      as a line
  [4] mutant evidence: the "reject everything" mutant (§7.4) killed here

DERIVED BAND
  [1]+[2]        ⇒ MEDIUM
  [1..4]         ⇒ HIGH
  missing [1]    ⇒ unknown
```

This row looks like the easy one and it carries the whole grid: without it, **every** rejection assertion in
§6.2–§6.5 is satisfied by a validator that rejects its own valid input. It is the same structural role
inclusion assertions play in the isolation grid.

### 6.2 Structural rejections pydantic does not catch — B02, B04

**Must prove:** `graph_lint` rejects a recipe that is a valid `Recipe` object but an invalid DAG, and the
rejection identifies **which** rule fired.

```
REQUIRED
  [1] REJECTION — the call raises, and the exception type is the specific one
      the rule contract implies, never a bare Exception
  [2] DISCRIMINATION — the rejection is distinguishable from the other three
      rules' rejections. Read test_graph_lint.py:96,114,126,150: the existing
      bundled test already matches a different substring per rule, and those
      four matches must still hold when you split the test
  [3] PAIRED POSITIVE CONTROL — the same fixture with only this defect
      repaired passes
  [4] CONSTRUCTION PATH — B02 is the only row allowed the model_construct
      back door (test_graph_lint.py:86-95 shows the mechanism, and
      validator.py:9-12 says why rule 1 exists: defense-in-depth for a
      recipe read back from wb.recipes.recipe jsonb). B04 must use plain
      constructors, because a dangling edge needs no back door
  [5] mutant evidence: dropping this rule's check from your own body turns
      exactly this row red, and no other row

DERIVED BAND
  [1..5]              ⇒ HIGH
  missing [5]         ⇒ MEDIUM
  missing [2] or [3]  ⇒ unknown
```

Requirement [2] is what §4.4 is about. Without it, a mutant that removes rule 4 and a mutant that removes
rule 1 produce the same red line, and the mutant map in §7 measures nothing.

### 6.3 `cycle` — B03 (capped at MEDIUM until Q1 is answered)

**Must prove:** a cyclic DAG never reaches the interpreter — for whichever definition of "cycle" the mentor
rules. **You cannot finish this row today, and you must not pick a definition to unblock yourself.**

```
REQUIRED
  [1] REJECTION at the graph_lint gate, not at the interpreter. If the
      interpreter happens to terminate on a cyclic recipe, that masks the
      missing check — score this row at the gate, never on a run result
  [2] PAIRED POSITIVE CONTROL — an acyclic DAG through the same call
  [3] at least three cycle shapes, because they are not one case:
      self-loop, the 2-node cycle, and a cycle reached only through a
      condition node / an edge carrying `when`
  [4] mutant evidence — BLOCKED, see Q1

DERIVED BAND
  [1]+[2]+[3]        ⇒ MEDIUM, and that is the ceiling until Q1 is answered
  [1..4]             ⇒ HIGH
  only the 2-node shape ⇒ LOW
```

The existing suite has exactly one cycle case, the 2-node shape (`test_graph_lint.py:99-115`). An
implementation that only blocks self-loops passes it while letting the 2-node cycle through, and an
implementation that blocks everything passes it too. Requirement [3] is what separates them.

### 6.4 `tool-outside-whitelist` — B05

**Must prove:** a `tool-call` node naming a tool absent from `agent_config.tool_whitelist` is rejected, and
the empty-whitelist case is included.

```
REQUIRED
  [1] REJECTION for a tool-call node whose params name a tool not in the
      whitelist
  [2] PAIRED POSITIVE CONTROL — the same DAG with the tool in the whitelist
  [3] the EMPTY-whitelist case, built through the builder path of §4.3 —
      builder.py:174 and :250 fabricate a tool name when the whitelist is
      empty, so this is the one row where your own package supplies the
      violating fixture. Assert on the recipe the builder actually returns,
      not on a hand-written one
  [4] DISCRIMINATION as in 6.2 [2]
  [5] mutant evidence: M-N "drop the tool-whitelist check" (§7.3) killed here

DERIVED BAND
  [1..5]        ⇒ HIGH
  missing [3]   ⇒ MEDIUM, and say so explicitly — [3] is the live hole
  missing [2]   ⇒ unknown
```

### 6.5 Values with no rule behind them — B06, B07, B08

**These three rows cannot be completed and the reason is a spec gap, not a missing seam.** `when-never-true`,
`entry-unreachable` and `duplicate-node-id` violate none of the four rules in `validator.py:7-19`, and nothing
else in the kit constrains them.

What you can do now, and what counts:

```
REQUIRED (the honest partial cell)
  [1] CONSTRUCTIBILITY — show the axis value is reachable: the recipe builds
      through ordinary constructors and is a valid Recipe object. For B06
      that includes an edge whose `when` can never be true; note that
      interpreter.py:10,79 records `Edge.when` as unevaluated, so this value
      currently changes no behaviour anywhere
  [2] the row is marked with the open question it waits on (Q8), naming the
      decision needed: reject, warn, or accept
  [3] NO assertion about graph_lint's behaviour on it. Writing
      pytest.raises(...) here would invent a rule the spec does not have,
      and an AI-assisted test will happily write it — see 00-METHODOLOGY.md §3

DERIVED BAND
  [1]+[2]        ⇒ stub — an honest recorded state, not coverage
  any assertion about accept/reject before Q8 is answered ⇒ unknown
```

Marking these `stub` and leaving them visible is the point. A row that silently invents rule 5 is worse than
a row that says "nobody has decided".

---

## 7. Mutation evidence

Procedure, unchanged from `00-METHODOLOGY.md` §5: plant the mutant, run the named test, record **which
assertion line went red**, remove it. Red on an unexpected line is itself a finding — write it down.

**All four mutants this guide owns are unanchorable today**, and the reason is uniform: the line to mutate
does not exist. That is not a weak test suite; it is a missing function body. Each row below names the seam
that has to land before the mutant has a home.

| Mutant | Change | Anchorable today? | Seam required | Required by |
|---|---|---|---|---|
| `M-G#3` | `publish` stops reading `scorecard.gate.verdict` | **No** — `publish.py:42-44` is the entire body; there is no `if` to delete | X-1 **and** X-2 (§3) | §7.1 |
| `M-G#4` | `rollback` returns the newest version instead of the previous one | **No** — `publish.py:53-55` is the entire body | X-2 **and** X-3 (§3) | §7.2 |
| `M-N` (a) | `graph_lint` drops the tool-whitelist check | **No** into the body (`validator.py:41-43`); **yes** against the spec text (`validator.py:17-19`) | a `graph_lint` body, split per rule (§4.4) | §6.4, §7.3 |
| `M-N` (b) | `graph_lint` drops the cycle check | **No**, and additionally **undefinable** until Q1 | a `graph_lint` body **and** Q1 | §6.3, §7.3 |
| reject-everything | `graph_lint` raises unconditionally for every recipe | **No** into the body; the shape is real today, since the stub already raises unconditionally | a `graph_lint` body | §6.1, §7.4 |

Consequence, stated plainly rather than papered over: **until X-1/X-2/X-3 exist, every cell that depends on
`publish` or `rollback` caps at MEDIUM by the register's own rule** (§7 of the register: a blocking-zone cell
reaches HIGH only with mutant-kill evidence). Zone 3 is your zone, and it stays capped by your seam.

### 7.1 `M-G#3` — `publish` stops reading the verdict

The branch the mutant would delete is specified in prose at `publish.py:9-16` and exists nowhere in code. The
field is real (`scorecard.py:47-51`), so the mutant is well defined the day the body lands.

Two properties make it killable, and one case is not enough:

- a `FAIL` verdict must block the publish **and** leave the previously served version in place. A test with
  only the `FAIL` case cannot kill the "always block" mutant.
- a `PASS` verdict must publish. A test with only the `PASS` case cannot kill "stops reading the verdict",
  because ignoring the verdict and publishing look identical.

Both cases, in the same cell, or the mutant survives. Note also the ownership line at `publish.py:12-16`: SWE
**wires** the gate by reading `gate.verdict`; a `publish` that re-derives the verdict from
`scorecard.aggregate` recreates the ownership overlap that boundary exists to prevent, and your test should
make that visible by handing `publish` a scorecard whose `verdict` and `aggregate` disagree.

### 7.2 `M-G#4` — `rollback` returns the newest version instead of the previous one

Two traps, both measurable today:

1. **The explicit-`to_version` path hides the mutant.** `rollback(agent_id, tenant, *, to_version)`
   (`publish.py:47`) takes the target version as an argument, so an implementation that honours it is hard to
   mutate. But `publish.py:10-11` also requires an **automatic** rollback when the verdict is `FAIL` — and
   that path must derive "the previous version" itself. That derivation is where the mutant actually lives,
   and today there is no signature for it. The cell must exercise the automatic path, not only the explicit
   one.
2. **Two versions are not enough.** With v1 and v2 only, "the previous version" and "the newest version other
   than the failing one" are the same row, and the mutant survives. Build **at least three** versions, roll
   back from v3, and assert the endpoint serves v1 — never v3.

And per §4.7, assert on the **content** of the restored version, not only on its version number:
`wb.recipe_versions` has no uniqueness constraint, so a version number can identify two different rows.

### 7.3 `M-N` — the `graph_lint` members

Both members mutate a body you have not written yet, which means **you plant them in your own implementation**
once it lands. Score them at the `graph_lint` gate, never on an interpreter run: if the interpreter happens to
terminate on a cyclic recipe or refuses an unlisted tool, the lower layer masks the missing check and the
mutant looks killed when it is not.

- **(a) drop the tool-whitelist check.** The one mutant in this guide that already has a victim recipe
  committed in the repo: `create_recipe_d4(tool_whitelist=[])` returns a `tool-call` node naming `kb_search`
  with an empty whitelist (§4.3, measured). If rule 4 is mutated away, that recipe flows to the interpreter
  and calls a tool nobody granted.
- **(b) drop the cycle check.** **Blocked by Q1.** If "forbidden cycle" means only a subset of cycles, then
  "dropped the check" and "checks the correct subset" are different mutants, and an implementation that blocks
  self-loops only would survive both while passing every existing test.

### 7.4 The reject-everything mutant, and why this grid needs one

The isolation grid uses `M-E` — `search()` returns `[]` — to catch tests whose assertions are true regardless
of the code. This grid needs the mirror image: a `graph_lint` that **raises for every recipe**. It passes all
seven rejection rows and fails only B01.

The register lists `M-E` with three sites, all on the retrieval path. This is a fourth site with the same job
— measuring the test rather than the code — and it is **proposed here, not yet in the register's mutant
list**. The mentor should record it or reject it explicitly; do not treat it as already blessed. Either way
the assertion class it enforces (B01 plus the paired positive control in §6) is mandatory.

---

## 8. Ordering flows

### B-S01 — `S1`, tenant leak via a recycled pooled connection (blocking zones 1 and 2)

**Must prove:** request A (tenant X) returning its connection to the pool cannot let request B (tenant Y) see
X's setting or X's rows.

Buildable today, with no product change:

- two **sequential** requests — you do not need concurrency to prove this;
- `min_size=1` so the pool has exactly one connection to hand back. Note the shipped values:
  `_db.py:59` builds the app pool `min_size=1, max_size=8` and `_db.py:46` the admin pool
  `min_size=1, max_size=4`, and **neither passes `reset=`**, so `RESET ALL` never runs on check-in (register
  H17). That is precisely what makes the mutant `SET LOCAL` → `SET` leak into one specific tenant;
- an `httpx` ASGITransport client against `create_app()` — plus your own test-mounted route, because the kit
  ships none (§4.8);
- a third case where an exception is raised inside `call_next`, since that is the path where the reset is
  least certain. `middleware.py:84-85` resets the ContextVar in a `finally`, but the connection itself is
  returned by the `async with pool.connection()` block opened at `:75`.

The repo has **no barrier precedent**: `asyncio.Event` — 0 occurrences, advisory locks — 0. You are building
the first one. Give it an `asyncio.timeout` (register CP-2.6): a hung barrier test in GATE-3 week is a
schedule event, not a puzzle.

> ⚠️ **H21, unresolved before you start.** `tenant_context_middleware` holds connection #1 for the whole
> request — `pool.connection()` at `middleware.py:75` wraps the `call_next` at `:83` — while anything
> request-scoped that calls `get_pool()` again borrows connection #2 from the same `max_size=8` pool. At 8
> concurrent requests that deadlocks, and a **concurrent** construction of this flow may hang instead of
> failing. The sequential construction above avoids it. **Probe the deadlock rather than designing around it
> silently** — that probe is row B-P02 (§11), and if it is real it is a finding worth its own report.

### B-S02 — `S2`: this is not a test gap, it is an architecture hole

The flow: `agent_config.instructions` is edited between the eval run and the publish call, so v2 ships on
v1's passing scorecard.

**It cannot be written as a test, and the reason is structural: `Scorecard` carries no pointer to the recipe
version it was computed against.** Its fields are `agent_id`, `golden_set_ref`, `results`, `aggregate`, `gate`
(`scorecard.py:61-65`). There is no `recipe_version` and no `recipe_hash`. So "this scorecard belongs to that
recipe" is not expressible, and a test asserting the mismatch would have to invent the field it is checking.

**This routes to design escalation — register §12 Q3 — not to a test.** Do not build a barrier around a
`publish` double and a `Scorecard` double; that is two fakes choreographing each other, the same defect the
register records for `S4b` (CP-2.4 #5).

What the test becomes once the field exists:

```
GIVEN  a recipe at version v1 and a scorecard whose version pointer is v1,
       gate.verdict == PASS
WHEN   agent_config.instructions is changed (a new frozen Recipe — recipe.py:86
       makes every Recipe immutable, so "editing" means constructing v2)
       and publish is called with the v1 scorecard
THEN   publish refuses, on the ground that the scorecard's version pointer does
       not match the recipe being published — and the refusal is distinguishable
       from a FAIL-verdict refusal
PLUS   a paired positive control: the same publish with a matching pointer
       succeeds
```

Until Q3 is answered, this row is `todo:publish-seam` **and** carries the escalation note. The escalation is
the deliverable, not a test.

### B-S03 — `S3`: also an architecture hole, for a different reason

The flow: `publish` and `rollback` running concurrently — which version ends up live.

**The question cannot even be stated in schema terms, because `wb.recipes` has no column that expresses
"live".** The closest thing is `status TEXT NOT NULL DEFAULT 'draft'` (`schema.py:34`), which has no `CHECK`
constraint, no consumer, and is self-labelled *"spec-only for now"* (`schema.py:10-11`). `UNIQUE (agent_id,
tenant, version)` (`schema.py:36`) prevents duplicate version numbers and nothing else: two rows for the same
`(agent_id, tenant)` can both say `published`, and the state "no version is live" is representable without
anyone noticing. There is also no endpoint table anywhere in the five schemas, although `publish.py:19`
requires *"flip the named endpoint"*.

**This routes to design escalation — register §12 Q4** — which also asks the part that decides the test's
shape: is "at most one live version" enforced by a partial unique index or by an advisory lock? Those two
answers need different tests, and a test written for one grades the other wrongly.

What the test becomes once the answer exists:

```
GIVEN  v1 live, v2 publishable, and whatever construct expresses "live"
WHEN   publish(v2) and rollback(to_version=1) are released from one barrier
       into the same window
THEN   exactly one version is live afterwards — asserted by reading the live
       marker, not by reading a return value
AND    the losing operation fails loudly rather than silently no-op'ing
AND    the terminal state is one of the two intended ones, never "nothing live"
```

If the answer is an advisory lock, the test must show the second caller **waits** rather than proceeding: the
repo has 0 advisory locks today, so that is new construction too.

---

## 9. Things that never count as evidence for a cell in this guide

- `pytest.raises(NotImplementedError)` — proves the seam is absent, not that the rule works. Both `publish`
  and `rollback` currently have no test at all, and adding this one would be worse than nothing: it goes red
  the day you implement the function, so somebody deletes it, and the spot ends up with no test.
- **`xfail` or `skip` in any form.** In this quadrant that is not a general caution, it is the local failure
  mode: `test_graph_lint.py` returns `0 failed` for a correct implementation, an empty implementation, and
  today's stub alike (§4.2, measured). Do not extend that pattern into your rows.
- **An assertion inside an `if` that tests the thing being asserted.** `test_wiring_d6.py:139`
  (`if len(trace_writer.events) > 0:`) and `:179` (`if len(kb_output) > 0:`) both do this. The comment above
  the first one says *"Verify trace emission if supported by current engine version"* — but it checks no
  version, it checks the very output it is about to assert on. Consequences, measured: an engine that emits no
  event and an engine that emits the right 4 events give the same green; and at `:179`, if the KB double
  returns `[]` — which is exactly mutant `M-E` — the chunk-id assertion at `:180` is skipped, so **`M-E`
  survives at that site**. This is the register's H2 in a second form: not an always-true assertion, but an
  assertion that never runs.
- **A recipe fixture produced by `create_recipe_d4` / `create_recipe_d6` used as a "valid recipe".**
  `builder.py:174` and `:250` auto-generate a `tool-call` node whose tool is absent from an empty
  `tool_whitelist` (§4.3, measured). That recipe violates rule 4. It is a fine fixture for B05 and a wrong one
  for B01.
- **A rejection assertion with no paired positive control** (§6). It is satisfied by a `graph_lint` that
  rejects everything — including the shape it is supposed to accept.
- **`pytest.raises(Exception)`, or matching on no message at all.** Today's stub raises
  `NotImplementedError`; a bare `Exception` catch is green against the stub, so the test would pass before the
  feature exists.
- **A cell whose axis value never enters the test's causal path** (register CP-2.4 #4). `tools/xcheck_cell_ids.py`
  checks id parity only, so a cell id sitting in the docstring of an unrelated test passes every automated
  check. A B03 test that constructs an acyclic DAG is `unknown`, not LOW.
- **`test_builder.py` / `test_wiring_d3` / `test_wiring_d4` / `test_wiring_d7` counted as recipe-lifecycle
  coverage.** `build_agent_config` — 10 lines with no branch (`builder.py:24-34`) — is asserted by four
  near-identical cases (`test_builder.py:23-32`, `test_wiring_d3.py:19-28`, `test_wiring_d4.py:19-28`,
  `test_wiring_d7.py:58-76`), while `publish` and `rollback` have none. Case count is not coverage.

---

## 10. Open questions blocking parts of this guide

Do not guess these. They change what a correct test asserts. Ids follow the quadrant deep-dive
(`round2-deepdive-2-recipe.md` §6.2); the register mapping is named where one exists.

| id | Question | Which rows it blocks |
|---|---|---|
| **Q1** | **Which cycles are forbidden?** Does "no forbidden cycle" mean every cycle, or a named subset — and if a subset, which? Is a self-loop in it? What about a cycle reachable only through a `condition` node or an edge carrying `when`? | **B03** entirely, and mutant `M-N` (b) in §7.3 |
| **Q2** | Is `publish_state` the state of the **endpoint** or of the **recipe under test**? | the classification of the 7 `na:` cells (§2) — 7 cells move to `todo:publish-seam` under the endpoint reading |
| **Q5** | Where do `publish` / `rollback` get a connection: a fifth protocol in `studio_contracts`, or a changed signature? | **B-P01**, and the whole of §3's X-2 |
| **Q6** | Is `rollback(agent_id, tenant: str, …)` (`publish.py:47`) correct, or must it be `tenant_id: UUID` like every other contract (`recipe.py:89`, `tenant_wall.py:55`)? And must `wb.recipes.tenant TEXT` become `tenant_id UUID`? | **B-P01**; a `yes` is a breaking DDL change and needs the INV-5 mini-RFC |
| **Q7** | Must `wb.*` carry RLS at all? Recipes hold `agent_config.instructions` and `kb_binding.scope` — tenant data — and `kb.chunks` is currently the only table in the kit with a policy | **B-P01**, and the assertion set of **B-P02** |
| **Q8** | **What does a correct `graph_lint` do with `when-never-true`, `entry-unreachable`, and `duplicate-node-id`?** None of the four rules covers them, and nothing else in the kit constrains them (§5) | **B06**, **B07**, **B08** |
| **Q10** | How are the two `test_graph_lint.py` cases resolved before Day 30 — `strict=True`, drop the marker on the stub-pinning case, or split into four per-rule cases? Note the cheap wrong fix: deleting `xfail` from the stub case makes it genuinely green and thereby **locks `NotImplementedError` in place**, blocking the implementation | §5.1 row L2-01 |
| **Q11** | The cell `valid × v1-live × post-consent-purge` — a live recipe whose `kb_binding.kb_id` points at purged data, so citations point at deleted rows — belongs to this grid or to flow `S4b` in the isolation guide? It is the one place `kb_state` is not inert here | nothing in §5 today; it is a cell with **no home**, which is why it is listed |
| register §12 **Q3** | Does `Scorecard` get a `recipe_version` / `recipe_hash`? | **B-S02** — without it, S2 is an architecture hole, not a test gap |
| register §12 **Q4** | Is "one live version" enforced by a partial unique index or an advisory lock, and where does "live" live? | **B-S03** |

**Q1 is the biggest, and it is unresolvable from the sources — do not try.** Three sources say three things,
and one contradicts itself inside a single sentence:

| Source | What it says |
|---|---|
| `umbrella-contract.md:112` | *"không chu trình cấm"* — grammatically ambiguous in Vietnamese: "no forbidden cycle" (some cycles allowed) or "cycles are forbidden" (none allowed) |
| `recipe.py:82-83` | copies the same ambiguous phrase verbatim, adding no information |
| `validator.py:13-14` | *"**no forbidden cycle** — the DAG … must not contain **a cycle**"* — the rule title implies a permitted class, the sentence body forbids all of them. **Self-contradictory in one sentence** |

The contract also contains two signals that conditional branching was contemplated — `NodeType.CONDITION`
(`nodes.py:21`) and `Edge.when` (`recipe.py:45`) — while `interpreter.py:10,79` records `Edge.when` as
unevaluated. That is evidence on both sides, which is exactly why this is a mentor decision. Raise it; leave
B03 at MEDIUM until it comes back.

---

## 11. Surface-5 rows you now own — the pool and the connection

Surface 5 (wired infrastructure) was owned by "nobody" in the register §2 and was therefore never going to be
built. CP-2.8 splits it: the fence-infra rows go to DE, **the pool and connection rows come to you**, together
with flow `S1` (`B-S01`, §8).

### B-P01 — `publish` writes through the request's own connection (`todo:publish-seam`)

**Must prove:** the write `publish` performs happens on the **same** connection that already ran
`SET LOCAL app.tenant_id` for this request — not on a connection `studio_workbench` opened for itself.

This row exists because the cheapest way to implement `publish` is the one that destroys the fence (§4.5). It
is not a hypothetical: `get_request_connection()` is defined at `middleware.py:31` and called **nowhere** in
`packages`, `apps`, or `tests` (register H15), so the mechanism that would make this correct has no user yet.

```
REQUIRED
  [1] POOL PATH — the write is observed on the request-scoped connection; a
      second connection opened inside studio_workbench must make this cell FAIL
  [2] the fence is exercised, not merely present: with app.tenant_id set to
      tenant Y, a publish for tenant X's agent must not write X's row
  [3] PAIRED POSITIVE CONTROL — the same publish with the matching tenant set
      succeeds and the row is readable (the empty-expected rule,
      00-METHODOLOGY.md §7.1: "no row was written" is also true of a broken
      fixture, an unapplied DDL, and a typo)
  [4] the row is read back through the app pool, not the admin pool — reading
      through admin_pool bypasses the policy and measures nothing
  [5] mutant evidence: whichever construct answers Q7 (policy on wb.*) can be
      dropped, and this cell must go red

DERIVED BAND
  [1..5]              ⇒ HIGH
  missing [5]         ⇒ MEDIUM
  missing [1] or [3]  ⇒ unknown
```

Blocked by **Q5** (where the connection comes from), **Q6** (`tenant TEXT` vs `tenant_id UUID` — a policy
comparing a UUID against a TEXT column will not run) and **Q7** (whether `wb.*` gets a policy at all). Owner:
**SWE**, ETA **Day 20**, same seam as §3.

### B-P02 — the H21 pool-exhaustion probe

**Must prove:** what actually happens when the middleware holds one connection per request and request-scoped
code borrows a second from the same `max_size=8` pool (`_db.py:59`).

This row is a **probe, not a guard**: its job is to replace an argument with a measurement, because the answer
changes how `B-S01` may be built and whether the deadlock is real (register H21, unresolved).

```
REQUIRED
  [1] a concurrency level derived from the pool's real max_size, read from
      _db.py rather than hardcoded — the number is the point of the test
  [2] asyncio.timeout on every task, and a recorded outcome: completed,
      timed out, or raised (register CP-2.6 — an acceptance suite that hangs
      in GATE-3 week is a schedule event)
  [3] the measured result written down whichever way it comes out. "No
      deadlock at 8" is a real finding and closes H21; a deadlock is a finding
      that needs its own report and a design decision, not a workaround
  [4] the test must not silently lower the concurrency until it passes

DERIVED BAND
  [1]+[2]+[3]   ⇒ HIGH — for a probe, a recorded honest measurement IS the
                  evidence
  missing [2]   ⇒ unknown (a hanging test produces no result at all)
  [4] violated  ⇒ unknown, and it is the most dangerous cell in this guide to
                  get wrong, because it would report "no deadlock" from a
                  configuration that could not have shown one
```

This row needs Postgres. Read `01-FOUNDATION.md` §1 and §2 first: DB tests skip silently when
`STUDIO_DATABASE_URL_ADMIN` is unset (`conftest.py:48-52`), `make test-int` starts the database and exports no
DSN (register H5), and the guard in `conftest.py:55-70` is `or`-joined, so a wrong DSN can still get through
and `TRUNCATE … CASCADE` a real database. A skipped run is not a passing run.

---

## 12. One note about the ids in this guide

The grid rows `B01`–`B08` are reconciled automatically: `tools/xcheck_cell_ids.py` matches a grid letter plus
two digits, so it will notice if one of them exists in one tier and not the other.

The five ids introduced by this guide — `B-S01`, `B-S02`, `B-S03`, `B-P01`, `B-P02` — **do not match that
pattern**, so their parity is checked by a human or not at all. Carry them verbatim in your test docstrings
anyway; that is what makes the manual reconciliation possible.
