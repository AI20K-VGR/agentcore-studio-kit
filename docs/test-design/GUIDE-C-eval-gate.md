# GUIDE C — Eval gate and scorer judgement (Grids C and F)

**Owner: AIE-2.** Read `00-METHODOLOGY.md` and `01-FOUNDATION.md` first. You do not need the other guides.

You own two grids and they are in opposite states.

| Grid | Subject | Blocking | Buildable today |
|---|---|---|---|
| **C — EVAL GATE** | `compute_scorecard` — the aggregate gate that decides `gate.verdict` | **yes** (blocking zone 3) | **0 of 9 cells** |
| **F — SCORER JUDGEMENT** | `score_case` — the per-case scoring rule | no | **7 of 7 cells** |

Grid C is a specification written ahead of the code. Grid F is a specification of code that runs today.
Both are graded. Do not treat the second as a substitute for the first.

> All `file:line` citations are against the pinned baseline named in `02-MATRIX.md` §6
> (kit `8a420e7`, `packages/evalhub` `123e85c4`, `packages/contracts` `3d7004b2`). Verified by reading
> those files at those SHAs. Measured numbers in this guide come from
> `.venv/bin/python -m pytest packages/evalhub/tests -q -p no:cacheprovider -rsxX`, which on the pinned
> tree gives `38 passed, 1 skipped, 1 xfailed, 1 xpassed in 0.22s`.

---

## 1. Grid C has ZERO buildable rows today, and that is the honest number

Every one of Grid C's 9 cells is marked `todo:compute-scorecard`. The reason is one line:

```python
# packages/evalhub/src/studio_evalhub/compute.py:30
    raise NotImplementedError("compute_scorecard — spec AIE-2, not yet implemented")
```

`compute_scorecard` is the only function in the repo that can produce a `gate.verdict`
(`compute.py:19-25` is its signature; `verdict` is a field of its **return** type,
`packages/contracts/src/studio_contracts/scorecard.py:51`). No body, no verdict, no cells.

It is worse than one missing function, and you should know the full shape before you start:

| What Grid C needs | State on the pinned tree | Anchor |
|---|---|---|
| `compute_scorecard` body | `NotImplementedError` | `compute.py:30` |
| an aggregate computation (`success_rate`, `citation_accuracy` over a run) | **does not exist in any `.py` file.** `grep success_rate` over `packages`, `apps`, `scripts` returns 2 docstrings, 1 contract field, and 2 tests that build the value as a **constant** | `compute.py:4,26`; `contracts/.../scorecard.py:36`; `test_scorecard_roundtrip.py:38`; `contracts/tests/test_roundtrip.py:105` |
| a threshold comparison (`>=` or `>`) anywhere | **does not exist.** Every `threshold` hit in the repo is a declared value, a contract field, a stub parameter, a docstring, or a test constant | `compute.py:23-24` (parameters only) |
| `EvalHarness.run` → `Scorecard` | `NotImplementedError` | `harness.py:209` |
| `LLMJudge.judge` | `NotImplementedError` | `judge.py:35` |
| a consumer of `gate.verdict` (`publish`) | `NotImplementedError`, and it is SWE's file | `packages/workbench/src/studio_workbench/publish.py:42-44` |

So `gate.verdict` today is a string with **no producer and no consumer**. The only places in the repo
that assign it a value are a test fixture (`test_scorecard_roundtrip.py:41`,
`packages/contracts/tests/test_roundtrip.py:108`) and one assertion inside a test that cannot fail
(`test_eval_gate.py:40` — see §4.3).

**Read the zero correctly.** Grid C emitting 0 rows does not mean the gate is 0% tested; it means the
gate does not exist yet, and the grid is saying so out loud instead of quietly. Your quadrant has 38
green tests. None of them touches blocking zone 3.

### 1.1 What is NOT a reason for the zero

`compute_scorecard` being a stub does **not** make any cell `na:`. Per register §0 the acceptance horizon
is GATE-3 / Day 30, so a cell pointing at code that does not exist is normal. All 9 cells are
`todo:compute-scorecard` — they must be filled, they just cannot run today.

| Seam id | Cells | What has to exist | Owner | ETA |
|---|---|---|---|---|
| `todo:compute-scorecard` | 9 (C01–C09) | a `compute_scorecard` body: aggregate over `results`, compare both aggregates to both thresholds, set `verdict` | **AIE-2 (you)** | **Day 20** |

Day-20 is not decoration. Per register CP-2.3, a `todo:` in a blocking zone that has not landed by
Day 20 escalates to a sign-or-descope decision; it does not sit quietly until Day 30. At Day 30 the
judgement is: seam landed and cell filled ⇒ covered. Seam landed and cell still `todo:` ⇒ **blocks**.
Seam formally descoped through the INV-7 ladder with a recorded `defer:<decision-id>` ⇒ does not block.
Seam neither landed nor descoped ⇒ blocks, and what is blocked is the **feature**, not the test.

---

## 2. The one row that ships now: the ratchet, `C-R01`

An all-`todo:` grid has a failure mode of its own. Nine cells marked "cannot run yet" are invisible in a
green suite, and the day `compute_scorecard` gets a body, nothing anywhere changes colour to tell anyone
those nine cells are now buildable. They would stay `todo:` by inertia until Day 30, when they block.

`C-R01` exists to prevent exactly that. **Its only job is to go red on the day the seam lands.**

```
C-R01   RATCHET — compute_scorecard is still a stub

MUST PROVE
  [1] calling compute_scorecard with a well-formed argument list raises
      NotImplementedError, i.e. C01..C09 are still unbuildable
  [2] the test carries the id C-R01 and the list of cell ids it unlocks
      (C01..C09) in its docstring, so the red test tells the reader what to do
  [3] the marker rule below

MUST NOT
  [4] pytest.mark.xfail(..., strict=False) in any form
  [5] a docstring that describes it as a behaviour test of compute_scorecard

DERIVED BAND
  [1]+[2]+[3]        ⇒ the row counts as present (it is not a coverage cell and
                       has no band — it is a schedule device)
  strict=False       ⇒ unknown, and blocks: the row cannot fire, so it is
                       indistinguishable from not having written it
```

### 2.1 Why this is the exact opposite of the banned pattern

`00-METHODOLOGY.md` §3 bans `pytest.raises(NotImplementedError)` **used as a behaviour test**: it passes
precisely while the feature is missing, so when the feature arrives somebody deletes the test and that
spot ends up with no test at all.

`C-R01` uses the same assertion for the opposite purpose. It is not claiming anything about how the gate
behaves. It is claiming *the gate does not exist yet*, and **failing on implementation is the entire
point** — the red is the notification. The difference is not in the code, it is in what the red means and
in whether the test is allowed to be silent. So the rules are inverted: the assertion is mandatory, the
docstring must say it is a ratchet, and any marker that stops it going red disqualifies it.

### 2.2 Two admissible constructions, and one that is red today

