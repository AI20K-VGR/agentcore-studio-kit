# GUIDE D — Interpreter and the refusal surface (Grid E)

**Owner: AIE-1.** Read `00-METHODOLOGY.md` and `01-FOUNDATION.md` first. You do not need the other guides.

This grid covers money-shot step 5: a question whose answer exists only in another tenant's KB must produce
a **refusal, not a fabrication**. It is the smallest grid in the set — 3 live rows — and almost all of the
work is in the mutant cells (§8), not in the rows. That shape is deliberate and §1 explains why.

Every `file:line` below was verified against the pinned baseline (`02-MATRIX.md` §6 names the pinned SHAs:
kit `8a420e7`, `packages/engine` `a65c9d69`, `packages/contracts` `3d7004b2`). Every kill count in §8 was
**re-measured for this guide**, not copied — each mutant was planted, the whole kit suite run, then reverted
(`git status` clean after each). Where a re-measurement disagrees with the round-2 deep dive, this guide
carries the new number and says so.

---

## 1. What this grid is measuring

| Axis | Values | Where the value comes from |
|---|---|---|
| `grounding` | `authorized-match` · `no-match` · `out-of-scope-match` | what the `KbSearch` double hands back to the walk: a chunk that answers the question · nothing · chunks that exist but do not answer it |
| `provider` | `fixtures-stub` · `real-gateway` | which `LLM` / `EmbeddingService` the run is given. `interpreter.run` takes both as keyword arguments (`interpreter.py:109-116` region, dispatch built at `:161-168`), so swapping them touches no product code |

3 × 2 = **6 cells**. After the exclusion rules:

| | count | |
|---|---|---|
| `na:` — impossible, will never be testable | **0** | there is no impossible combination here |
| `todo:` — possible, seam not built yet | **3** | all three `real-gateway` cells, one seam, §3 |
| **real** — buildable against code that exists today | **3** | |
| **rows to write now** (`t=3`, blocking) | **3** | §5 |

Row ids come from the generator (Grid E). Do not renumber them and do not add rows to
that table. The extra cells in this guide carry their own `E-S…` / `E-M…` / `E-P…` ids and are listed in §6–§8.

### 1.1 `answer_shape` is NOT an axis here. It is the oracle column.

This is the single most important design fact about this grid, and an earlier version of it got this wrong.

Grid E used to be `grounding × answer_shape` — 3 × 3 — with `answer_shape ∈ {refuses, answers-from-chunk,
answers-with-no-chunk}`. Read the code that decides `refused`:

```python
retrieved_ids = {chunk.chunk_id for chunk in retrieved_chunks}                        # executors.py:245
citations = [cid for cid in _CITATION_RE.findall(answer) if cid in retrieved_ids]     # executors.py:246
return {
    "answer": answer,
    "tokens": Tokens(prompt=0, completion=0),
    "citations": citations,
    "refused": not citations,                                                         # executors.py:251
}
```

`citations` is the **intersection** of "bracketed in the answer" and "actually retrieved" (`:245-246`), and
`refused` is `not citations` (`:251`). There is no NLP, no sentinel string, no separate refusal branch.

So at `provider=fixtures-stub`, where you supply both the retrieved chunks and the model's answer,
`refused` is a **pure function of the inputs you already control through `grounding`**. `answer_shape` is an
**output**. Making it an axis produces cells that are impossible by construction — `authorized-match ×
refuses` and `no-match × answers-from-chunk` cannot be built, because a chunk cannot be cited unless it was
retrieved. The only way to fill those cells is to hand-construct an `AgentAnswer` (or a `TraceEvent`) double
carrying the flag you want, and then assert the flag you just set. That is not a test of the interpreter. It
is a test of the scorer, wearing the interpreter's cell id.

This is exactly the defect the register's Grid-3 axis correction (§5.1) was created to fix (`verdict` was an output being
used as an axis), reproduced one grid later. The fix, is the same:

- **Here (Grid E):** `grounding` is the sole axis. `answer_shape` is the **oracle column** — the value your
  assertions check, never a value you configure.
- **Grid F (`GUIDE-C-eval-gate.md`, owner AIE-2):** `answer_shape` is a legitimate **input** axis, because
  judging a response is what `score_case` does. Constructed doubles are honest there, and that guide labels
  them as constructed.

If you find yourself building an `AgentAnswer` by hand in this guide, you have wandered into Grid F. Stop and
say so — do not file the result under an `E…` id.

> **§14 CP-1 and CP-2 of the register override everything written before them.** Grid E as three rows plus an
> oracle column is CP-2.2. If you are reading an older document that describes a 32-cell or 18-row Grid 5,
> that document is superseded.

---

## 2. `na:` rules — there are none, and that is worth one sentence

No combination of `grounding × provider` is structurally impossible. A grid with zero `na:` cells is normal;
it means the axis values were chosen so that each one is reachable. Do not invent an `na:` to shrink the work
— a cell marked `na:` without a rule id counts as `unknown`, which blocks (methodology §4).

---

## 3. `todo:` cells — 3, one seam, and it is not yours

| Seam id | Cells | What has to exist | Owner | ETA |
|---|---|---|---|---|
| `todo:embedding-gateway` | 3 (every `real-gateway` cell) | a gateway `LLM` / `EmbeddingService` reachable from CI | not AIE-1 alone — needs `STUDIO_GEMINI_API_KEY` + network policy | see §11 Q-E5 |

Per register §14 CP-2.7 the `real-gateway` column collapses to a small number of **pilot** cells across the
whole set rather than a full column. Grid E's share is **one** pilot row, `E-P1` (§8.3). The other two
`real-gateway` cells stay in the inventory as `todo:embedding-gateway` and are not separate rows.

