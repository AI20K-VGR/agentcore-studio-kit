# Coverage matrix and acceptance conditions

> The integrating document. Every guide points here for the totals; this file points back for the detail.
> Numbers are **generated** by a covering-array script, not counted by hand. If a guide disagrees with this
> file, this file is right — and the fix is to regenerate, not to patch a number.
>
> Read `00-METHODOLOGY.md` first if you have not.

---

## 1. Who owns what

| Guide | Grids | Owner | Rows now | Cells waiting on a seam |
|---|---|---|---|---|
| `GUIDE-A-isolation.md` | A (isolation) + D (provenance) | **DE** | 16 + 3 | 22 + 1 |
| `GUIDE-B-recipe.md` | B (recipe lifecycle) + surface-5 pool rows | **SWE** | 8 | 1 |
| `GUIDE-C-eval-gate.md` | C (eval gate) + F (scorer judgement) | **AIE-2** | 0 + 7 | 9 |
| `GUIDE-D-interpreter.md` | E (refuse) | **AIE-1** | 3 | 3 |

Every file has exactly one owner. That is deliberate: an earlier draft had eight files across four people,
with three surfaces owned by "nobody" — and unowned files do not get written. The cross-cutting invariants
that used to live in those files are folded into the quadrant guide of whoever owns the code they touch.

The 8-step e2e spine is **not a file**. It is a scheduled whole-team exercise with a named driver, because a
file nobody owns is a file nobody writes.

---

## 2. The totals

| Grid | Subject | exhaustive | `na:` | `todo:` | real | `t` | rows |
|---|---|---|---|---|---|---|---|
| **A** | isolation | 64 | 18 | 22 | 24 | 3 | **16** |
| **B** | recipe lifecycle | 16 | 7 | 1 | 8 | 2 | **8** |
| **C** | eval gate | 9 | 0 | 9 | 0 | 3 | **0** + 1 ratchet |
| **D** | number provenance | 18 | 15 | 0 | 3 | 3 | **3** |
| **E** | refuse (interpreter) | 6 | 0 | 3 | 3 | 3 | **3** |
| **F** | scorer judgement | 9 | 2 | 0 | 7 | 2 | **7** |
| | | **122** | **42** | **35** | **45** | | **37 + 1** |

Plus: flow cells (`S1`, `S4a`, `S4b`), one gateway pilot (`A-P1`), and the surface-5 pool rows. Committed
total lands near **50 rows**, roughly 12–13 per person.

### Why the number is small, and why that is the point

An earlier draft of this design claimed 110–140 rows across ~300 cells. Computing it rather than estimating it
gave 45 real cells and 37 rows. The estimate was wrong three times in one day, always the same way: axis
arithmetic without applying the exclusion rules.

The lesson is in the methodology now, and it applies to you too: **compute before quoting a number.** A guide
that overstates its own size gets skimmed, and a skimmed guide gets filled with the cheapest green that
satisfies the letter.

### `todo:` is a schedule, not a verdict

35 cells are `todo:` — possible, but the code does not exist yet. They are **not** counted as covered, and in
a blocking zone they **do** block at Day 30. But they are not a veto today.

| Seam | Cells | Owner | ETA |
|---|---|---|---|
| `todo:kb-pipeline` (`re_index`, `consent_purge`) | 22 | DE | Day 20 |
| `todo:compute-scorecard` | 9 | AIE-2 | Day 20 |
| `todo:embedding-gateway` | 3 + `A-P1` | AIE-1 | Day 20 |
| `todo:publish-seam` | 1 | SWE | Day 20 |
| `todo:kb-search` | caps all 16 Grid-A rows at MEDIUM | DE | Day 20 |
| `todo:refusal-reason` | Grid E `reason` enum | AIE-1 | Day 20 |

Every `todo:` in a blocking zone carries an owner and an ETA. **Day 20 is a hard checkpoint**: a `todo:` that
has not landed by then escalates to a sign-or-descope decision. It does not sit quietly until Day 30 and then
force a waiver — a blocking gate that gets waived once teaches everyone that verdicts are negotiable, which
is the opposite of what this set is for.