Per register CP-1 the row must be a **plain assertion** or **`xfail(strict=True)`**, never `strict=False`.
Those two are not interchangeable — they assert different things and they fire at different moments.
Measured (five variants, run against a two-function stand-in, `pytest 9.1.1` on the kit's own `.venv`):

| Construction | While the seam is a stub | The day the seam lands |
|---|---|---|
| **(A)** plain assertion — `with pytest.raises(NotImplementedError): compute_scorecard(...)`, no marker | `PASSED` | **RED** — `Failed: DID NOT RAISE NotImplementedError` |
| **(B)** `@xfail(strict=True)` on a test asserting the **future** contract — `assert scorecard.gate.verdict == "FAIL"` | `XFAIL` (suite green) | **RED** — `[XPASS(strict)]` |
| **(C)** `@xfail(strict=True)` on the raises-assertion of (A) | **RED today** — `[XPASS(strict)]` | green |
| **(D)** `@xfail(strict=False)` on either | green | green — *cannot fire in either direction* |

Use **(A)**. It is the shape that says "the seam is absent" and fires when that stops being true.

**(B)** is also admissible and is worth adding later as a second ratchet on the *contract* rather than on
the *absence* — but note the trap it hides: (B) only fires when the seam lands **and is correct**. A
`compute_scorecard` that returns a constant `"PASS"` leaves (B) as XFAIL, i.e. green. So (B) alone is not
a substitute for the real C03/C06/C07/C08/C09 cells.

**(C)** is the mistake to expect, because "strict is stricter" is a reasonable-sounding rule of thumb and
it is wrong here: `strict=True` turns an unexpected **pass** into a failure, and (A)'s assertion passes
today. If you write (C) you will get a red suite immediately and conclude the guide is broken. It is not
— you put the marker on the wrong shape.

**(D)** is the pattern already in the repo, and §5.3 is about what it costs.

### 2.3 `C-R01` collides with an existing pin-test

`packages/evalhub/tests/test_eval_gate.py:44-75` — `test_harness_judge_compute_not_implemented` — already
makes assertion **[1]** three times (`:53-57`, `:59-75`), for all three seams. It is a `KHÓA` pin
(`:45`). Two differences matter: it carries `xfail(strict=False)` (`:43`), so it is construction (D) and
cannot fire; and its docstring claims a property it does not have (§5.3).

**Pinned-by for `C-R01`:** `test_eval_gate.py::test_harness_judge_compute_not_implemented` (`:43-49`).
When the seam lands, that marker and this row change **in the same commit**, with a reference to the
decision. Per `00-METHODOLOGY.md` §7.2 a pin-test asserts a *decision*, not a behaviour — and the
decision recorded at `test_eval_gate.py:8-12` is the kit owner's, not yours: *"`strict=False` means an
unexpected pass … is reported as XPASS, not a failure"*, chosen deliberately so the P8 regression gate is
not blocked. **Do not edit that marker on your own authority.** Whether the acceptance set may require
`strict=True` there is an open question (§11, M6). `C-R01` is a *new* test that you own, which is why it
can be written correctly today without touching anybody's policy.

---

## 3. Grid C — the 9 cells and what the axes actually are

| Axis | Values | What the value means |
|---|---|---|
| `rel_success` | `above` · **`exactly-at`** · `below` | where `aggregate.success_rate` sits relative to `threshold_success` |
| `rel_citation` | `above` · **`exactly-at`** · `below` | where `aggregate.citation_accuracy` sits relative to `threshold_citation_accuracy` |

3 × 3 = **9 cells**, all `todo:compute-scorecard`. `verdict` is **not** an axis — it is the **oracle
column**, the expected result. This was register decision D-17, and the reason is worth carrying: with
`verdict` as an axis, the cell `(score above threshold, verdict = FAIL)` is impossible by definition, and
the only way to fill it is to hand-build `Gate(verdict="FAIL")` — a test that is green regardless of the
code. A wrongly-chosen axis actively manufactures the defect this whole apparatus exists to catch.

There is **no `provider` axis and no `kb_state` axis** in Grid C, and this is not an oversight.
`compute_scorecard(agent_id, golden_set_ref, results, threshold_success, threshold_citation_accuracy)`
(`compute.py:19-25`) is a pure function of `results` plus two floats. Neither shared axis reaches it.
Per register CP-2.7 both were stripped. If you see a cell label mentioning a provider, the cell is
mislabelled — see §4.4 on label laundering.

### 3.1 The oracle column, derived from D-19

Under D-19 as it now stands (§4.1): **AND** over both thresholds, operator **`>=`**, at the **aggregate**
level. That fixes every oracle value mechanically:

| id | `rel_success` | `rel_citation` | oracle `verdict` | what the cell is for |
|---|---|---|---|---|
| **C01** | above | above | `PASS` | the baseline. Without it, every FAIL cell below is satisfiable by a gate that always FAILs |
| **C02** | above | exactly-at | `PASS` | boundary on the citation threshold only. `>=` vs `>` |
| **C03** | above | below | `FAIL` | **AND vs OR.** Under OR this cell is `PASS` |
| **C04** | exactly-at | above | `PASS` | boundary on the success threshold only. `>=` vs `>` |
| **C05** | exactly-at | exactly-at | `PASS` | **the double-boundary cell.** The only cell where both `M-G` mutants are visible at once |
| **C06** | exactly-at | below | `FAIL` | AND vs OR, with one side on the boundary |
| **C07** | below | above | `FAIL` | **AND vs OR.** This is money-shot step 7: citations fine, answers bad |
| **C08** | below | exactly-at | `FAIL` | AND vs OR, with one side on the boundary |
| **C09** | below | below | `FAIL` | the other baseline. Without it, every PASS cell is satisfiable by a gate that always PASSes |

Four cells — **C03, C06, C07, C08** — are the ones that distinguish AND from OR. The grid Grid C replaced
had no cell that could tell the two apart, which meant the register's own AND/OR ruling had nothing
watching it. Keep that in mind when you are tempted to treat them as near-duplicates of each other.

> **The id ordering is fixed here and must not be renumbered.** the generator emits Grid C as
> `exhaustive 9 · na 0 · todo 9 · real 0 · rows 0` with **no id table**, because a generator that emits
> zero rows has no rows to name. The row-major mapping above (`rel_success` outer, `rel_citation` inner,
> values in register §3 order) is this guide's, it is mirrored id-for-id in tier B, and
> `tools/xcheck_cell_ids.py` reconciles the two. Changing the mapping later silently re-labels nine
> graded cells.

### 3.2 The trap that would make all 9 cells worthless

Both axes are **threshold-relative**, and both thresholds are **free inputs** of the function
(`compute.py:23-24`). The escalation review (`round3-escalation-review.md` §2c) states the consequence
plainly: all 9 cells are satisfiable against **one dataset** by tuning the two thresholds. That is
legitimate boundary-testing of a pure function — and it means the grid can degrade into 1 dataset + 9
threshold pairs, i.e. 9 comparator cases dressed up as 9 system states.

Worse is the special case for the `exactly-at` cells. Copy the run's computed float into the threshold
parameter and equality is true by construction, `0.5549999… == 0.5549999…`, the float question (§11 Q1)
evaporates, nothing about boundary semantics gets measured, and the most expensive cell in the set becomes
the cheapest. **This is forbidden.** Per review §3.2:

```
FORBIDDEN
  threshold := the value the run just computed
  threshold nudged after the fact to make the cell come out the intended way
  round(...) inserted into the aggregate to make an equality hold

REQUIRED for every exactly-at cell (C02, C04, C05, C08)
  [1] the threshold is a ROUND DECIMAL, fixed and written down BEFORE the
      dataset is constructed
  [2] the case count is engineered so the aggregate lands on it exactly
      (11/20 = 0.55), and the test ASSERTS that equality on the aggregate
  [3] kill evidence for M-G#1 (>= becomes >): this cell must go red.
      Applies to C02, C04, C05 only — see the note below on C08
  [4] the assertion names the threshold literal, not a variable copied from
      the result

DERIVED BAND
  [1..4]           ⇒ HIGH
  missing [3]      ⇒ MEDIUM (register §7: a blocking-zone cell without mutant
                    evidence caps at MEDIUM)
  missing [1]/[2]  ⇒ unknown, NOT low — the cell measured nothing
```

> **C08 is the exception, and it is a real asymmetry rather than a drafting slip.** C08 is
> `(rel_success = below, rel_citation = exactly-at)`. Under AND the success side already decides FAIL, so
> `>=` → `>` leaves the verdict at FAIL and **C08 cannot kill `M-G#1`** — measured: `AND >=` gives FAIL,
> `AND >` gives FAIL. Its boundary is only observable in the **aggregate** assertion, which is why `[2]`
> requires asserting the equality on `aggregate.citation_accuracy` itself and not just on the verdict.
> C08's mutant is the `and` → `or` mutant instead (§7.1). The same masking does **not** happen to C02, C04
> or C05: measured, all three go PASS under `>=` and FAIL under `>`.

**Requirement [3] is the fraud detector, and that is its purpose.** The dishonest construction cannot kill
`M-G#1`: if the threshold *is* the computed value then under both `>=` and `>` … no. Be precise about
this, because it is the mechanism you are relying on. Under the copied-threshold construction the two
sides are bit-identical, so `>=` says PASS and `>` says FAIL — the cell **does** change. What it cannot do
is change **for the right reason**: it flips on an equality that the test itself manufactured one line
earlier, so it also flips for a dataset that should have been nowhere near the boundary, and it flips
identically no matter what the golden set contains. The honest construction flips only because 11 of 20
cases succeeded against a threshold of `0.55` written down beforehand. Both cells report "M-G#1 killed";
only one of them is telling you something about the gate.

So the mechanical rule tier B grades against is **[1] + [2] + [4] together**: a round-decimal threshold
literal, appearing in the test source, fixed before the data. A cell that kills `M-G#1` while reading its
threshold out of the result under test is recorded as **unknown**.

**One measured fact that makes [2] achievable.** The obvious worry is that "engineer the count to land
exactly" is impossible in binary floating point. For the construction this guide mandates it is exact —
measured with CPython 3.14 doubles: `sum([1.0] * 11) / 20 == 0.55` is `True`, and `11 / 20 == 0.55` is
`True`. It stops being exact as soon as the per-case values have mixed denominators: a 20-case set of
per-case accuracies with denominators in 1–5 measured `0.6174999999999999` where the exact value is
`0.6175`. Hence the construction rule in tier B: for the `exactly-at` cells, give every case **exactly one**
expected citation, so per-case `citation_accuracy` is `0.0` or `1.0` and the mean is `k/20`. Q1 is still
open for every golden set that does not obey that rule — which includes the real 30-case set.

---

## 4. Things you must know before writing a single test

These are measured facts about the pinned tree. Each one changes what a correct test looks like.

### 4.1 D-19 as it now stands — read this before you touch `harness.py`

**The ruling:** the gate is **AND** over both thresholds, operator **`>=`**, at the **aggregate** level.
Source: `compute.py:26-29` — *"`gate.verdict` is `"PASS"` when **both meet**
`threshold_success`/`threshold_citation_accuracy`, else `"FAIL"`"*. The word *both* settles AND; the word
*meet* settles `>=`.

**And the part an earlier draft of this guide got backwards.** `harness.py:159` says, in bold:

> *"**`citation_accuracy` là metric riêng, KHÔNG gate `success`**"* — `citation_accuracy` is a separate
> metric, it does NOT gate `success`

That sentence is about the **per-case** field `SmokeResult.success`, and it is **correct as written**.
The `success` it refers to is computed one screen below at `harness.py:169`:

```python
success = (answer.refused is False) and _contains_phrase(answer.answer, case.expected)
```

and the clause immediately after the bold sentence settles it beyond argument (`harness.py:159-160`):
*"trace sai/rỗng ⇒ accuracy 0.0 nhưng vẫn PASS nếu answer đúng"* — the **case** passes.
`compute.py:28-30` rules the **aggregate**. Two levels, composing exactly as the frozen contract lays them
out: per-case `success` and `citation_accuracy` as siblings (`contracts/.../scorecard.py:22-30`), then
`Aggregate` over both (`:33-37`), then a `Gate` over both aggregates (`:40-51`).

**There is no conflict, and `harness.py:159` must NOT be changed.** Register §11 D-19 originally said the
opposite — that the two lines could not both be true and that `harness.py` was the side that had to change.
That instruction is **withdrawn** in register CP-2.1. It is spelled out here because a trainee acting on
the withdrawn version would make `citation_accuracy` gate per-case `success`, which **double-counts every
citation failure**: the case fails *and* the aggregate drops, silently deflating `success_rate`. That is a
semantic change to a frozen contract wearing the costume of a consistency fix.

If you want to do something about `harness.py:159`, the sanctioned change is to **add one sentence** there
pointing at the aggregate gate, so the next reader does not manufacture the same conflict.

There is already a `KHÓA` test standing guard over this, and it is worth knowing which one:
`test_smoke_runner.py:164-175` — `test_citation_accuracy_zero_when_trace_empty_but_success_still_true` —
asserts `citation_accuracy == 0.0` **and** `success is True` on the same result. Make citation gate
per-case success and that test goes red. It is the mechanism that would have caught the withdrawn
instruction, which is a good argument for why cells F05 and F06 are in the set.

### 4.2 No aggregate arithmetic exists yet, so the float hazard is yours to create

Register §11 and §12 Q1 describe the boundary problem as *"`harness.py` computes `sum()/n`"*. On the
pinned tree that is **not accurate**, and the difference matters for where you look:

- `harness.py:171-173` computes a **per-case** ratio, `len(expected & set(retrieved)) / len(expected)`,
  with a denominator of 1–5 in practice (`cli.py` cases carry 1 chunk each; `test_smoke_runner.py:131-152`
  has a 2-chunk case).
- The **mean over cases** — `aggregate.success_rate` and `aggregate.citation_accuracy` — exists in **no
  `.py` file at all**. You are about to write it.

So the `0.555` → `0.5549999999999999` hazard is not a bug you inherit; it is a bug you can choose not to
create, and the cells that would have been destroyed by it are C02, C04, C05 and C08. Q1 (§11) is still
open and still blocks those four cells for any golden set that does not use the one-citation-per-case
construction of §3.2.

### 4.3 `test_eval_gate.py`'s two cases cannot go red in either direction

`packages/evalhub/tests/test_eval_gate.py:28` and `:43` both carry
`@pytest.mark.xfail(reason="spec AIE-2 fills harness/judge/compute", strict=False)`. Under `strict=False`
pytest has two outcomes and **neither is red**: the test passes ⇒ `XPASS`; the test fails ⇒ `XFAIL`. On the
pinned tree, measured: `test_gate_blocks_on_fail` is `XFAIL`, `test_harness_judge_compute_not_implemented`
is `XPASS`. **No input exists that turns either red.** These are two tests carrying zero bits of signal.

Two consequences you have to plan around:

1. **Blocking zone 3 is currently guarded by nothing.** Somebody wanting a green suite could add
   `return Scorecard(..., gate=Gate(threshold=..., verdict="PASS"))` — a constant `PASS` regardless of
   `results` — and the suite would not change. `test_gate_blocks_on_fail` (`:29-40`) is written to catch
   precisely that (`assert scorecard.gate.verdict == "FAIL"`, `:40`) and cannot.
2. **The docstring at `:45-49` states something untrue, and you will read it before you read this guide.**
   It claims: *"A red-teamer or reviewer 'making this green' by stubbing a fake return value (instead of
   implementing the real seam) would be caught by this assertion flipping from raise-NotImplementedError
   to no-raise."* Measured in `round2-deepdive-3-eval-gate.md` §5 L1: implementing `compute_scorecard`
   flips the test `XPASS` → `XFAIL` and the whole-workspace summary does not change by one character.
   Nobody is caught. Do not build a plan on that sentence.