There is a measured reason the pilot needs care rather than enthusiasm.
`GeminiProvider.complete` discards its `kwargs` (`apps/studio/src/studio_app/providers/gemini.py`, and
`executors.py:231-235` documents it in a comment: *"`GeminiProvider.complete` also discards kwargs, using its
own `self._model` instead"*). `interpreter.py:233` threads `recipe.agent_config.model` into
`node.params["model"]`, `executors.py:236-237` forwards it into `kwargs["model"]` — and the gateway drops it.
So a recipe declaring one model can run against another, silently. `[UNVERIFIED]` by a live call: no API key
and no network path in this environment; the claim is read from `gemini.py` and from the comment at
`executors.py:231-235`, not from a real request.

Until `E-P1` exists, this grid's `provider` axis takes exactly **one** value in the live row set. An axis with
one live value contributes **zero discrimination** — it is honest bookkeeping about what is untested, not
coverage. Say that out loud in your report rather than presenting 3 of 6 as "50% covered".

---

## 4. Things you must know before writing a single test

Four measured facts about the current tree. Each one changes what a correct test looks like. None of them is
a matter of opinion; each was run.

### 4.1 `registry.REGISTRY` is not the dispatch table

`registry.py:1-2` opens with: *"Node-type → executor-class registry — the **ONLY** place `NodeType` maps to a
concrete executor."* That sentence is false.

The table the interpreter actually dispatches through is built **inline** in `interpreter.run` —
`interpreter.py:161-168` — and looked up at `interpreter.py:237` (`await executors[node_type].execute(node)`).
`REGISTRY` (`registry.py:27-34`) is a second, parallel dict. Measured: `grep -rn "REGISTRY|get_executor_class"`
over `packages`, `apps`, `tests` returns **7 hits, none of them a product-code consumer** — the definition
itself, the re-export at `__init__.py:20`, two `__all__` entries (`:23`, `:32`), and
`test_node_type_closed.py`. Nothing in the running system reads `REGISTRY`.

Consequence, measured both ways:

- deleting `NodeType.CONDITION` from `registry.py:30` ⇒ **1 test red** (`test_node_type_closed.py::test_registry_has_exactly_six`)
- deleting the same key from the real table at `interpreter.py:165` ⇒ **0 tests red**; the suite reports its
  full baseline unchanged

`test_node_type_closed.py::test_registry_has_exactly_six` (`:16-21`) is therefore locking a **copy**. Its
load-bearing line is `:21` (`len(REGISTRY) == 6`) — `:20` alone (`set(REGISTRY.keys()) == set(NodeType)`)
compares the two sides to each other and stays green if someone adds a seventh value to both.

The 6-node cap is not what breaks here. §4.4 shows the cap is genuinely enforced. What breaks is dispatch: a
missing key in the real table raises `KeyError(<NodeType.X>)` **when a customer's recipe runs**, not in CI.
Loud, but late. Cell `E-M1` exists for this.

### 4.2 `Edge.when` is a dead field

`Edge.when` is declared at `recipe.py:45` (`when: str | None = None`) and read by **no line of product code**.
Measured: `grep -rn "\.when\b"` over `packages`, `apps`, `tests` returns only docstrings
(`interpreter.py:10`, `:79`; `executors.py:256`; `packages/kb/src/studio_kb/trace_reader.py:58`, `:104`) and
one test docstring.

Probe, run for this guide against the pinned tree: a two-node recipe `n1(llm-step) → n2(end)` whose **only**
edge carries `when="1 == 2"` walks **both** nodes and emits both trace events. No exception, no warning, no
log line, nothing in the trace recording that a condition was ignored.

`_build_next_map` (`interpreter.py:77-90`) reads `edge.from_` and `edge.to` and drops `edge.when` on the
floor. The `raise` at `:85-88` only fires when a node has **more than one** outgoing edge; at out-degree 1 the
condition evaporates in silence. A recipe author who writes `when: "verdict == 'PASS'"` to gate a dangerous
branch gets that branch executed unconditionally.

Compare with `ConditionExecutor`, which is still `NotImplementedError` (§4.4): the stub **breaks loudly**.
`Edge.when` does not break at all. Silent is worse than absent. Cell `E-M7` covers it, and it is blocked on
an open question (§11 Q-E6) because "reject the recipe" and "evaluate the condition" are different features.

### 4.3 The monotonic-`ts` guard is dead code — and this is the one mandatory test in the guide

`interpreter.py:262-265`:

```python
now = datetime.now(UTC)
if last_ts is not None and now <= last_ts:      # :263
    now = last_ts + timedelta(microseconds=1)   # :264
last_ts = now
```

The invariant it defends is declared in the contract: `trace.py:33` — `ts: str  # iso8601, monotonic within a
run`.

Measured: real per-node `ts` deltas on this tree are **10–156 µs**, against a comparison that only triggers at
**≤ 1 µs**. Wall-clock resolution does the guard's job for it, so the guard never executes. Re-measured for
this guide: **removing the guard turns 0 tests red** (full suite, baseline unchanged). Not "flaky" — the
mutant survives deterministically.

The test that watches the invariant today, `test_trace_event_emission.py:111-117`, asserts
`timestamps == sorted(timestamps)` (`:116`) and that all four are distinct (`:117`). Both hold whether the
guard is present or not.

**The seam that makes this killable exists.** `interpreter.py:33` does `from datetime import UTC, datetime,
timedelta`, which binds the name `datetime` **in the interpreter module**, so
`monkeypatch.setattr(interpreter, "datetime", <a frozen stand-in>)` replaces the clock the guard reads.
Probed for this guide, both ways:

| | guard present | guard removed |
|---|---|---|
| real clock | 2 distinct `ts` | 2 distinct `ts` — mutant survives |
| **frozen clock** | **2 distinct `ts`, exactly 1 µs apart** | **1 distinct `ts` — mutant dies** |

That is the whole cell. **`E-M4` is mandatory.** Without it, blocking zone 4 keeps a permanent hole that no
amount of other work fills.

> **Corollary, and it applies to every cell you write:** `assert ts == sorted(ts)` on **interpreter output**
> is a **tautology** — though not for the reason an earlier draft gave. `:263-264` does **not** force
> monotonicity: its branch never executes, because natural deltas are ~10× the 1 µs it compares. The ordering
> is monotonic because the clock already is. Either way the assertion is true by construction and
> would stay true if every timestamp were wrong. It is a false green in the exact sense
> `packages/kb/tests/test_pg_kb.py` names **"xanh giả"**. Ordering evidence about *stored* trace rows belongs
> to Grid D (owner DE) and must go through `trace_reader`, not through the interpreter.

### 4.4 Two executors are still stubs — and the 6-node cap is enforced at runtime, not just by mypy

`ConditionExecutor.execute` raises at `executors.py:261-262`; `HitlPauseExecutor.execute` raises at
`executors.py:316-317`. Both messages carry a spec label. That is correct stub behaviour: a recipe routed
through either node **breaks loudly**, which is why §4.2's silence is the more dangerous of the two.

On the cap itself, the enforcement is real and it is at **runtime**, not only in the type checker.
`NodeType` is a `StrEnum` with exactly six members (`nodes.py:16-24`), carried on `Node.type`
(`recipe.py:32`), and `Node` is a pydantic model. So a seventh value is rejected at
`Dag.model_validate` / `Node(...)` construction — before the recipe reaches the workbench validator, and long
before it reaches the interpreter. Two probes (round-2 deep dive §2.2, re-read here against the same SHAs)
show a `pydantic.ValidationError` at `nodes.0.type` for both the direct-construction and the dict-load path.

Two consequences for how you spend your time:

1. "A node outside the six types" is an **easy** cell, not a dangerous one. It already has a real wall.
2. The wall is at the pydantic boundary, so it only holds for recipes that **pass through** that boundary. A
   future loader that reads YAML and picks `node["type"]` out by hand would bypass it, and **no current test
   would notice** — every existing test constructs `Node(...)` through pydantic. That is mutation point
   `M-I-16`, unanchorable today because `packages/engine` has no file-based recipe loader at all. It stays in
   the inventory as `[UNVERIFIED]` with the note *"needs seam: recipe file loader"*.

---

## 5. The 3 rows

Zone column: **Z1** = cross-tenant / cross-role leakage · **Z4** = cost lineage and trace ordering. Both are
blocking. Target band is the band a complete cell **can** reach, not a promise — and read §8.4 before you set
your expectations, because this surface is currently capped.

| id | `grounding` | `provider` | Zone | Target | §  |
|---|---|---|---|---|---|
| E01 | authorized-match | fixtures-stub | — | MEDIUM | 5.1 |
| E02 | no-match | fixtures-stub | Z1 | HIGH | 5.2 |
| E03 | out-of-scope-match | fixtures-stub | **Z1** | HIGH | 5.3 |

**E01 is not the easy row you skip.** E02 and E03 are both **empty-expected cells**: the correct outcome is an
empty citation list. Methodology §7.1 exists for precisely this shape, and it was written about the fence —
but it applies here word for word. `assert citations == []` (or `refused is True`) goes green against a
`KbSearch` double that never got called, a walk that never reached `llm-step`, an `LLM` double that returned
the empty string, and a working derivation. Only the paired positive control tells them apart, and E01 **is**
that control.

### 5.1 E01 — `authorized-match` (the positive control)

**Must prove:** when retrieval hands back a chunk that answers the question and the model cites it, the run is
**not** flagged as a refusal, and the citation that survives is the retrieved one.

```
REQUIRED
  [1] INCLUSION — the citation list is non-empty and contains the id of a chunk
      the KbSearch double actually returned
  [2] the refusal flag reads "did not refuse"
  [3] the assertions read the value the WALK produced (through interpreter.run),
      not the LlmStepExecutor called directly — at least one of E01..E03 must
      go through the walk, and E01 is the cheapest place to do it
  [4] the same double is reused, unchanged, by E02/E03 as their control

DERIVED BAND
  [1]+[2]        ⇒ MEDIUM
  [1]+[2]+[3]    ⇒ MEDIUM (this row is not in a blocking zone; MEDIUM is its ceiling)
  missing [1]    ⇒ unknown, and E02/E03 drop to unknown with it
```

E01 has no HIGH band because it is not in a blocking zone. It is in the set anyway, for the same structural
reason the two `same`-tenant control rows are in `GUIDE-A`: without it, every empty-expected assertion in this grid is satisfiable by
a component that does nothing.

### 5.2 E02 — `no-match` (Z1, blocking, empty-expected)

**Must prove:** when retrieval returns nothing, nothing is citable, the run is flagged as a refusal — **and a
bracketed id the model invented does not buy its way out of that branch.**

```
REQUIRED
  [1] EXCLUSION — the citation list is empty
  [2] the refusal flag reads "refused"
  [3] PAIRED POSITIVE CONTROL — E01's cell, same corpus shape, same doubles,
      differing only in what retrieval returned (methodology §7.1(a))
  [4] a SECOND sub-case in the same cell: the model's answer brackets an id
      that was never retrieved. The bracketed id must NOT appear in the
      citation list, and the run must still read as a refusal
  [5] mutation evidence: M-I-1 and M-I-1b killed (§8.2)

DERIVED BAND
  all of [1..5]     ⇒ HIGH
  missing [5]       ⇒ MEDIUM
  missing [3] or [4]⇒ unknown, NOT low
```

Requirement [4] is what separates this cell from a shape that measures nothing. Assertion [1] alone is also
true of an `LLM` double that returned an empty string, and of a citation extractor that was never called.
Sub-case [4] can only pass if the intersection at `executors.py:246` is really being computed.

> **Requirement [5] names `M-I-1b` and not `M-I-1c`, and the reason is measured.** Reverting the derivation to
> the retired signal (`refused = not retrieved_chunks`, mutant `M-I-1c`) leaves this cell **green** — with
> nothing retrieved, both the old and the new signal say "refused". Re-measured for this guide: `M-I-1c` turns
> 3 tests red and **none of them is the `no-match` shape**. E02 cannot kill it. E03 can. Do not claim `M-I-1c`
> kill evidence from this row.

### 5.3 E03 — `out-of-scope-match` (Z1, blocking, and the row that carries the grid)

**Must prove:** when retrieval **does** return chunks but none of them answers the question, the run is still
flagged as a refusal. This is the case where the retired signal and the shipped one disagree, and it is the
engine-level shape of a cross-tenant attempt: the answer is only available in another tenant's KB, the fence
dropped those chunks, and retrieval handed back unrelated in-tenant chunks instead.

```
REQUIRED
  [1] the retrieval double returns a NON-EMPTY list, and the test asserts it is
      non-empty. If the list is empty this is E02 wearing E03's id
  [2] EXCLUSION — the citation list is empty
  [3] the refusal flag reads "refused"
  [4] PAIRED POSITIVE CONTROL — E01, as in §5.2 [3]
  [5] a sub-case where the answer brackets an id belonging to a DIFFERENT
      tenant than the one whose chunks were retrieved: the id must not become
      a citation, and the run must still read as a refusal
  [6] mutation evidence: M-I-1c killed — the mutant only THIS row can kill —
      plus M-I-1 and M-I-1b (§8.2)

DERIVED BAND
  all of [1..6]        ⇒ HIGH
  missing [6]'s M-I-1c ⇒ MEDIUM, and record that the retired signal is unguarded
  missing [1] or [4]   ⇒ unknown, NOT low
```

### 5.4 What all three rows prove, and the sentence you must not let them imply

The refusal flag says **"nothing could be cited"**. It does not say **"the answer contains no other tenant's
data"**. An answer that fabricates a complete cross-tenant figure and simply **omits the brackets** produces
an empty citation list and therefore reads as a refusal.

This is not a new finding and it is not a bug you should fix here. It is a documented limitation of the
derivation, recorded in the code itself (`executors.py:240-244` explains why raw extraction was rejected) and
measured independently by DE in `packages/kb/tests/test_spine_live.py`, which states outright that its own
case *"KHÔNG chứng minh nhánh từ chối đúng — nó chỉ chốt hành vi hiện hành"* (this test does not prove the
refusal branch is right; it pins current behaviour).

What is required of you: **do not write an assertion, a docstring, or a report line that claims these rows
prove "does not fabricate".** They prove "does not fabricate **a citation**". The gap between the two belongs
to Grid F (`GUIDE-C-eval-gate.md`, the `no_leak` check over answer text) and to the `E-P1` pilot. Claiming
more than the assertion supports is the single most expensive error available on this surface, because it
closes an open question by assertion rather than by evidence.

---

## 6. `E-S1` — refusal **+ audit**, and the trap sitting inside it

The hard AC is two halves. `docs/requirements/00-orientation/umbrella-contract.md:71`: a question whose answer
exists only in Tenant-Y's KB, asked while scoped to Tenant-X, must produce **`refusal + audit`**, not a
hallucination. §5 covers the `refusal` half. This section is the `audit` half, and it opens with a warning
because the obvious way to build it is a false green.

### 6.1 The trap: `refused` is already in the trace, so "an audit row exists" needs zero new behaviour

Measured end to end on the pinned tree, by running a three-node recipe and inspecting what the trace writer
received:

- the executor's dict becomes the event's `outputs` (`interpreter.py:250-260`, assigned at `:276`), so the
  `llm-step` event's `outputs` already carries the keys `answer`, `citations`, `refused`, `tokens`
- `PgTraceWriter` writes it as JSONB (`apps/studio/src/studio_app/obs/trace_writer.py:41`,
  `Jsonb(event.outputs)`) into `obs.trace_events.outputs JSONB NOT NULL`
  (`apps/studio/src/studio_app/obs/schema.py:28`)

So `outputs->>'refused' = 'true'` is already a working query today. A trainee can satisfy *"a refusal audit row
exists"* by issuing any query that matches nothing and asserting the flag — **green, with not one line of new
behaviour, while the actual AC is untouched.** Register §14 CP-2.4 #3 names this shape; this is where it lands.

Two further measurements sharpen how empty the trace half currently is:

- the **only** place in the entire kit that reads `outputs["refused"]` off a trace event is
  `packages/kb/tests/test_spine_live.py:238` — and it needs the `pool` fixture, so it sits inside the 51
  DB-gated skips (register H4). On an AIE-1 machine, **zero** tests watch the trace half.
- `test_refusal_from_grounding.py` runs its five golden cases through the real walk but hands
  `interpreter.run` a `_NoOpTraceWriter` (`:77-79`, used at `:229`) that **discards every event**. Ten
  refusal cases, and not one assertion about a trace.

### 6.2 What `E-S1` must prove instead: the causal chain

Not "a flag exists somewhere". The chain, in order, in one test:

```
REQUIRED — cell E-S1  (Z1, blocking; seam: todo:refusal-reason)
  [1] CAUSE — the retrieval double returns a set of chunks from which the
      answer-bearing chunk has been REMOVED, standing in for the fence having
      dropped it. The test must assert what the double returned, so the cause
      is on the record and not just in a docstring
  [2] EFFECT 1 — the run reads as a refusal
  [3] EFFECT 2 — a `reason` accompanies it, drawn from the closed enum in
      rider 2 below
  [4] EFFECT 3 — the refusing run's TRACE carries no citation. Assert this on
      the event captured by a recording trace-writer double, NOT on the value
      returned from `run()`. The two are different objects and only one of them
      is the audit
  [5] CARRIER — exactly one event in the run carries the refusal keys
      (rider 1 below). Assert the count, not just the presence
  [6] mutation evidence: M-I-1b killed AT THE TRACE ASSERTION — that is,
      the line that goes red must be [4] or [5], not a final-state line.
      If only the final-state assertion reddens, the audit half is unguarded
      and the cell caps at MEDIUM

DERIVED BAND
  all of [1..6]      ⇒ HIGH
  missing [6]        ⇒ MEDIUM
  missing [1] or [4] ⇒ unknown — [1] without [4] is the trap in §6.1, and
                        [4] without [1] is an assertion about a value the test
                        itself set
```

Requirement [1] is the reason this cell is not simply E02 again. E02 varies `grounding`; `E-S1` asserts that a
specific **cause** produced the refusal. Requirement [4] is the reason it is not the §6.1 trap.

### 6.3 The shape of `audit` is decided: register `D-20`, with three riders

You do not get to choose the shape, and you do not have to invent it. Register `D-20` rules it:

> **the audit is an `obs.trace_events` row whose `outputs` records the refusal** — e.g.
> `outputs = {"refused": true, "reason": "no_authorized_chunks"}`.

**No schema change. No contract change.** `TraceEvent.outputs` is `dict[str, object]` (`trace.py:35`) and is
free-form under frozen contract #2; the column already exists (`obs/schema.py:28`); the writer already
serialises it (`trace_writer.py:41`). A dedicated `obs.refusals` table was considered and rejected — it adds a
schema to the most heavily loaded owner — and log-only was rejected because it is not machine-checkable, so it
cannot support `leakage = 0` as something provable.

Three riders come with it. All three are testable, and all three are yours to assert:

1. **Pin the carrier.** **Exactly one** event per run carries the refusal keys — the `llm-step` event. Without
   this rule, "did this run refuse?" becomes "scan every event and decide what contradictory flags mean". Your
   cell asserts the count is one, which is why §6.2 [5] exists.
2. **`reason` is a small closed enum**, not free text: `no_authorized_chunks` | `no_match` | `judge_descope`.
   Free text is unqueryable variety, and an audit you cannot query is a log. Measured: none of these three
   strings appears anywhere in the tree today (`grep` over `packages`, `apps`, `docs` ⇒ 0 hits), and no product
   line writes a `"reason"` key at all (`grep '"reason"'` over `packages`, `apps` ⇒ 0 hits). So `reason` is the
   **only** genuinely new behaviour in this cell — which is exactly why the cell is worth writing and why it
   carries seam id `todo:refusal-reason`. That seam is AIE-1-owned and needs nobody's signature, because it
   adds a key to a free-form object.
3. **The audit inherits H22.** `obs.trace_events` has **no RLS**. Verified: the only table in the kit carrying
   `ENABLE ROW LEVEL SECURITY` is `kb.chunks` (`packages/kb/src/studio_kb/schema.py:52-53`), and the
   `obs.trace_events` DDL (`obs/schema.py:19-32`) carries no policy at all. So the audit trail — a record of
   cross-tenant **attempts** — is itself **cross-tenant-readable**. This is not a new exposure, since trace
   already stores chunk content, but it means the audit half of a hard AC currently rests on the leakiest table
   in the system. **Your cell must name RLS-on-`obs` as a dependency in its docstring.** Naming it is the
   deliverable; fixing it is DE's table and not your row.

---

## 7. `E-S2` — the distinction the interpreter cannot currently make

**"Refused because the fence blocked it"** and **"refused because the KB was empty"** arrive at `llm-step` as
the same thing: `node.params["retrieved_chunks"] == []`.

Verified, three ways, and the answer is that the seam does not exist:

- both paths enter through the same parameter, read at `executors.py:213`. The executor has no way to learn
  where the empty list came from
- the `KbSearch` contract returns `list[KbSearchResultItem]` (`packages/contracts/src/studio_contracts/kb.py:36-42`)
  — no `filtered_out_count`, no outcome object, no reason. `KbRetrieveExecutor.execute` returns that list
  unchanged (`executors.py:141`)
- the `kb-retrieve` event's `outputs` is `{"chunks": [...]}` and nothing else
  (`interpreter.py:243-246`). Empty is empty

The consequence is stated plainly because it is a security-versus-data-quality distinction and the two must not
be graded the same. In the current suite, `test_refusal_from_grounding.py:114-120` is labelled *"SC-05's shape:
the role fence emptied retrieval outright"* — and its body calls the executor with an empty list, with **no
tenant, no role, and no fence anywhere in the test**. The label lives in the docstring. No assertion carries
it. **A completely broken fence stays green as long as retrieval returns empty.**

```
REQUIRED — cell E-S2  (Z1, blocking; seam: DOES NOT EXIST — see below)
  [1] two runs, identical in every respect except the CAUSE of the empty
      retrieval: one where the fence removed the chunks, one where the corpus
      never held them
  [2] an assertion that distinguishes the two — on the trace, on the refusal
      `reason`, or on retrieval metadata
  [3] the assertion must fail if the two causes were swapped

DERIVED BAND
  the seam does not exist ⇒ this cell is `todo:`, and it BLOCKS as a feature,
  not as a test gap. Do not fill it with a docstring label.
```

**Flagging this as required, per the guide's own rule.** [2] cannot be written today. There is no seam. Two
options exist and they belong to different owners:

| Option | What changes | Owner | Cost |
|---|---|---|---|
| **A** | `KbSearch.search` returns retrieval metadata (a count of chunks the fence removed, or a `RetrievalOutcome{items, filtered_out_count, reason}`) | **DE** — this is frozen contract #3 | **mini-RFC + 4/4 signatures** (`umbrella-contract.md` §3) |
| **B** | the `kb-retrieve` event's `outputs` gains `roles_requested` / `roles_effective` alongside `chunks`, so Grid A and Grid E have something to compare | **AIE-1 (you)** — the change is at `interpreter.py:243-246` | no signature; `outputs` is free-form |

Option B is cheaper and does not touch a contract, but it only distinguishes the two causes if something
resolves roles server-side to compare against — which is open question Q2 in `GUIDE-A`. Write the cell as
`todo:`, name both options, and take the decision to the mentor. Do not pick A on your own; it is not your
contract.

Until this seam lands, `E-S1`'s `reason` enum is the closest available proxy: `no_authorized_chunks` versus
`no_match` is exactly this distinction, expressed as a value the writer chooses rather than a fact the system
observed. That is weaker than a measurement and the difference must be written down in the cell, or the enum
becomes a place to record a guess and call it evidence.

---

## 8. Mutant family `M-I` — 23 points, and only 8 of them are your job

Procedure for every mutant, without exception: plant it, run the named test, record **which assertion line
went red**, remove it, confirm the tree is clean. Red on a line you did not expect is itself a finding — write
it down rather than adjusting the expectation.

All counts below were **re-measured for this guide** on the pinned baseline
(`203 passed · 51 skipped · 2 xfailed · 3 xpassed · 1 failed` — the one failure is
`tests/test_workspace.py::test_import_linter_passes`, a missing `lint-imports` binary, an environment fault
and not a regression; it is excluded from every count). 22 of the 23 points are anchored to a `file:line` that
exists today.

### 8.1 The 14 already-killed points — a RECORDED TABLE, not work

Per register §14 CP-2.7 and the review's cut list, these fourteen points are **already guarded by the existing
suite**. You do not write new tests for them. When a cell needs one of these as evidence, you **cite the
existing test and the measurement below**; you do not re-derive it.

| Mutant | `file:line` | What changes | Red (re-measured) | Kill sits in |
|---|---|---|---|---|
| `M-I-1` | `executors.py:246` | drop the `if cid in retrieved_ids` filter — ungrounded brackets become citations | **6** | E02 [5], E03 [6] |
| `M-I-1b` | `executors.py:251` | `"refused"` hardcoded false | **7** | E02 [5], E03 [6], `E-S1` [6] |
| `M-I-1c` | `executors.py:251` | revert to the retired signal `not retrieved_chunks` | **3** | **E03 [6] only** — see §5.2's note |
| `M-I-2a` | `registry.py:30` | remove a key from `REGISTRY` (the copy) | **1** | recorded only; the real table is `E-M1` |
| `M-I-3a` | `interpreter.py:84-88` | out-degree > 1 no longer raises (last-edge-wins) | **1** | Grid B (`recipe_validity`), owner SWE |
| `M-I-3b` | `interpreter.py:202-206` | cycle guard no longer raises | **2** | Grid B |
| `M-I-3c` | `interpreter.py:72` | accept > 1 start node, take the first | **1** | Grid B |
| `M-I-4` | `demo_stubs.py:98` | `StubEmbedding` returns a constant vector | **1** | §9, and Q-E2 |
| `M-I-10` | `interpreter.py:273` | every event's `node_type` is `END` | **1** | Grid D (trace identity) |
| `M-I-11` | `interpreter.py:281-282` | drop the `kb-retrieve` event from the trace | **7** | Grid D (`trace_state = missing event`) |
| `M-I-12` | `executors.py:305` | `tool-call` bypasses the dispatcher (no whitelist) | **1** | Grid B (`tool-outside-whitelist`) |
| `M-I-13` | `executors.py:48-49` | remove the "do not cite if the excerpts do not answer" line from the prompt | **1** | recorded |
| `M-I-14` | `executors.py:226` | build the prompt without the retrieved chunks | **2** | recorded |
| `M-I-15` | `interpreter.py:219` | stop threading `recipe.tenant_id` into `kb-retrieve` | **1** | Grid A cross-reference |

**Two corrections to the round-2 deep dive, from re-measurement:**

1. **`M-I-3c` turns 1 test red, not 2.** The deep dive listed both
   `test_zero_start_candidates_raises_value_error` and `test_multiple_start_candidates_raises_value_error`. Only
   the second reddens. The mutant as specified (`if not starts: raise`, then `return starts[0]`) still rejects
   the zero-start case, so the zero-start test is **correctly** green. The verdict (KILLED) is unchanged; the
   count is 1.
2. **`M-I-11`'s true detection is 8, of which 1 is silently discarded.** Seven tests go red. An eighth,
   `packages/workbench/tests/test_wiring_d5.py::test_workbench_recipe_emits_trace_events_via_interpreter`,
   XPASSes at baseline and flips to XFAIL under the mutant — it **detects** the mutation, and its
   `xfail(strict=False)` marker converts the detection into a non-failure. This is register H3 with a price
   tag: a stale `xfail` on this surface is not just an unread signal, it is a **mutation-kill absorber**.
   `test_wiring_d5` is also the only case in the kit watching trace ordering plus `ts`, which is blocking
   zone 4. Report it; do not remove someone else's marker (it is SWE's file).