Three markers, three meanings:

| Marker | Meaning | Counts as covered | Blocks at Day 30 |
|---|---|---|---|
| `na:<rule-id>` | structurally impossible, forever | yes | no |
| `todo:<seam-id>` | not built yet; needs owner + ETA in a blocking zone | **no** | **yes** |
| `defer:<decision-id>` | mentor-signed descope, recorded in the register | **no** | **no** |

> **A descoped cell is never "covered", and a `todo:` that gets descoped does not become `na:`.**
> This is stated bluntly because the alternative is an exploit, not a rounding error. If descoping promoted a
> cell to `na:`, and `na:` counted as covered, then the cheapest way to pass acceptance would be to pull the
> INV-7 descope ladder — which is **pre-approved from Day 1** and judged only by "the 8-step demo still
> works". Three seams go unlanded, their cells get descoped, every zone reports covered, and the run passes
> with **zero blocking-zone tests in existence**.
>
> `na:` means the situation cannot arise. `defer:` means we chose not to look. Those are not the same fact and
> they must not produce the same number.

A marker without a matching id counts as `unknown`, which blocks. Prose saying "not applicable here" is not a
marker — that sentence is equally true of an impossible cell and a forgotten one.

---

## 3. Blocking zones

Roll-up is the **minimum of each zone**, never the average. One cell short of evidence in a blocking zone
blocks the run.

| Zone | Name | Cells | Owner of most of it |
|---|---|---|---|
| **Z1** | cross-tenant / cross-role leakage | A03–A08, A11, A12, A15, A16, `A-P1` | DE |
| **Z2** | fail-open when the tenant cannot be resolved | A09, A10, A13, A14 | DE |
| **Z3** | eval gate fails to block a bad version / rollback returns the wrong version | C01–C09, B-publish rows | AIE-2, SWE |
| **Z4** | cost lineage diverges / trace loses ordering | D01–D03 | DE |
| **Z5** | agent fabricates instead of refusing | E01–E03, `E-M4` (**mandatory**), `E-S1`, `E-S2` | AIE-1 |

**Z4 was re-scoped before anyone saw it, and you should know why.** The stated invariant is one cost number
across three surfaces. Measured: only **one** of the three surfaces exists, and `cost` is the constant `0.0`
(`interpreter.py:63,278`) — so three surfaces comparing three zeroes agree even if all three formulas are
wrong. The ~12 cells covering the missing surfaces are `defer:cost-dashboard-unowned`, because a `todo:`
requires an owner and there is none. What remains is a gate someone can pass or fail: is the one real surface
internally consistent, and is its ordering trustworthy?

**Z3 currently has zero buildable rows**, because `compute_scorecard` raises `NotImplementedError`. It ships
as nine `todo:` cells plus one **ratchet row** whose only job is to fail the day the seam lands. See
`GUIDE-C-eval-gate.md`.

---

## 4. Acceptance conditions

Seven conditions. All seven must hold. **Each one names how it is checked** — the previous version of this
apparatus, on a different system, had conditions that were satisfiable without checking anything, and two of
four turned out to be vacuous. So: if a condition cannot be checked by a command or a named person reading
named evidence, it does not belong here.

