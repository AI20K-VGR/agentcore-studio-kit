# Onboarding — AgentCore Studio kit

This is the Day-1 walkthrough for a new OJT engineer (DE, SWE, AIE-1, or AIE-2) joining the
AgentCore Studio batch. Read this before touching any package. The plan's full decision record is
`plans/260717-1516-studio-kit-template/plan.md`; the system spec this kit is built against is
`plans/260717-1516-studio-kit-template/research/studio-spec-and-workspace.md`.

## The 2-4-8 rule

- **2 weeks to stand up** — the mentor builds this kit in Tuần 0 (before Day 1), so trainees
  `git clone` straight into a running skeleton: Docker/Postgres/CI/contracts/RLS/queue/OTel are
  already WIRE (they run) on day one. Business logic in the 4 quadrant packages is intentionally
  left as `Protocol` + `NotImplementedError` + a RED acceptance test — that RED test **is** your
  spec.
- **4 owners**, one per quadrant, each self-sufficient inside their own package (see the ownership
  table below). You should never need to read, let alone edit, another owner's package to make
  progress on yours — if you find yourself needing to, that is a sign the 4 contracts
  (`packages/contracts/`) are missing something, and that's a mini-RFC + mentor-approval conversation,
  not a quiet cross-owner edit.
- **8-step demo** — the graduation demo (charter.md §2) that proves the whole lifecycle works
  end to end, mirrored as one RED-by-design system-level test file:
  `tests/e2e/test_lifecycle.py`.

## Which package is mine?

| Owner | Package | Import name | What you build | What you consume, never write |
|---|---|---|---|---|
| **DE — Nguyễn Đông Anh** | `packages/kb` | `studio_kb` | KB pipeline (doc-factory, chunk/embed/index), `kb.search` fence-DATA (permission filter AT RETRIEVAL, chunk-level, fail-closed, server-side `section_roles`), trace sink, cost table, golden-set (30 case) | Workbench/Tenant-Wall (SWE), interpreter/executor (AIE-1), eval harness/judge (AIE-2) |
| **SWE — Thiệu Quang Minh** | `packages/workbench` | `studio_workbench` | Workbench UI (form + canvas wiring), recipe validator + graph-lint (6-node closed set, no cycles the spec forbids), publish/eval-gate wiring, version/rollback, Tenant-Wall (INV-1, session→tenant resolve) | KB pipeline/`kb.search` internals (DE), interpreter/executor (AIE-1), eval harness/judge/scorecard-render (AIE-2 — you only wire the gate that reads AIE-2's verdict) |
| **AIE-1 — Trần Bá Đạt** | `packages/engine` | `studio_engine` | Interpreter, the 6 node executors (`kb-retrieve·llm-step·condition·tool-call·hitl-pause·end`), `EmbeddingService` 2-impl (stub-local + gateway — this is YOUR graded deliverable, do not accept a "complete" Gemini embedding shortcut), fence-EXECUTOR (pass `section_roles` through correctly, never bypass via the LLM) | Workbench/Tenant-Wall (SWE), doc-factory/`kb.search` internals/trace-sink (DE — you call `kb.search`, you don't write it), eval harness/judge/scorecard (AIE-2 — you supply citations, not verdicts) |
| **AIE-2 — Lưu Tiến Duy** | `packages/evalhub` | `studio_evalhub` | Eval harness, LLM-judge + agreement-check (vs the golden-set hand labels — don't trust the judge blindly), scorecard render, trace UX | eval-gate-wiring/publish/rollback (SWE — you supply the verdict, SWE wires the gate), golden-set authoring (DE), interpreter/executor/EmbeddingService (AIE-1 — you consume citations) |

`packages/contracts` (`studio_contracts`) is mentor/shared-owned, mentor-approval to change — every
quadrant package imports it (DIP), never each other. `apps/studio` (composition root) and
`apps/web` (Vite + React Flow canvas scaffold) are mentor-owned.

## First hour

```bash
git clone <this-kit-subtree-repo>
cd agentcore-studio-kit
cp .env.example .env          # fill in real DSNs/keys (or leave STUDIO_USE_FAKE_PROVIDERS=true)
make setup                    # uv sync — one venv, one lockfile, all 6 Python members
make dev                      # docker compose up -d — pgvector/pgvector:pg17, default profile
make test                     # uv run pytest — full workspace suite should be green
                               # (except tests/e2e — that one is RED-by-design until you fill in
                               # your quadrant's business logic; see the demo target below)
make demo                     # placeholder for the 8-step lifecycle demo — wired progressively
```

Then open your package's `tests/` directory. Every `Protocol` you need to implement already has a
RED acceptance test sitting next to it. Green that test, one at a time, and you're building toward
your slice of the 8-step demo.

## Money-shot steps (read before you touch fence code or the eval gate)

- **Step 5 — fence-proof** (`tests/e2e/test_lifecycle.py::test_step_5_fence_proof_zero_leak_money_shot`):
  a question whose answer exists ONLY in another tenant's KB must produce a refusal, never a
  leaked answer. Leakage=0 is a hard AC, not "reduced" — the dedicated leak-test at
  `packages/kb/tests/test_leak.py` and `make leak-test` hold DE to the same zero bar.
- **Step 7 — gate-blocks-a-regression** (`tests/e2e/test_lifecycle.py::test_step_7_regression_blocks_gate_and_rolls_back_money_shot`):
  degrading an agent's instructions must FAIL the re-eval and BLOCK publish + trigger a rollback —
  a real hard gate, never just a warning.

## Fallback (Hướng A)

If per-package `uv`/mypy/IDE tooling costs the mentor too much time in Tuần 0, the directory tree
can stay exactly as-is while collapsing to a single root `pyproject.toml` (Hướng A) — the 4-tier
ownership boundary (packaging + CI-per-package + CODEOWNERS + schema-per-quadrant) still holds
without a true `uv` workspace. Not the default; this is an explicit escape hatch, documented so a
mentor under time pressure has a pre-approved fallback instead of inventing one under stress.

## Docs vs this kit

The training docs at `agentcore-studio/**` (repo root, one level up) are an input for field names,
node-types, and contract shapes — not a hard constraint. Where they diverge from this production
kit (repo layout, Python version, storage mechanism), see `docs/DOCS-UPDATE-NOTE.md`.