### 8.2 The 8 open points — this is the assignment

Seven mutants survive the whole suite. One needs no mutant, because the code already does the wrong thing.
Each one gets a cell.

| Mutant | `file:line` | What changes | Red (re-measured) | Cell | Zone |
|---|---|---|---|---|---|
| `M-I-2b` | `interpreter.py:165` | remove `NodeType.CONDITION` from the **real** dispatch table | **0** | `E-M1` | — |
| `M-I-5` | `executors.py:139` | widen `section_roles` — append roles the node never declared | **0** | `E-M2` | **Z1** |
| `M-I-5b` | `executors.py:139` | erase `section_roles` entirely (maximum over-scope) | **0** | `E-M2` | **Z1** |
| `M-I-6` | `executors.py:140` | ignore the declared `top_k`, fetch wide | **0** | `E-M3` | **Z1** |
| `M-I-7` | `interpreter.py:263-264` | remove the monotonic-`ts` guard | **0** | `E-M4` **(mandatory)** | **Z4** |
| `M-I-8` | `interpreter.py:63` | `cost` is no longer the trace's number | **0** | `E-M5` | **Z4** |
| `M-I-9` | `interpreter.py:275` | `inputs_hash` becomes a constant | **0** | `E-M6` | — |
| `M-I-3d` | `recipe.py:45` | **no mutant needed** — `Edge.when` is already ignored (§4.2) | — | `E-M7` | — |
| `M-I-16` | — | a recipe loader that bypasses `Dag.model_validate` | `[UNVERIFIED]` | inventory only | — |