| # | Condition | How it is checked | Fails when |
|---|---|---|---|
| **1** | Every row in §2 has a test carrying its cell id, or a marker with a matching id | `python3 tools/xcheck_cell_ids.py --tests <paths>` | a row has neither a test nor a marker; or a test claims an id no guide defines |
| **2** | Tier A and tier B agree on every cell id and every marker id | same command, no `--tests` | one tier has a cell or marker the other does not |
| **3** | Every blocking-zone cell's test **actually ran** — not `skip`, not `xfail`, not inside a `continue-on-error` job | `pytest -q -rsxX` on the acceptance run, cross-referenced against the blocking-zone cell list | any blocking-zone cell's test appears in the `SKIPPED` / `XFAIL` / `XPASS` list |
| **4** | Every blocking-zone cell at band HIGH has recorded mutation evidence: mutant id, the assertion line that went red | the band-derivation script reads the evidence block in each test docstring | a HIGH claim has no mutant evidence ⇒ the script downgrades it to MEDIUM automatically |
| **5** | Every ordering flow marked blocking is **deterministic** — same result on ten consecutive runs, with an `asyncio.timeout` | `pytest --count=10 <flow tests>` (or a loop), plus grep for `asyncio.timeout` in each flow test | a flow test passes intermittently, or has no timeout and can hang the suite |
| **6** | Every `todo:` in a blocking zone has an owner and an ETA, and the Day-20 checkpoint recorded a **live non-`todo:` cell count per zone** | the mentor reads §2's seam table against the register, and records the counts | a `todo:` has no owner; or Day 20 passed with no sign-or-descope decision; or the counts were not recorded |
| **7** | **Every blocking zone contains at least one cell whose test actually ran and killed a mutant, and which is not `na:`, `todo:`, or `defer:`.** A zone with none reports **NO GATE** — never PASS | the band-derivation script, per zone | a zone's live-cell count is 0. At that point the zone has no opinion, and reporting PASS would be a lie of omission |

### Condition 7 exists because five of the six above can pass with an empty zone

Today's live non-`todo:` cell counts, which is what condition 6 now records:

| Zone | live cells today |
|---|---|
| Z1 cross-tenant leakage | 5 |
| Z2 fail-open | **0** |
| Z3 eval gate | **0** |
| Z4 provenance | 5 |
| Z5 refuse vs fabricate | 3 |

Two of the five zones currently have nothing in them. Without condition 7, both would report PASS at Day 30 by having
nothing to fail — and "PASS" and "we never looked" would print the same word. **NO GATE** is the honest
output, and it is not a passing outcome.

### Condition 3 is the one that would have been vacuous

It exists because of a measured fact: a CI job named `leak-test` reports `success` in 0.14 s while evaluating
**no assertions** — both its cases are `xfail(strict=False)`, and its job is `continue-on-error: true`. An
acceptance condition that reads job colour would pass on that. So condition 3 reads **per-test outcomes**, and
`SKIPPED`, `XFAIL`, and `XPASS` all count as "did not run".

### Condition 4 is what makes bands honest

Bands are **derived**, never declared. Every test carries a machine-extractable evidence block in its
docstring:

```
Cell: A05
Assertions: inclusion=L1 exclusion=L2 pool-path=pool trace-surface=L4
Mutants: M-R#1->L2 M-R#4->L2 M-E->L1
```

The band-derivation script applies each guide's rules to those blocks and emits the per-zone `min` roll-up.
The rules in the guides are already written as if they were code; the script is what makes running them on
~50 cells in GATE-3 week possible at all. Hand-deriving 50 bands while reconciling four submissions does not
happen, and then the verdict gets improvised — which defeats the whole apparatus.

**Audit policy:** the mentor deep-reads **100%** of blocking-zone cells and samples 20% elsewhere. The script
makes using the ruler feasible; it does not replace reading.

---

## 5. Pin-tests: the suite defends its own holes

This repo has a `KHÓA` idiom — green tests whose job is to assert the *current configuration*, holes included.
There are more than ten. The clearest example: `tests/test_ops.py:145-155` asserts
`continue-on-error is True` for the `leak-test` job, so **fixing the biggest hole in the suite turns a passing
test red**.

That is not sabotage. It is a decision, written down as a test so nobody reverts it by accident.

**The rule:** a pin-test asserts a *decision*, not a behaviour. When the decision changes, the pin-test
changes **in the same commit**, with a reference to the decision. Doing that is not weakening a gate.

Every must-fix row in every guide lists its **pinned-by** tests for this reason. If you find a pin-test the
guide did not list, that is a gap in the guide — report it. Do not route around it in either direction: not by
deleting the pin, and not by concluding the fix is impossible.

---

## 6. Regenerating these numbers

The row sets come from a greedy `t`-wise covering-array generator over the axis definitions plus the exclusion
rules. It is deterministic — same input, same rows, same ids — so a regenerated guide can be diffed against
the previous one.

When an axis, a value, or a rule changes: change it in one place, regenerate, and update the guides from the
output. Do not hand-edit a row table. Every counting error this design has had came from hand-maintained
numbers drifting away from the axes they were supposed to describe.