A third, smaller thing in the same file: `test_gate_blocks_on_fail:38` calls
`harness.run(agent_id="agent-bad-instructions", ...)`. `"agent-bad-instructions"` is **a label string** —
no mechanism in the repo makes that agent actually bad. When you implement `run`, this test will fail
because the agent is not found, not because a verdict was wrong. How to construct a genuinely bad version
is open question M8 (§11), and it blocks the FAIL half of Grid C from ever being an end-to-end
demonstration — which is why C03/C06/C07/C08/C09 are specified at the `compute_scorecard` level, where
`results` are inputs you control.

### 4.4 `test_determinism.py` does not re-run anything

Answer first: **it does not re-run. It calls twice inside one process.** `test_determinism.py:134-139`
constructs `EvalHarness().run_smoke(...)` twice in the same test body — same interpreter, same
`PYTHONHASHSEED`, same memory.

What it genuinely proves, and this part should not be talked down:

1. `run_smoke` keeps no state between calls, and golden order is preserved (`:141-142`).
2. The score is invariant to trace metadata (`:150-197`) — the only real source of run-to-run variation is
   `run_id = uuid4()` and `ts = now(UTC)`, and the assertion is placed on `citations_from_trace`, the one
   function that sees `TraceEvent`, rather than on `score_case`, where it would be a tautology because
   `score_case` never receives `events`. That reasoning is written in the docstring at `:151` and it is
   correct.