`M-I-16` stays in the inventory and gets no cell: `packages/engine` has no file-based recipe loader, so there
is nothing to plant a mutant into. Recording it costs nothing and stops the §4.4 wall from being assumed
permanent.

#### `E-M1` — the real dispatch table covers all six node types

**Must prove:** the dict the interpreter actually dispatches through is complete — not that a parallel copy is.

```
REQUIRED
  [1] the assertion must reach interpreter.py:161-168, not registry.REGISTRY.
      A test importing REGISTRY does not qualify, however it is worded
  [2] the failure must surface at TEST time. Today a missing key surfaces as
      KeyError when a recipe runs — see §4.1
  [3] mutation evidence: M-I-2b killed, with the red line named
  [4] state in the docstring that test_node_type_closed.py::test_registry_has_exactly_six
      guards the copy, so a reader does not treat the two as redundant

DERIVED BAND
  [1]+[2]+[3]  ⇒ HIGH
  missing [3]  ⇒ MEDIUM
  missing [1]  ⇒ unknown — this is the whole point of the cell
```

Note the constraint you will hit: the dict is a **local variable** inside `run()`, so there is no public
handle on it. Reaching it means either driving a recipe through each node type and observing dispatch, or
proposing a small refactor that lifts the table to module scope where both the interpreter and a test can see
it. The refactor is inside your own file and needs nobody's signature — but if you take that route, say so
explicitly, because it changes `registry.py`'s docstring claim from false to true and that is a decision, not
a cleanup.