---

## 7. Which tree this describes

Every `file:line` in these guides was verified against exactly this baseline. Check yours matches before you
conclude a citation is wrong:

```bash
git rev-parse HEAD          # 88ad7224523cc70fb0bfe6c0ddc0259a2bd51387
git submodule status
```

| Submodule | SHA |
|---|---|
| `apps/studio` | `2f65a93b38f740c00141991f113b60713508ae67` |
| `apps/web` | `e05e49e2651ed5e1b580278ec7da1c513382952a` |
| `packages/contracts` | `3d7004b2e55d500e3706b9eac412fc809eb4e839` |
| `packages/engine` | `a65c9d6962e19460dab8aafed264499cdc4a1433` |
| `packages/evalhub` | `123e85c44a7932eab48dfb69552c3a869ae01a1c` |
| `packages/kb` | `210135206e3d31853fd9a2974723739ec02dec7d` |
| `packages/workbench` | `afa805dc9ef6ba6b70cd726c2e25addec0bb9c95` |

**Line numbers go stale fast** in a repo four people edit daily. If a citation misses by a few lines, the
symbol name is the real anchor — search for it rather than assuming the guide is wrong. If it misses entirely,
say so; a stale citation is a bug in the guide.

### Two of these pointers are behind the submodules' own `main`

| Submodule | this kit records | that repo's `origin/main` |
|---|---|---|
| `packages/engine` | `a65c9d69` | `a6967a24` |
| `packages/workbench` | `afa805dc` | `134fc262` |

So `git clone --recursive` gives you **older** `engine` and `workbench` code than those repos' `main`. If you
are AIE-1 or SWE, a test can pass in your own repo against code the kit does not contain. Before claiming
evidence for a cell, check which commit the kit is actually building.

---

## 8. Rulings that change who does what

Four decisions were taken after the guides were first drafted. Each one moves work or settles a question the
guides had left open, so they are recorded here rather than only in the mentor's register.

| Id | Ruling | Who it lands on | What it changes in these guides |
|---|---|---|---|
| **D-21** | **The middleware validates `recipe.tenant_id` against the session-resolved tenant.** | **SWE** | The hole in `GUIDE-A` §4.1 now has an owner. A recipe declaring another tenant's UUID must be refused before retrieval. `GUIDE-A`'s `client-declared` cells (`A11`, `A12`, `A15`, `A16`) surface (b) stop being "an architecture hole nobody owns" and become a testable obligation — but the test lives with **SWE**, next to `resolve_tenant`, not with DE |
| **D-22** | **"Exactly at threshold" means the case count lands on a round threshold fixed in advance, compared with `==`.** No tolerance | **AIE-2** | `GUIDE-C`'s `exactly-at` cells must build their golden set so the aggregate lands exactly on a threshold chosen *before* the data (11/20 = 0.55). Copying a computed float into the threshold is the banned construction. A tolerance was rejected because it would make `>=` and `>` indistinguishable, destroying the most valuable mutation point in the set |
| **D-23** | **`cost` becomes a real number — owner DE. HTTP routes get written — owner SWE.** | **DE, SWE** | Blocking zone Z4 gains a second real surface once `cost` stops being the constant `0.0`, and 4 of the 8 e2e spine cases become buildable. Until then `defer:cost-dashboard-unowned` stands — but it now has an end date rather than being open-ended |
| **D-24** | **Fix the schemas before Day 20, then write the tests.** Add `recipe_hash` to `Scorecard`; add a partial unique index expressing "one live version" | **AIE-2 (contract), SWE (schema)** | Flows `S2` and `S3` were unbuildable because the schema could not express the question — `Scorecard` carries no version pointer, and `wb.recipes` has no "live" column. `Scorecard` is frozen contract #4, so this needs a **mini-RFC with four signatures**. That is the programme's own "live by the contract" lesson arriving as real work rather than as a slogan |

**None of these is optional, and none of them is a test-writing task.** Three are code or schema changes that
unblock tests; one moves a test between owners. If your guide's cell list seems to disagree with this table,
this table is newer.
