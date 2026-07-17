"""eval.* schema DDL seam (schema-per-quadrant, Decision #4).

P1 stub filled at Phase 8 (Evalhub, AIE-2 owner) — `ensure_all_schemas()` (Phase 3,
`apps/studio/src/studio_app/core/schema.py`) direct-imports this module and calls `ddl()`. This
file is edited ONLY here, never `apps/studio` (antichain, plan.md "Dependency matrix &
file-ownership").

`eval.golden_sets` — one row per golden-set (produced by DE's doc-factory, consumed by AIE-2's
`harness.py`): `cases` is a JSONB array of the 30 `{case_id, expected}` pairs the eval-harness
runs against an agent recipe.

`eval.scorecards` — one row per eval run, shaped to match the `Scorecard` contract (P2, R-SPEC
A1#4): `results` (per-case `CaseResult`s), `aggregate` (success_rate/citation_accuracy), `gate`
(threshold + verdict — the field SWE's publish/rollback pipeline reads, INV-6).
"""

_EVAL_DDL = """
CREATE SCHEMA IF NOT EXISTS eval;

CREATE TABLE IF NOT EXISTS eval.golden_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    golden_set_ref TEXT NOT NULL UNIQUE,
    cases JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eval.scorecards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    golden_set_ref TEXT NOT NULL,
    results JSONB NOT NULL,
    aggregate JSONB NOT NULL,
    gate JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def ddl() -> str:
    """Return this quadrant's idempotent DDL — `eval.golden_sets` + `eval.scorecards`."""
    return _EVAL_DDL