3. The score is invariant to event order (`:205-222`).
4. It has a **real negative control**: `test_equality_actually_discriminates` (`:230-253`) perturbs every
   field of `SmokeResult` one at a time and requires `!=`, so the three `==` assertions above it are proven
   to have teeth.

That is a good file. It locks determinism at the `SmokeResult` level and it locks it honestly. What it does
**not** watch is everything Grid C is about:

| What DoD #34 asks for | Present? | Missing where |
|---|---|---|
| a re-run **across processes** giving the same numbers | no | no subprocess, no second `pytest` invocation, no varied `PYTHONHASHSEED` |
| determinism of `aggregate` and `verdict` | no | the code does not exist (`compute.py:30`); the whole file stops at `SmokeResult` |
| determinism when the **case order** in the golden set changes | no | only **event** order is reversed (`:205`) |
| determinism when trace is read from Postgres instead of memory | no | `:212` says so itself: Postgres does not guarantee the same order |
| determinism of the rendered scorecard | no | deliberate (`:19-23`), and `_render` has 0 tests (§7.2) |

**A real re-run cell requires all four of these**, and it is the cell that catches the failure mode the
existing file cannot see:

```
REQUIRED for a re-run cell over aggregate + verdict
  [1] two runs in two SEPARATE processes (subprocess, or a re-invoked pytest),
      not two calls in one
  [2] PYTHONHASHSEED differing between the two — that is the variable being
      controlled for, and the default is randomised
  [3] the compared value is aggregate.success_rate, aggregate.citation_accuracy
      AND gate.verdict — not SmokeResult
  [4] a negative control in the same style as test_determinism.py:230-253:
      perturb one input, require the compared value to change
  [5] the case order in the golden set permuted between the two runs

DERIVED BAND
  [1..5]         ⇒ HIGH
  missing [4]    ⇒ MEDIUM
  missing [1]/[2]⇒ unknown — that is the existing file's coverage, not a new cell
```

The concrete bug this catches: an implementation that aggregates by walking `set(results)`, or a `dict`
keyed on `case_id` and read through `.values()`, gets a float summation order that depends on string
hashing. Inside one process, `PYTHONHASHSEED` is fixed, so both calls agree and all four existing tests
stay green. Across two CI processes the sum order changes, the aggregate moves in the last bit, and if the
score sits **exactly at** the threshold the **verdict flips between two CI runs**. That is precisely the
"CI flaky for reasons unrelated to answer quality" that `test_determinism.py` was written to stop — it
stops it at `SmokeResult`, and nobody is watching `aggregate`.

> This re-run cell is **not** one of C01–C09. It is a cross-cutting obligation on all nine, and tier B
> grades it as part of C05 (the double-boundary cell), where a last-bit shift actually changes the verdict.

### 4.5 Axis-label laundering — the check that will not catch you

`tools/xcheck_cell_ids.py` reconciles cell **ids** between tier A and tier B and, with `--tests`, against
your test files. That is **id parity only** (`xcheck_cell_ids.py:48-49`, `:109-119`). A cell id sitting in
the docstring of an unrelated test passes every automated check in the system.

The band rule from register CP-2.4 #4 is therefore: **an axis value not causally exercised by the test's
setup ⇒ the cell is `unknown`.** For Grid C, "causally exercised" has a precise meaning, because the axes
are relations: the cell's `rel_success` and `rel_citation` positions must be produced by the `results` you
built and the threshold literals you fixed, and the assertion must read `verdict` out of the value
`compute_scorecard` returned. A test that hand-builds `Gate(verdict=...)` and asserts on it has laundered
the label — see §10 for what that specific line looks like in the repo today.

---

## 5. What each Grid C cell must prove

Grouped by oracle, because the proof obligation is the same within a group. Every cell in Grid C is in
**blocking zone 3** (*"the eval gate fails to block a bad version"*, register §4). Target band is what a
complete cell reaches, not a promise.

### 5.1 Common to all nine cells

```
REQUIRED (missing any line ⇒ unknown ⇒ blocks)
  [1] the value asserted on is the verdict RETURNED by compute_scorecard.
      Not a hand-built Gate. Not a verdict read from a fixture
  [2] both threshold arguments are ROUND DECIMAL LITERALS written in the test
      source, fixed before the results list was constructed
  [3] the results list is built so that BOTH aggregates land where the cell's
      two axis values say they land — and the test asserts the aggregate
      values too, not only the verdict. Otherwise the cell's axis labels are
      a claim about the dataset that nothing checks
  [4] the results are `studio_contracts.CaseResult` instances (compute.py:22),
      with per-case citation_accuracy values that a real score_case run could
      have produced — see §6 for what those are
```

Requirement **[3]** is the one that separates a Grid C cell from a comparator unit test. The cell is named
after a position of the aggregate; if the test never asserts the aggregate, the name is decoration.

### 5.2 `PASS` cells — C01, C02, C04, C05

**Must prove:** a version that meets both thresholds is allowed through — and that the gate is not simply
returning `PASS` for everything.

```
REQUIRED
  [1..4] of §5.1
  [5] a paired FAIL control: the SAME assertion style, in the same file, on a
      cell from §5.3. A PASS-only test is green against a constant-PASS gate,
      which is the exact defect §4.3 describes as currently unguarded
  [6] for C02, C04, C05 (exactly-at): the §3.2 block in full, including the
      M-G#1 kill

DERIVED BAND
  C01              [1..5]              ⇒ MEDIUM   (no boundary, no mutant)
  C02, C04         [1..6]              ⇒ HIGH
  C05              [1..6] + M-G#2 kill ⇒ HIGH
  missing [5]      ⇒ unknown
  missing [6] on an exactly-at cell ⇒ unknown, NOT medium — the cell's entire
                   subject is the boundary
```

**C05 is the most valuable cell in the grid**, and the reason is mechanical rather than rhetorical: it is
the only cell where **both** comparisons sit on their boundary simultaneously, so it is killed by a `>=` →
`>` mutation of **either** one — where C02 catches only the citation-side mutation and C04 only the
success-side one. It also kills `M-G#2` (inverting `PASS`/`FAIL`), though that is no distinction: `M-G#2`
flips all nine cells, and any single cell kills it. C05 gets both kills from one dataset. It is also the
cell that Q1 (§11) can destroy, and the cell where the §4.4 re-run obligation is graded.

### 5.3 `FAIL` cells — C03, C06, C07, C08, C09

