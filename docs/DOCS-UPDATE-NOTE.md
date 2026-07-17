# Docs update NOTE — training docs vs this production kit

**This is a pointer NOTE only.** It records where the training docs at `agentcore-studio/**`
(this repo's root, one level up from `agentcore-studio-kit/`) diverge from the production
decisions locked in this kit. It does **not** edit those docs — updating `agentcore-studio/**` to
match the production framework is a **separate, out-of-scope task**
(plan `260717-1516-studio-kit-template`, Decision #10 / discovery-brief.md §8). The docs are an
input (field names, node-types, contract shapes), not a hard constraint on this kit
(`plans/260717-1516-studio-kit-template/research/studio-spec-and-workspace.md` A6) — so this
divergence is expected, not a defect in either side.

## K1 — Repo layout

- **Docs say** (`agentcore-studio/05-mentor-playbook/mentor-cadence.md:55`, checklist item K1):
  a mono-repo with flat, top-level quadrant directories — `workbench/` (SWE) · `interpreter/`
  (AIE-1) · `kb/` + `obs/` (DE) · `eval/` (AIE-2) — plus top-level `recipes/`, `tests/`,
  `fixtures/`. No package manager boundary between quadrants; ownership is directory convention
  only.
- **This kit ships**: a real `uv` workspace — `packages/{contracts,kb,engine,workbench,evalhub}/`
  + `apps/studio/` + `apps/web/`, each a standalone `pyproject.toml` member with its own
  `[project].name`, resolved through one root `uv.lock` (Decision #1). Naming also differs:
  `interpreter/` -> `packages/engine/` (avoids the `eval` builtin shadow that ruled out a literal
  `eval/` package name too -> `packages/evalhub/`). Ownership is enforced 4 layers deep
  (packaging + CI-per-package matrix + CODEOWNERS + schema-per-quadrant DDL), not just directory
  convention.
- **Update needed**: rewrite K1's target-state tree in `mentor-cadence.md` to the `packages/*` +
  `apps/*` layout above (or explicitly re-affirm the flat layout as intentional and note this kit
  as a divergent, opt-in production variant).

## K2 — Python version

- **Docs say** (`agentcore-studio/00-tong-quan/charter.md:96`, DEC-E7): pin **Python 3.12**
  ("khớp venv skill").
- **This kit ships**: **Python 3.14** (`pyproject.toml` `requires-python = ">=3.14"`), matching the
  `document-intake` production reference (R-SPEC A6, Decision #6) — `uv` manages the toolchain
  itself, so the version pin does not change how a trainee runs `make setup`.
- **Update needed**: either bump DEC-E7 to 3.14 (align with this kit), or explicitly record that
  the training track (docs) and the production kit intentionally target different Python minors
  and why.

## Storage ladder (umbrella-contract.md Section 4) — SQLite vs Postgres

- **Docs say** (`agentcore-studio/01-roadmap/umbrella-contract.md`, Section 4 "Transport / storage
  ladder", ~lines 178-186): a 3-rung ladder — L0 in-memory + trace JSONL/SQLite, **L1 (S2
  default) SQLite** for trace/cost/index-metadata, L2 (stretch) a lightweight local vector store
  (sqlite-vss/faiss). Fence-at-retrieval and the money-shot demo steps are designed to stand on
  SQLite at L1.
- **This kit ships**: **Postgres-everything** (`pgvector/pgvector:pg17`) — DB + vector
  (`kb.chunks.embedding` column) + queue (`SELECT ... FOR UPDATE SKIP LOCKED` + lease) + blob
  (`bytea`), no SQLite anywhere (Decision #2). The fence is Postgres Row-Level Security
  (`FORCE ROW LEVEL SECURITY` + 2-role split + `WITH CHECK`) rather than an application-level
  SQLite filter (Decision #3).
- **Update needed**: rewrite Section 4's ladder to describe the Postgres-everything path (or keep
  the SQLite ladder as the training-only track and cross-reference this kit as the production
  alternative it maps to).

## Scope reminder

Nothing in `agentcore-studio/**` was modified to produce this NOTE. The actual doc rewrite (K1
tree diagram, DEC-E7 pin, Section 4 ladder text) is tracked as a follow-up task outside this plan
— see `plans/260717-1516-studio-kit-template/discovery-brief.md` line 131 and
`plans/260717-1516-studio-kit-template/plan.md` "Out of scope".