#### `E-M2` — the fence-EXECUTOR does not widen or erase `section_roles` (Z1, blocking)

**Must prove:** the roles that reach `KbSearch.search` are the roles the run was entitled to — neither widened
nor emptied on the executor side.

This is the most serious open point on the surface. `KbRetrieveExecutor`'s own docstring states the duty three
times (`executors.py:95-107`): roles must be resolved **server-side** and passed **unchanged**; a
client-declared override must be **ignored**; widening is *"exactly the T6 label-spoof this fence exists to
stop"*. Measured against that: **no test anywhere touches `section_roles`**, and both mutants survive the full
suite.

Probed for this guide: a `kb-retrieve` node declaring `section_roles=["public", "admin"]` and `top_k=9999`
reaches `KbSearch.search` with exactly `(["public", "admin"], 9999)`. A recipe that declares itself `admin`
goes straight through to the retrieval layer.

```
REQUIRED
  [1] a recording KbSearch double that CAPTURES the roles argument. A double
      that discards it cannot support this cell, and most existing doubles in
      packages/engine/tests discard it on their first line
  [2] the double must REACT to the roles it is given — return a chunk only when
      a role the run does not hold is present. A double that returns the same
      list whatever it is handed makes [3] a bookkeeping check rather than a
      fence check (GUIDE-A §6.4 [3], same rule)
  [3] an EXACT-EQUALITY assertion on the captured roles. Exact equality reddens
      under both widening and erasing; a subset or `in` assertion catches only
      one of the two, so the operator here is load-bearing
  [4] an EXCLUSION assertion on the RESULT: the chunk that only a widened role
      set could reach is absent
  [5] mutation evidence: BOTH M-I-5 and M-I-5b killed, with the red line named
      for each
  [6] the docstring must state which layer this cell does NOT cover: fence-DATA
      (RLS at retrieval) is DE's, in Grid A

DERIVED BAND
  all of [1..6]      ⇒ HIGH
  missing [5] partly ⇒ MEDIUM
  missing [1] or [2] ⇒ unknown
```