**Must prove:** a version that misses **either** threshold is blocked. This is blocking zone 3's whole
sentence: *the gate must BLOCK, not warn.*

```
REQUIRED
  [1..4] of §5.1
  [5] a paired PASS control from §5.2 in the same file — same construction,
      one number moved. Without it, "FAIL" is green against a constant-FAIL
      gate, and a constant-FAIL gate is exactly as broken as a constant-PASS
      one (it blocks every good version instead of admitting every bad one)
  [6] for C03, C06, C07, C08 — the AND-vs-OR cells: the test docstring states
      which side is below and records that OR semantics would make this cell
      PASS. This is what makes the cell readable as evidence for D-19 rather
      than as an arbitrary FAIL
  [7] for C08 (exactly-at on one side): §3.2 [1], [2] and [4] — NOT [3].
      C08 cannot kill M-G#1 (the box in §3.2 says why), so its boundary is
      asserted on aggregate.citation_accuracy and its mutant is `and` -> `or`
  [8] mutation evidence: M-G#2 (invert PASS/FAIL) killed by at least one cell
      in this group, AND the `and` -> `or` mutant killed by at least one of
      C03, C06, C07, C08

DERIVED BAND
  all of [1..8] applicable to the cell ⇒ HIGH
  missing [8]      ⇒ MEDIUM
  missing [5]      ⇒ unknown
  missing [6] on an AND-vs-OR cell ⇒ MEDIUM, and say so explicitly
```

**C07 is money-shot step 7.** `rel_success = below`, `rel_citation = above`: the citations are impeccable
and the answers are wrong. A version like that must be blocked, and under OR semantics it would not be.
If you build only one FAIL cell before Day 20, build this one.

---

## 6. Grid F — SCORER JUDGEMENT, 7 rows, all buildable today

| Axis | Values | Where the value comes from |
|---|---|---|
| `answer_shape` | `refuses` · `answers-from-chunk` · `answers-with-no-chunk` | the `AgentAnswer` handed to `score_case` (`agent_runner.py:30-55`) |
| `grounding` | `authorized-match` · `no-match` · `out-of-scope-match` | what `retrieved_citations` contains, relative to the case's `expected_citation` and `expected_tenant` |

Subject: `score_case` (`harness.py:147-186`). 3 × 3 = 9 cells, `na 2`, **7 rows**
(generator, Grid F).

| Rule id | Removed combination | Why it can never happen |
|---|---|---|
| `na:no-match-cannot-answer-from-chunk` | `answers-from-chunk` × `no-match` | "from chunk" names the provenance of the answer. With nothing retrieved there is no chunk for it to come from — an answer that nonetheless contains the expected phrase is `answers-with-no-chunk` by definition |
| `na:out-of-scope-cannot-answer-from-chunk` | `answers-from-chunk` × `out-of-scope-match` | same reason: the only retrieved material is out of the asker's scope, so an answer built on it is not "from *the* chunk" |

### 6.1 Why this grid exists at all, and why constructed doubles are honest here

Register CP-2.2 split the old Grid 5 in two, because at `provider=fixtures-stub` the interpreter's
`refused` flag is a **pure function** of retrieval: `executors.py:245-251` computes
`citations = [cid for cid in _CITATION_RE.findall(answer) if cid in retrieved_ids]` and then
`"refused": not citations`. At the interpreter, therefore, `answer_shape` is an **output** — the same
defect `verdict` had in the old Grid 3, and the off-diagonal cells there are impossible by construction.

At `score_case` the situation is reversed. `score_case(case, answer, retrieved_citations)` takes the answer
shape as an **argument**. Judging responses — including malformed, over-refusing and unsupported ones — is
literally its job. So `answer_shape` is a legitimate **input axis** here, and there is nothing dishonest
about handing it an `AgentAnswer` that no current interpreter would produce: that is the point of a scorer.

**Label them as such.** Every Grid F test docstring must say that the `AgentAnswer` and the citation list
are **constructed doubles**, and that the cell makes a claim about the scoring rule, not about the
interpreter. Two reasons: it stops the cell being read later as evidence that the interpreter can
fabricate (it cannot, at the stub — that is Grid E's problem and AIE-1's), and it stops the reverse
mistake of deleting the cell as "unrealistic".

### 6.2 The axis reading is fixed here

`score_case` sees exactly three things. The axes must be expressed in those three things or they are not
causally exercised (§4.5):

| Axis value | Operationally |
|---|---|
| `answer_shape = refuses` | `AgentAnswer(refused=True, ...)` |
| `answer_shape = answers-from-chunk` | `refused=False` **and** `answer` contains `case.expected` as consecutive tokens (`_contains_phrase`, `harness.py:129-144`) |
| `answer_shape = answers-with-no-chunk` | `refused=False` **and** the assertion the answer makes is not supported by an authorized retrieved chunk — either the expected phrase is absent, or it is present while the trace produced nothing that could have supplied it |
| `grounding = authorized-match` | `retrieved_citations` contains the case's own `expected_citation` entry |
| `grounding = no-match` | `retrieved_citations == []` |
| `grounding = out-of-scope-match` | `retrieved_citations` contains a chunk that is **not** in `expected_citation`: a chunk of `expected_tenant` on a refusal case, a chunk of an unrelated third tenant, or an id whose tenant prefix does not parse (`_citation_tenant`, `harness.py:49-57`) |

### 6.3 The 7 rows and what each must prove

`branch` says which arm of `score_case` the cell enters — `case.expects_refusal` decides it
(`golden_case.py:87-111`), and the two arms have **different scoring rules**, so getting the branch wrong
silently changes the subject of the cell.

| id | `answer_shape` | `grounding` | branch | what the cell must prove | §6.4 |
|---|---|---|---|---|---|
| F01 | refuses | authorized-match | answerable | over-refusal is not rewarded: the authorized chunk was there, the agent refused anyway ⇒ the case FAILS, while `citation_accuracy` stays high | 6.4.1 |
| F02 | refuses | no-match | refusal | the honest refusal: refused, cited nothing ⇒ the case PASSES. **Plus** the value the refusal branch pins for `citation_accuracy` — see Q8 | 6.4.2 |
| F03 | refuses | out-of-scope-match | refusal | the leak check reads **trace**, not `answer.citations`, and it is fail-closed on unparseable ids. Three sub-shapes, two outcomes | 6.4.3 |
| F04 | answers-from-chunk | authorized-match | answerable | the canonical pass. Without it every FAIL cell here is satisfiable by a scorer that fails everything | 6.4.4 |
| F05 | answers-with-no-chunk | authorized-match | answerable | **citations perfect, answer wrong ⇒ FAIL.** One half of the two-level model of §4.1 | 6.4.5 |
| F06 | answers-with-no-chunk | no-match | answerable | **answer right, nothing cited ⇒ case PASSES with `citation_accuracy = 0.0`.** The other half, and the single most load-bearing cell in Grid F | 6.4.5 |
| F07 | answers-with-no-chunk | out-of-scope-match | both | answered anyway, on material the asker may not have. The closest the scorer gets to *"refuses rather than fabricates"* | 6.4.6 |

### 6.4 Per-cell obligations

Common to all seven:

```
REQUIRED
  [1] the asserted values are read from the SmokeResult that score_case
      returned (harness.py:180-186) — every field the cell claims something
      about, not just `success`
  [2] the case is built as a real GoldenCase, so that `expects_refusal`
      (golden_case.py:109-111) DERIVES the branch. Do not pick the branch by
      hand-tuning fields until it happens to come out right — state in the
      docstring which of the two axes (T1 cross-tenant / T6 cross-role) puts
      the case in the branch
  [3] the docstring labels the AgentAnswer and citation list as constructed
      doubles (§6.1)
```

#### 6.4.1 F01 — over-refusal

```
REQUIRED
  [1..3]
  [4] assert BOTH: success is False AND citation_accuracy is at its maximum.
      The pair is the cell: it shows the two metrics moving independently
  [5] the answer text must CONTAIN case.expected while refused is True — see
      the note below. A generic refusal string makes this cell unfalsifiable
  [6] mutation evidence: drop the `answer.refused is False` conjunct at
      harness.py:169 — this cell must go red
DERIVED BAND
  [1..6] ⇒ HIGH        missing [6] ⇒ MEDIUM
  missing [4] or [5] ⇒ unknown
```

Requirement [4] is what stops this cell being a duplicate of F05. Both fail; only F01 fails *while the
citations are perfect and the agent volunteered a refusal*.

**Requirement [5] is the same shape as GUIDE-A §6.4 `[3]`, and it is measured.** Build F01 the obvious way —
`refused=True` with a generic refusal sentence — and the cell is green, but **dropping the
`answer.refused is False` conjunct changes nothing**: `_contains_phrase` was already `False` because a
refusal sentence does not contain `"12 ngày"`. The mutant is masked by the answer text, so the cell reports
"correct" while measuring nothing about the `refused` flag. Measured over all 12 Grid F sub-shapes with a
generic refusal string, that mutant goes red on **zero** of them. Give the answer text the expected phrase
*and* `refused=True` — the shape `test_smoke_runner.py::test_answerable_refused_flag_fails` (`:123-129`)
already uses, with `answer="12 ngày"` — and F01 becomes the unique killer.

#### 6.4.2 F02 — the honest refusal, and the Q8 hardcode

```
REQUIRED
  [1..3]
  [4] assert success is True
  [5] assert the citation_accuracy value the refusal branch produces, as a
      literal, with a comment naming harness.py:178 and Q8 as the reason it
      has that value. This is a PIN, not a behaviour claim
  [6] a paired negative control: the SAME answer shape on an ANSWERABLE case
      ⇒ success is False. Without it, "refused and passed" is green against a
      scorer that passes everything in the refusal branch
DERIVED BAND
  [1..6] ⇒ HIGH        missing [6] ⇒ unknown        missing [5] ⇒ MEDIUM
```

Requirement [5] deserves an explanation, because it looks like the guide telling you to lock a value the
review calls questionable. `harness.py:178` sets `citation_accuracy = 1.0` on the refusal branch, and
`harness.py:166` self-labels it *"Q2 chưa chốt — chỉ hiển thị skeleton"*. **No test in the repo asserts
that value** — so today, changing `1.0` to `0.0` there turns nothing red. That is a live unguarded
mutation point in your own quadrant. Pinning it means that when Q8 (§11) is answered, the answer shows up
as a **visible decision change** in a test that has to be edited in the same commit, rather than as a
number that quietly moves and shifts every aggregate that depends on it.

#### 6.4.3 F03 — the leak check, three sub-shapes

The refusal branch is a conjunction of three conditions (`harness.py:175-177`), and this cell is the only
one that can tell them apart:

```
REQUIRED
  [1..3]
  [4] sub-shape (a): trace cites a chunk of case.expected_tenant
      ⇒ success is False                       (the leak)
  [5] sub-shape (b): trace cites an id whose tenant prefix does not parse
      ⇒ success is False                       (fail-closed on unparseable)
  [6] sub-shape (c): trace cites a chunk of an unrelated THIRD tenant
      ⇒ success is True                        (the v0 rule bans only
                                                expected_tenant)
  [7] the docstring records that (c) is a recorded v0 decision, not an
      accident, and names the pin-test that holds it (§9)
  [8] `answer.citations` is populated with a DIFFERENT set from
      retrieved_citations in at least one sub-shape, and the assertion follows
      the trace. This is what proves the scorer reads the trace
  [9] mutation evidence: flip `!=` to `==` at harness.py:176 ⇒ (a) goes red.
      Record that (b) and (c) do NOT go red, and why
DERIVED BAND
  [4..9] ⇒ HIGH        missing [9] ⇒ MEDIUM
  missing [6] or [8] ⇒ unknown
```

Sub-shape (c) is uncomfortable and you should not smooth it over: a refusal that leaked a third tenant's
chunk into the trace still scores `success = True`. That is what the v0 rule says
(`docs/scorecard-v0.md` §2.3 as implemented at `harness.py:176`), and Grid A's fence cells are where that
class of leak is actually caught. Your cell's job is to make the decision visible, so that if the Day-11 workshop tightens
the rule, one test changes and the change is deliberate.

#### 6.4.4 F04 — the canonical pass

```
REQUIRED
  [1..3]
  [4] assert success is True AND citation_accuracy is at its maximum
  [5] mutation evidence: force `success = False` in both arms of score_case
      (harness.py:169 and :177) ⇒ this cell goes red
DERIVED BAND
  [1..5] ⇒ HIGH        missing [5] ⇒ MEDIUM        missing [4] ⇒ unknown
```

This is the `M-E`-analogue cell for Grid F: it is the row that makes every other row's failure meaningful.
A scorer that returns `success = False` unconditionally satisfies F01, F05, F06 and F07 — five of the seven
rows expect `False` — and only F04 and F02 catch it. Do not choose the intersection mutant
(`expected & set(retrieved)` → `expected | set(...)`, `harness.py:172`) as F04's evidence: with one expected
citation that is also the retrieved one, union and intersection give the same size, so F04 stays green. That
mutant is killed by **F06 and F07** instead, where the retrieved set differs from the expected one.

#### 6.4.5 F05 and F06 — the two-level model, both directions

These two are mirror images and they are the reason §4.1 is enforceable.

```
F05  citations perfect, answer wrong
REQUIRED
  [1..3]
  [4] assert success is False AND citation_accuracy is at its maximum
  [5] the same case, same trace, with a CORRECT answer ⇒ success is True.
      One variable moved

F06  answer right, trace empty
REQUIRED
  [1..3]
  [4] assert success is True AND citation_accuracy == 0.0, in ONE test, on ONE
      result object. Asserting them in two tests loses the point
  [5] a second sub-shape: answer ALSO wrong with an empty trace ⇒ success is
      False and citation_accuracy == 0.0 — so that [4] is not satisfiable by a
      scorer that ignores the answer entirely
  [6] the docstring states, in one sentence, that this per-case PASS is
      correct (harness.py:159 stands, register CP-2.1) and that the same case
      drags aggregate citation_accuracy down, which is where the gate acts

DERIVED BAND (both)
  [1..5]/[1..6] ⇒ HIGH        missing the paired sub-shape ⇒ unknown
```

F06 requirement [6] is the sentence that keeps somebody from "fixing" the apparent inconsistency later. It
is also the cell tier B grades hardest, because a trainee who has internalised the withdrawn version of
D-19 will write `assert success is False` here and be confidently, contract-breakingly wrong.

#### 6.4.6 F07 — answered on out-of-scope material

```
REQUIRED
  [1..3]
  [4] on an ANSWERABLE case: trace cites only out-of-scope material and the
      answer asserts something anyway ⇒ success is False AND
      citation_accuracy == 0.0
  [5] on a REFUSAL case: refused is False ⇒ success is False, regardless of
      what the trace contains. The two sub-shapes fail for DIFFERENT reasons
      and the docstring must say which
  [6] the docstring states what this cell does NOT prove: that the system
      refuses rather than fabricates. At provider=fixtures-stub the
      interpreter cannot fabricate (executors.py:246,251), so this is a claim
      about the SCORING of a fabricated shape, not about the agent
DERIVED BAND
  [4]+[5]+[6] ⇒ HIGH        missing [6] ⇒ MEDIUM, and record why
  missing [5] ⇒ unknown
```