> **This cell is blocked on an open question and you must not resolve it by writing a test.** Whether
> `section_roles` is resolved server-side at all is `GUIDE-A` Q2, unanswered. `executors.py:128-131` says
> outright that *"Day 3 has no real server-side session/tenant context to resolve `section_roles` from"*. So
> the assertion "roles were passed unchanged" is buildable today, and the assertion "roles came from the
> session, not the recipe" is not. Write the first, mark the second `todo:`, and name the question. Asserting
> that the current pass-through behaviour is *correct* would pin the hole in place — the `KHÓA` pattern applied
> to a bug (methodology §7.2, and see §10).

#### `E-M3` — the declared `top_k` is honoured (Z1, blocking)

**Must prove:** the executor does not fetch wide and filter afterwards.

`executors.py:100-103` names over-fetching as the umbrella contract's explicitly forbidden anti-pattern
(retrieve broadly, then ask the model not to mention things). `M-I-6` breaks it and survives.

```
REQUIRED
  [1] a recording KbSearch double capturing the top_k argument
  [2] an assertion on the captured value
  [3] the declared value must be small enough that a widened fetch is
      distinguishable from it
  [4] mutation evidence: M-I-6 killed

DERIVED BAND
  all of [1..4]  ⇒ HIGH   ·   missing [4] ⇒ MEDIUM   ·   missing [1] ⇒ unknown
```

`E-M2` and `E-M3` share one double and can share one test, provided each assertion is separately identifiable
so the mutant map can name which line reddens for which mutant.

#### `E-M4` — the monotonic-`ts` guard, under an injected clock (Z4, blocking) — **MANDATORY**

**Must prove:** the guard at `interpreter.py:263-264` does something. Today nothing proves it (§4.3).

```
REQUIRED
  [1] the clock must be REPLACED, not observed. Use
      monkeypatch.setattr(interpreter, "datetime", <frozen stand-in>) — this
      works because interpreter.py:33 binds the name in the module
  [2] under the frozen clock, assert that consecutive events do NOT share a
      timestamp. With the guard in place they differ by the smallest step the
      guard applies; with it removed they are identical
  [3] a second case where the stand-in clock moves BACKWARDS between nodes
  [4] mutation evidence: M-I-7 killed. This is non-negotiable — a cell that
      cannot kill M-I-7 has not tested the guard, whatever else it asserts
  [5] the cell must NOT assert `ts == sorted(ts)` on interpreter output as its
      evidence. That is the tautology in §4.3

DERIVED BAND
  all of [1..5]  ⇒ HIGH
  missing [4]    ⇒ unknown, NOT medium. This is the one cell in the guide where
                   the mutant IS the cell — without the kill there is no
                   observable difference between guard and no guard
```