Requirement [6] is register CP-2.4 #3 applied to your surface: "refusal cells go green today with zero new
behaviour" is a real trap, and the version of it that would catch you is claiming F07 as evidence for the
umbrella's *refuses-rather-than-fabricates* AC. It is not. It is evidence that the scorer does not reward
that shape.

---

## 7. Mutation evidence

Procedure, from `00-METHODOLOGY.md` §9: plant the mutant, run the named test, record **which assertion
line went red**, remove the mutant. Red on an unexpected line is itself a finding — write it down.

### 7.1 The `M-G` family: both points are unanchorable today

| Mutant | Change | Target line | Measured today |
|---|---|---|---|
| `M-G#1` | threshold comparison `>=` → `>` | **does not exist.** Nearest line: `compute.py:30`, the `raise` | **0 tests red** |
| `M-G#2` | invert `PASS` / `FAIL` in the verdict expression | **does not exist.** Same insertion point | **0 tests red** |
| `and` → `or` in the verdict expression | breaks D-19's AND ruling | **does not exist.** Same insertion point | **0 tests red** |

The third row is **not a register id.** Register §7 credits the `M-G` family with 4 points and the deep dive
anchors 2 of them; the AND/OR point is the one D-19 needs and the register has not numbered. It is written
here by its edit rather than by an id, and it is a candidate addition to register §7 for the mentor to
number — do not invent an id for it in your docstrings, name the edit.

Which cells kill which (derived from the D-19 oracle, and checked arithmetically against the §3.2
construction):

| Mutant | Killed by | Not killed by, and why |
|---|---|---|
| `M-G#1` `>=` → `>` | **C02, C04, C05** | C01, C03, C06, C07, C09 — no equality is decisive. **C08** — the success side already decides FAIL, so the citation equality is masked (§3.2) |
| `M-G#2` invert `PASS`/`FAIL` | **any single cell** | nothing — which is why it is weak evidence on its own, and why the paired-control requirements exist |
| `and` → `or` | **C03, C06, C07, C08** | C01, C02, C04, C05 (both sides on the PASS side) and C09 (both below) — `or` gives the same verdict |

There is no comparison operator anywhere in the repo to mutate. The measurement in
`round2-deepdive-3-eval-gate.md` §4.1–4.2 was taken against a throwaway reference implementation
(`>=` + AND, per the `compute.py:26-29` docstring), planted, measured, reverted — and the result was that
the whole-workspace summary was **identical to the baseline** for both mutants. That number answers *"does
the existing suite catch this?"* (no) and does **not** answer *"will yours?"*. Your `M-G` evidence must be
measured against **your** implementation, after Day 20, on the cells named in §5.

Two consequences to plan for:

1. **`M-G#1` is not even well-defined until Q1/M1 are answered.** If the ruling had been `>`, then
   `>=` → `>` is not a mutant, it is the correct version, and every test written the other way is wrongly
   red. D-19 settles it as `>=` (§4.1), which is why the mutant is definable at all. Do not let that ruling
   drift: the cell and the mutant are two halves of one statement.
2. **`M-G#2` needs a discriminating cell.** Inverting `PASS`/`FAIL` is invisible to a suite that only has
   PASS cells or only FAIL cells. §5.2 `[5]` and §5.3 `[5]` — the paired controls — exist for this mutant.

### 7.2 One `M-G#2` site that IS live today, and nothing is watching it

`packages/evalhub/src/studio_evalhub/cli.py:222`:

```python
        lines.append(f"{r.case_id:<20} {('PASS' if r.success else 'FAIL'):<8} {r.citation_accuracy:>12.2f}")
```

Invert it to `('FAIL' if r.success else 'PASS')`. Measured in the deep dive §4.2(a): evalhub
`38 passed, 1 skipped, 1 xfailed, 1 xpassed` — **unchanged**; whole workspace — **unchanged**. The same
line exists a second time at `scripts/smoke_eval_d6.py:217`, also with no test importing it.

Why this survives: `_render` has **zero** tests. `test_determinism.py:12-13` says so itself
(*"`run_smoke` có đúng **1** test … và `_render` có **0**"*), and `:19-23` explains the deliberate decision
not to snapshot the table format because the format is still moving. That decision is defensible. What
happened is that *"do not pin the format"* got implemented as *"do not check anything"* — including the
`success` → label mapping, which does not depend on column widths at all.

And the consequence is not academic: `cli.py:1-6` declares this table to be weekly demo #1. The total line
(`cli.py:223-225`) counts `r.success` directly and does **not** read the label, so an inverted build prints
`5/5 PASS` on the summary line while every detail line reads `FAIL`. A self-contradicting table, with no
test noticing, in front of the room.

**Honest statement of where this leaves the grid:** this mutation point belongs to **no cell** in Grid C or
Grid F. the generated row set is frozen, so this guide does not invent a row for
it. It is recorded here as the one **calibration ruler** the `M-G` family has today — the only `M-G` point
that can be planted and measured before `compute_scorecard` exists — and as an open gap for the mentor:
either a row gets assigned to the `_render` label mapping, or blocking zone 3 keeps a hole that is live,
cheap to close, and pointed at the surface humans read. See §11.

---

## 8. The `agreement-check` problem — blocking, and not resolved here

Umbrella §3.4 requires an agreement-check against hand labels: *does the judge deserve to be trusted?*
The target field exists. The source field does not.

| Half | State | Anchor |
|---|---|---|
| where the number goes | exists — `Judge.agreement: float` | `contracts/.../scorecard.py:19` |
| where the human label comes from | **nowhere.** `GoldenCase` has 8 fields; none of them holds a human pass/fail judgement. `expected` (`golden_case.py:73-78`) is a hand-labelled **answer fragment** for token matching, not a verdict | `golden_case.py:28-111` |
| a table that could hold one | **none.** `eval.golden_sets` is `golden_set_ref` + `cases JSONB`; `eval.scorecards` mirrors the `Scorecard` contract | `packages/evalhub/src/studio_evalhub/schema.py` |
| permission to fake it | **explicitly refused.** `judge.py:6-9`: every case's agreement score *"must be derivable from a real comparison against a hand label, not a constant/placeholder value"* | `judge.py:6-9` |

So the specification requires a comparison for which the data shape provides no operand, and forbids the
only thing you could otherwise do. Note that the example you will copy from is itself the forbidden thing:
`Judge(label="pass", agreement=0.95)` at `test_scorecard_roundtrip.py:27` and `test_eval_gate.py:70` — both
constants, both in fixtures, both harmless there and poisonous if promoted into an implementation.

**Why this is stated as a blocking open question rather than solved with a workaround.** Without an
agreement-check, this is the failure path, end to end: the judge is implemented with a weak prompt, or a
model with an agreeableness bias, so it returns `success=True` for every subjective case including the
wrong answers. It reports its own `agreement` as 0.95. `success_rate` comes out high, the gate says
`PASS`, `publish` ships the bad version. **Nothing in the design catches it**, because (a) there is no
hand label to compare against, and (b) `agreement` is a number the thing being audited assigns to itself.
That is the "false green" pattern (`xanh giả`, the repo's own term from `test_pg_kb.py`) at the highest
level of the system — a quality-check metric filled in by the subject of the check.

**Do not resolve this yourself.** It is open question M5 (§11). The three candidate answers all cost
something outside your quadrant: a new `GoldenCase` field touches DE, who owns the shape; a separate table
touches schema; dropping the `agreement` requirement touches a frozen contract and the umbrella AC. All
three need the mentor. Until then, every `LLMJudge` cell is `todo:` with **no ETA you can commit to**, and
that is the honest state to report at Day 20 — not a fabricated `agreement`.

---

## 9. Pinned-by — must-fix rows that collide with a `KHÓA` pin-test

Per `00-METHODOLOGY.md` §7.2 and register CP-2.5: a pin-test asserts a **decision**, not a behaviour. When
the decision changes, the pin-test changes **in the same commit**, with a reference to the decision. Doing
that is not weakening a gate. Not knowing which pin you are about to hit is how a trainee concludes the
guide is wrong.

| Row / change | Pinned-by | What has to happen |
|---|---|---|
| `C-R01` once the seam lands | `test_eval_gate.py::test_harness_judge_compute_not_implemented` (`:43-49`) — `xfail(strict=False)`, asserts all three seams raise | Both change together. The `strict=False` policy is the kit owner's (`:8-12`), so the change needs the M6 ruling first |
| C01–C09, all of them | `test_eval_gate.py::test_gate_blocks_on_fail` (`:28-40`) — `xfail(strict=False)`, and `:38` uses a label-only "bad agent" | When a real verdict exists, this test either becomes real or is retired with a reference. It cannot stay as it is and be counted as evidence |
| Any change to per-case `success` semantics (i.e. anyone acting on the **withdrawn** D-19 instruction) | `test_smoke_runner.py::test_citation_accuracy_zero_when_trace_empty_but_success_still_true` (`:164-175`) | This pin **should not move**. It is the guard on CP-2.1. If your change turns it red, your change is the thing that is wrong |
| F02, and any Q8 resolution | `harness.py:178` has **no pin at all** today — that is the gap F02 `[5]` closes | Write the pin in F02, then flip it in the same commit as the Q8 ruling |
| F03 sub-shape (c) | `test_smoke_runner.py::test_refusal_other_tenant_citation_still_fails_closed` (`:250-256`) — asserts a third-tenant citation still passes, self-labelled as recording v0 behaviour | If the Day-11 workshop tightens the leak rule, this pin and F03 `[6]` flip together |
| F03 sub-shapes (a) and (b) | `test_smoke_runner.py::test_refusal_leak_fails` (`:234-239`), `test_refusal_unparseable_citation_fails` (`:242-247`) | These already assert the right thing; F03 supersedes them with the three sub-shapes in one cell. Do not delete them, and do not count them twice |
| An aggregate that changes `SmokeResult` shape | `test_determinism.py::test_equality_actually_discriminates` (`:230-253`) | Add the new field to the perturbation list in the same commit, or the negative control silently stops covering it |

If you find a pin-test this section did not list, that is a gap in **this guide** — report it. Do not route
around it in either direction.

---

## 10. Things that never count as evidence in this guide

- **A hand-built `Gate` or `Scorecard`.** `test_scorecard_roundtrip.py:41` writes `verdict="PASS"` by hand
  and `:38` writes `Aggregate(success_rate=1.0, citation_accuracy=0.95)` by hand. That file has a real job
  (`:1-8`: pinning evalhub to the frozen contract instead of redefining it) and it does that job well. It
  is **not** evidence about the gate: no code computes those two values, so every possible mutant inside
  `compute_scorecard` leaves those lines green.
- **`assert restored == original`** (`test_scorecard_roundtrip.py:57-58`). `Scorecard` is a frozen pydantic
  model; `model_dump` → `model_validate` round-tripping is a property of pydantic, not of your quadrant.
- **A constant `agreement`** (§8). It is what `judge.py:8-9` forbids, and the fixtures model it.
- **`xfail` or `skip` in any form on a coverage cell.** `test_eval_gate.py`'s two cases are
  `xfail(strict=False)` and cannot fire in either direction (§4.3). Do not extend that pattern. The single
  exception in this guide is `C-R01`, which is not a coverage cell and may use `xfail(strict=True)` —
  never `strict=False`.
- **`pytest.raises(NotImplementedError)` as a behaviour test** for any of C01–C09. It proves the seam is
  absent. Only `C-R01` gets to make that claim, and only because that is all it claims.
- **A cell whose axis value never enters the test's setup** (§4.5). `tools/xcheck_cell_ids.py` will not
  catch it; the band rule makes it `unknown`.
- **A PASS cell with no paired FAIL control, or a FAIL cell with no paired PASS control** (§5.2, §5.3).
  Either one alone is green against a constant-verdict gate.
- **A test whose threshold is read out of the value under test** (§3.2).

---

## 11. Open questions that block rows

Do not guess these. Each one changes what a correct test asserts, and three of them can silently invert a
result.

| id | Question | Rows it blocks |
|---|---|---|
| **Q1 / M4** | *"Exactly at threshold"* on floats: exact `==`, `math.isclose`, rounding to n digits, or `Fraction`? Per-case values are ratios with denominators 1–5 (`harness.py:171-173`) and the aggregate mean does not exist yet (§4.2). Measured: the mandated one-citation-per-case construction is exact (`11/20 == 0.55` is `True`), but a mixed-denominator 20-case set measured `0.6174999999999999` against an exact `0.6175` | **C02, C04, C05, C08** — the four `exactly-at` cells. C02, C04, C05 are also the only cells that distinguish `>=` from `>` (§7.1) |
| **Q8** | How do refusal cases contribute to aggregate `citation_accuracy`? `harness.py:178` pins per-case `1.0` for every refusal, including cases that already FAILED; `harness.py:166` self-labels this *"Q2 chưa chốt"*. The escalation review argues **excluding refusals from the denominator** is cleaner than pinning `1.0`, because pinning inflates refusal-heavy sets under AND. Measured consequence already on record (`scorecard-v0.md:276-282`): a 10-case run reported `0.90` where the answered-cases-only value was `0.833`. And measured here in float: 10 refusals at `1.0` plus 20 answered cases at `0.85` gives **exactly** `0.9` — landing a version that deserves FAIL precisely on a `0.9` threshold, which under `>=` is a PASS | **every Grid C cell whose dataset contains a refusal case**, and the pin in **F02** `[5]`. It also decides which side of a threshold in `(0.833, 0.90]` a real run falls on |
| **M5** | Where do the judge's hand labels come from — a new `GoldenCase` field (DE owns the shape), a separate table, or is the `agreement` requirement dropped? Target field exists (`contracts/.../scorecard.py:19`), source field exists nowhere, constants forbidden (`judge.py:8-9`) | **every `LLMJudge` cell**, and the umbrella §3.4 AC *"the judge is trustworthy"*. §8 |
| **M1** | Confirmation that the gate operator is `>=` and not `>`. D-19 rules `>=` (§4.1) on the strength of the word *meet* at `compute.py:28`. It is listed here because if it ever moves, `M-G#1` inverts from mutant to correct version | C02, C04, C05 and the definition of `M-G#1` |
| **M6** | May the acceptance set require `strict=True` (or marker removal) at `test_eval_gate.py:28,43`? The `strict=False` choice is recorded as deliberate kit-owner policy at `:8-12` | whether blocking zone 3 may count those two tests as "watched" at all. `C-R01` is written to be correct without needing this answer |
| **M8** | By what mechanism is a genuinely bad version constructed, so that it measurably loses points? `test_gate_blocks_on_fail:38` uses a label string; the current LLM fixture is described as reading only the prompt, and no document claims it is sensitive to `instructions` | the end-to-end form of money-shot step 7. The `compute_scorecard`-level cells (C03, C06–C09) are specified so they do **not** depend on this |
| **new** | Does the `_render` label mapping (`cli.py:222`, `scripts/smoke_eval_d6.py:217`) get a cell? It is the only `M-G#2` site that can be measured today, it is unguarded, and it belongs to no generated row (§7.2) | nothing formally — which is the problem |