The seam was probed for this guide and works in both directions (§4.3's table). You are not being asked to
build something speculative.

#### `E-M5` — `cost` on the event is the trace's number (Z4, blocking)

**Must prove:** the number on the event comes from the run, not from a module constant.

`interpreter.py:63` defines `_NO_COST = 0.0` and `:278` assigns `cost=_NO_COST`. Changing the constant turns
**0** tests red in the whole non-DB suite. The kit's only cost assertion lives in
`apps/studio/tests/test_trace_writer.py` and is inside the 51 DB-gated skips, so on your machine nothing
enforces it.

```
REQUIRED
  [1] an assertion on the cost carried by the emitted event
  [2] the assertion must distinguish "the value the run computed" from "the
      module constant". Pinning the constant's current value satisfies neither
  [3] mutation evidence: M-I-8 killed
  [4] if [2] is not yet possible, the cell is `todo:` with the seam named

DERIVED BAND
  all of [1..3]  ⇒ HIGH
  [1]+[3] only   ⇒ MEDIUM, and record that the number is still a constant
  [1] only       ⇒ unknown — a pin on 0.0 is constant-versus-constant (§9)
```

Be honest about the ceiling here. While `cost` is a constant, the three-surface cost invariant that blocking
zone 4 exists to protect holds **trivially** — all surfaces agree because there is one number and it is
hardcoded. Register Q2 (who makes `cost` real, and when) is unanswered, and register §14 CP-2.3 re-scoped zone
4 partly because of it. Your cell can prove the plumbing carries a number; it cannot prove the number is right.
Say which one you proved.

#### `E-M6` — `inputs_hash` is derived from the inputs

**Must prove:** `inputs_hash` changes when the node's params change, and is stable when they do not.

`interpreter.py:275` computes a sha256 over `node.params`. Replacing it with a constant survives the suite.
`inputs_hash` is the only field that supports "same inputs ⇒ same run", so constant-ising it destroys
traceability invisibly.

```
REQUIRED
  [1] two runs whose node params DIFFER ⇒ the hashes differ
  [2] two runs whose node params are IDENTICAL ⇒ the hashes match
  [3] mutation evidence: M-I-9 killed — note that [2] alone stays green under
      the constant mutant, so [1] is the load-bearing half

DERIVED BAND
  [1]+[2]+[3]  ⇒ HIGH   ·   missing [3] ⇒ MEDIUM   ·   [2] only ⇒ unknown
```

Requirement [2] on its own is the same tautology class as `test_stub_embedding_is_deterministic` (§9): a
constant is perfectly stable.

#### `E-M7` — `Edge.when` does not vanish silently

**Must prove:** a recipe that declares a condition on an edge does not get that condition ignored without a
trace.

This cell has **no mutant**, because the current behaviour is already the mutant (§4.2). What it must prove
depends on a decision that is not yours (§11 Q-E6):

| If the mentor rules | the cell asserts |
|---|---|
| `Edge.when` is **out of scope** for Day 30 | a recipe carrying a non-null `when` is **rejected**, loudly, with a message naming `when`. One line of product code, one test. This is the honest form of "not supported" |
| `ConditionExecutor` and `when` evaluation **land** before Day 30 | the declared condition actually decides the branch — and Grid E gains a `branch_taken` axis, which is a change to a generated file and therefore a mentor decision, not yours |

```
REQUIRED (either ruling)
  [1] a recipe whose only edge carries a `when` that is never true
  [2] an assertion that the run's outcome REFLECTS the declaration — either by
      refusing the recipe, or by not walking the edge
  [3] the current behaviour (walk it anyway, silently) must make the assertion
      FAIL. Verify that by running the test before any product change

DERIVED BAND
  the ruling is open ⇒ this cell is `todo:` pending Q-E6.
  Silence is the worst of the three available outcomes; do not ship it as `na:`.
```

### 8.3 `E-P1` — the one `real-gateway` pilot (`todo:embedding-gateway`)

**Must prove:** the refusal derivation holds when the answer comes from a component that is genuinely capable
of fabricating — which no `fixtures-stub` cell can show, because at the stub you write the answer yourself.

```
REQUIRED
  [1] a real gateway LLM in the loop, asked a question whose answer exists only
      outside the retrieved set
  [2] the same oracle as E03: no citation survives, the run reads as a refusal
  [3] an assertion on the ANSWER TEXT, not only on the flags — this is the one
      cell in the guide that can address the §5.4 gap
  [4] a recorded note on non-determinism: umbrella §3.5 requires that acceptance
      criteria not depend on an LLM's IQ, so this cell reports evidence and
      never gates on model quality

DERIVED BAND
  seam absent ⇒ `todo:embedding-gateway`. Do NOT substitute a fixture LLM and
  file it under E-P1 — that is E01..E03 with a different label (register §14
  CP-2.4 #4, axis-label laundering: an axis value not causally exercised by the
  test's setup ⇒ the cell is `unknown`).
```

### 8.4 What the open points do to this surface's ceiling — read this before promising a band

**5 of the 8 open points fall inside blocking zones:** `M-I-5`, `M-I-5b`, `M-I-6` in zone 1 (cross-tenant /
cross-role leakage) and `M-I-7`, `M-I-8` in zone 4 (cost lineage and trace ordering).

Register §7's rule: *a cell in a blocking zone may reach band **HIGH** only with evidence that a real mutant
was killed.* Applied here, with no editorialising: **until those five points are closed, every blocking-zone
cell on the interpreter surface caps at MEDIUM.** Not because nobody has done the work — because there was no
anchor to kill.

And because the zone roll-up is **`min`, never the average** (register §4), one cell short of evidence in
zone 1 or zone 4 holds the whole acceptance run. The five points above are, concretely, the list of things that
lift this surface off its cap. That is the schedule; work it in that order.

> **Scope of every "0 red" above.** The counts are over the **203 non-DB tests**. The 51 DB-gated tests were
> not run — this environment has no Postgres and starting one was out of scope. For `M-I-8` specifically the
> gap is closed by inspection rather than by a run: the only cost assertion in the DB-gated population is
> `apps/studio/tests/test_trace_writer.py:62`, and it compares against an event the test itself constructs with
> `cost=0.0021` (`:29`), so it cannot redden when `_NO_COST` changes. `[UNVERIFIED]` by execution; verify it
> with a DB before you sign the band.

---

## 9. Things that never count as evidence for a cell in this guide

- **`pytest.raises(NotImplementedError)`** — proves a seam is absent, not that anything is right.
  `test_executors_behavior.py:174-183` uses it legitimately, as a **scope pin** on the two unbuilt executors,
  and its own docstring says so (`:176-178`: *"locks the current STUB state, not a business property"*). That
  is honest, and it is still not evidence for any `E…` cell.
- **`xfail` or `skip`, in any form.** On this surface the cost is measured, not theoretical: §8.1 correction 2
  shows an `xfail(strict=False)` marker **absorbing a live mutation kill**. If you must add one, record the cell
  id, the reason, and the condition for removal in the code.
- **A constant asserted against the same constant.** Three assertions in the current suite have this shape, and
  all three are load-bearing to know about because they look like coverage:

  | Assertion | Where | Where the value comes from |
  |---|---|---|
  | `result == []` for `kb-retrieve` | `test_executors_behavior.py:57` | `EmptyKbSearch` returns `[]` unconditionally. Replace the entire executor body with `return []` and this stays green |
  | `result == {"terminated": True}` | `test_executors_behavior.py:171` | `executors.py:329` — the same one-line constant, written twice |
  | `result["tokens"] == Tokens(prompt=0, completion=0)` | `test_executors_behavior.py:91` | `executors.py:249` — likewise |

  `test_interpreter_behavior.py:108` and `:122` repeat the first and second of these through the walk.

  **Be fair about these two files while you are being precise.** Their docstrings claim every assertion pins a
  concrete stub-shaped value rather than a bare `raises`, and read literally that claim is **true**. And the
  same files have real teeth elsewhere: the `citations` / `refused` / walk-order assertions are what makes
  `M-I-1` (6 red), `M-I-1b` (7 red) and `M-I-15` (1 red) die. These files are not "xanh giả" — false green — in
  general. Exactly three of their assertions are.

  What that means for your work: **label each assertion you write as a state-pin or a property-pin.** A
  state-pin fixes today's stub value and is expected to change when the stub is filled in; a property-pin fixes
  something that must hold in every implementation. Without the labels, the next person cannot tell which of
  your red tests at Day 30 is a regression and which is progress.
- **`test_stub_embedding_is_deterministic` (`test_stub_embedding.py:31-37`) and anything shaped like it.**
  `StubEmbedding.embed` reads a JSON file and returns its contents (`demo_stubs.py:94-98`) — it **cannot** be
  non-deterministic. The assertion is true regardless of the code. Measured: replacing the return with a
  constant vector leaves this case green while destroying every retrieval score, and only
  `test_stub_embedding_replays_fixture_vectors` (`:11-19`, absolute values) reddens. `_vectors_are_8_dimensional`
  (`:22-28`) also stays green, since a constant vector has the right width.
- **A test whose `KbSearch` double discards the argument the cell is about.** `FixtureKbSearch` (`:65`),
  `MultiChunkFixtureKbSearch` (`:90`) and `_TenantCapturingKbSearch` (`:128`) in
  `test_kb_retrieve_llm_step_threading.py` all `del` `section_roles` and `top_k` on their first line. Those
  doubles are correct for what that file measures — threading — and they are **structurally incapable** of
  supporting `E-M2` or `E-M3`. The file name says `kb_retrieve`, which makes it easy to assume the fence is
  already covered. It is not.
- **An axis value that never enters the test's causal path.** A cell labelled `real-gateway` whose setup
  contains no gateway is `unknown`, not covered. `tools/xcheck_cell_ids.py` checks **id parity only**, so a
  cell id sitting in an unrelated docstring passes every automated check that exists (register §14 CP-2.4 #4).
- **`assert ts == sorted(ts)` on interpreter output.** §4.3's corollary. Always true; proves nothing.

---

## 10. Pinned-by — must-fix rows that collide with a `KHÓA` pin-test

The repo has a `KHÓA` / `KHOÁ` idiom: green tests whose job is to pin the **current decision** in place, holes
included. There are more than ten of them across the kit. Methodology §7.2 has the rule: **a pin-test asserts a
decision, not a behaviour. When the decision changes, the pin-test changes in the same commit, with a reference
to the decision.** Doing that is not weakening a gate.

Every row below lists the pin-tests it collides with. Flip them in the same commit as the fix.

| Row / fix | Pinned-by | What the pin currently asserts | What has to happen |
|---|---|---|---|
| `E-M1`, if you consolidate the two dispatch tables | `test_node_type_closed.py::test_registry_has_exactly_six` (`:16-21`, `KHOÁ` at `:17`) | `REGISTRY`'s key-set is exactly the 6 `NodeType` values | If `REGISTRY` becomes the real table, or is removed, this test moves with it — and `registry.py:1-2`'s "ONLY place" claim stops being false. Reference the decision in the commit |
| `E-M1`, if you leave both tables | same | same | Add one sentence to the pin's docstring saying it guards the copy, and cite `E-M1` as the test that guards the original. Do not delete the pin |
| `E-M7`, either ruling | `test_executors_behavior.py::test_condition_hitl_still_not_implemented` (`:174-183`, `Scope-fence (KHOÁ)`) | `ConditionExecutor` and `HitlPauseExecutor` both raise `NotImplementedError` | Only collides on the "`ConditionExecutor` lands" branch. On the "reject `when`" branch there is **no** collision: measured, **no test anywhere in the kit constructs an `Edge` with a non-null `when`** (`grep "when=" \| grep -v "when=None"` ⇒ 0 hits), so a new rejection rule breaks nothing |
| `E-M4` | none — but `test_trace_event_emission.py::test_event_timestamps_strictly_increase` (`:111-117`) overlaps | that four events sort and are distinct | Do not modify or delete it. It is not wrong, it is insufficient (§4.3). Add `E-M4` alongside it and say in your docstring that `E-M4` is the one with teeth |
| `E-M5` | `apps/studio/tests/test_trace_writer.py:62` (DB-gated) | a written `cost` round-trips through Postgres | No collision: it builds its own event with `cost=0.0021` (`:29`) and never reads `_NO_COST`. Named here so nobody assumes it guards the interpreter's constant |
| Any row that makes `StubEmbedding` content-aware (Q-E2) | `test_stub_embedding.py::test_stub_embedding_replays_fixture_vectors` (`:11-19`) | the exact 8-dimensional vectors replayed from `smoke-01.json` | This is the **only** embedding assertion with teeth (it is what kills `M-I-4`). Content-awareness changes the vectors, so the pin must be re-pinned in the same commit — and it must stay an absolute-value assertion, or the last teeth on that surface are gone |

**If you find a pin-test this section did not list, that is a gap in this guide — report it.** Do not route
around it in either direction: not by silently deleting the pin, and not by concluding the fix is impossible.

---

## 11. Open questions that block rows

Do not guess these. Each one changes what a correct assertion says, and three of them are not AIE-1 decisions
at all.

| id | Question | Blocks | Whose call |
|---|---|---|---|
| **Q-E1** | Beyond `D-20`'s default shape, **who owns the audit** and does `reason` get any consumer? `D-20` fixes the carrier (`obs.trace_events.outputs`) and the enum, and that is enough to write `E-S1`. What is not decided: whether anything **reads** it. An audit nobody queries is a log with extra steps. Measured: `grep -rni "audit"` over `packages`, `apps`, `tests` returns **one** line — a docstring at `tests/e2e/test_lifecycle.py:69` restating the umbrella clause. No writer, no reader, no consumer | `E-S1` [3] can be written; the AC "the audit is usable" cannot be graded | mentor + DE |
| **Q-E2** | **Is `StubEmbedding` required to be content-aware?** Two stubs exist with opposite semantics: `demo_stubs.py:78-83` declares that `StubEmbedding.embed` *"ignores each text's CONTENT and replays the recorded `response` vectors"* and is *"not content-aware"*; `apps/studio/src/studio_app/providers/fakes.py:38-40` (`FakeEmbedding._vector`) **is** content-aware (sha256 of the text) — and `fakes.py:6-9` states it is explicitly **not** an AIE-1 deliverable. This is not a stylistic clash: `umbrella-contract.md:83` makes *"retrieval quality (chunking×embedding trade-off có số)"* a graded AIE-1 deliverable, and if every vector is chosen by index rather than by content then **every retrieval score is noise** and the trade-off has no numbers to report | the graded chunking × embedding deliverable, and the re-pin in §10 | mentor |
| **Q-E3** | **Does `EndExecutor` emit the final trace event?** `umbrella-contract.md:71` assigns `end` the job *"Emit trace cuối + result"*. The code does it the other way: `EndExecutor.execute` returns a one-line constant (`executors.py:325-329`) and the **interpreter** emits every event uniformly (`interpreter.py:267-282`). Uniform emission is the better design. But leaving both as they are makes `executors.py:320-323`'s docstring a dead contract, and keeps `test_end_terminates` a constant-versus-constant assertion forever (§9) | whether `end` gets a cell at all, and whether one §9 assertion is a bug or a correct state-pin | mentor |
| **Q-E4** | **Does `hitl-pause` belong to SWE or AIE-1?** `umbrella-contract.md:66` puts *"Owner chính"* = **SWE**. `executors.py:313` says *"AIE-1 owns this pause/emit/yield executor body"*. Two sources, two answers. Per the register's one-guide-per-quadrant rule (§1, `D-10`) there is one guide file per quadrant, so this decides **which guide** the node's cells live in | any `hitl-pause` cell — deliberately absent from this guide until it is answered | mentor |
| **Q-E5** | **How is a run that breaks mid-way recorded?** There is no `try`/`except` anywhere in `packages/engine/src/studio_engine/` (grep ⇒ 0), so an executor exception escapes `run()` at `interpreter.py:237` before that node's event is built. Events already written stay written; `RunResult` is never returned. The result in storage is a run with some events and no `end` — **indistinguishable** from Grid D's `trace_state = missing-event`. A dashboard reader cannot tell "the run failed" from "the trace is broken". Adding `status` / `error` to `TraceEvent` touches **frozen contract #2** ⇒ **mini-RFC + 4/4 signatures**; the cheaper alternative is an `end` event carrying `{"terminated": false, "error": …}` | a run-failure cell, and Grid D's `missing-event` row's interpretation | **mini-RFC** — contract #2 is DE's |
| **Q-E6** | **Is `Edge.when` in scope for Day 30 at all?** §4.2 measured it as a dead field that is silently ignored. Ruling (a) evaluate it, ruling (b) reject recipes that carry it. Silence is the third option and the worst of the three | `E-M7`, and whether Grid E gains a `branch_taken` axis (which would change a generated file) | mentor |

Also inherited, and answered elsewhere — do not re-open them here: `GUIDE-A` **Q2** (who resolves
`section_roles`) gates `E-M2`'s second half, and register **Q2** (who makes `cost` real) gates `E-M5`'s ceiling.

---

## 12. Cell index

Every id in this guide appears with the same spelling in the tier-B counterpart.
`tools/xcheck_cell_ids.py` fails the build if one side has an id the other does not — but be aware of what it
checks: its pattern is a grid letter plus exactly **two digits**, so it reconciles `E01`, `E02` and `E03` and is
**blind to the hyphenated ids** (`E-S…`, `E-M…`, `E-P…`). Ten of the thirteen cells below are therefore not
machine-reconciled. Carry the cell id in your test docstring for all thirteen anyway; the reconciliation for the
hyphenated ten is a human read, and a missing id there fails silently.

| id | Subject | State | Zone | § |
|---|---|---|---|---|
| `E01` | `grounding=authorized-match` — the positive control | live | — | 5.1 |
| `E02` | `grounding=no-match` | live | Z1 | 5.2 |
| `E03` | `grounding=out-of-scope-match` | live | Z1 | 5.3 |
| `E-S1` | refusal + audit, as a causal chain | `todo:refusal-reason` (yours) | Z1 | 6 |
| `E-S2` | fence-blocked versus KB-empty | `todo:` — **seam does not exist** | Z1 | 7 |
| `E-M1` | the real dispatch table covers 6 node types | live | — | 8.2 |
| `E-M2` | `section_roles` neither widened nor erased | live | Z1 | 8.2 |
| `E-M3` | declared `top_k` honoured | live | Z1 | 8.2 |
| `E-M4` | monotonic-`ts` guard under an injected clock | live, **mandatory** | Z4 | 8.2 |
| `E-M5` | `cost` on the event | live (capped) | Z4 | 8.2 |
| `E-M6` | `inputs_hash` derived from inputs | live | — | 8.2 |
| `E-M7` | `Edge.when` does not vanish silently | `todo:` pending Q-E6 | — | 8.2 |
| `E-P1` | `real-gateway` pilot | `todo:embedding-gateway` | Z1 | 8.3 |

**13 cells: 9 live, 4 `todo:`.** Three of the four `todo:` cells are blocked on decisions rather than on code,
which is why §11 is not an appendix.
