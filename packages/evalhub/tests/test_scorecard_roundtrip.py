"""Phase 8 gate test — scorecard round-trip + `eval.*` DDL idempotency.

KHÓA: evalhub dùng đúng `Scorecard` contract (P2) làm seam — bắt regression tự định
nghĩa lệch seam thay vì tái dùng contract đã đóng băng (R-SPEC A1#4). Round-trip qua
`studio_contracts.Scorecard` trực tiếp (không qua evalhub's own type) vì evalhub
KHÔNG định nghĩa lại Scorecard — nó tiêu thụ contract nguyên trạng (AIE-2 chỉ bút
harness/judge/compute, không bút schema).
"""

from __future__ import annotations

from studio_app.core._db import Pool
from studio_contracts import Aggregate, CaseResult, Gate, GateThreshold, Judge, Scorecard


def _sample_scorecard() -> Scorecard:
    return Scorecard(
        agent_id="agent-eval-1",
        golden_set_ref="golden-set-eval-1",
        results=[
            CaseResult(
                case_id="case-1",
                expected="A",
                actual="A",
                success=True,
                citation_accuracy=1.0,
                judge=Judge(label="pass", agreement=0.95),
            ),
            CaseResult(
                case_id="case-2",
                expected="B",
                actual="B",
                success=True,
                citation_accuracy=0.9,
                judge=Judge(label="pass", agreement=0.9),
            ),
        ],
        aggregate=Aggregate(success_rate=1.0, citation_accuracy=0.95),
        gate=Gate(
            threshold=GateThreshold(success=0.9, citation_accuracy=0.9),
            verdict="PASS",
        ),
    )


def test_scorecard_roundtrip_via_contract() -> None:
    """Build a `Scorecard` (P2 contract) the way evalhub's own compute.py will —
    agent_id/golden_set_ref/results/aggregate/gate — then dump -> validate must
    round-trip to an equal model. This pins evalhub to the frozen contract seam;
    if evalhub ever grew its own divergent Scorecard shape, this test would need
    to change to prove the divergence, catching the regression at review time."""
    original = _sample_scorecard()

    dumped = original.model_dump(mode="json")
    restored = Scorecard.model_validate(dumped)

    assert restored == original
    assert restored.model_dump(mode="json") == dumped


async def test_eval_schema_ddl_idempotent(admin_pool: Pool) -> None:
    """KHÓA: `eval.*` DDL (`studio_evalhub.schema.ddl()` — golden_sets/scorecards)
    chạy 2 lần liên tiếp không lỗi. Needs a live DB: `docker compose -f
    docker-compose.test.yml up -d` with STUDIO_DATABASE_URL_ADMIN pointed at it.
    The `admin_pool` fixture (root conftest.py) already runs `ensure_all_schemas`
    once during setup (which direct-imports this same `ddl()`); this test
    additionally re-runs evalhub's own DDL string directly, twice, in isolation
    — proving idempotency of THIS module's contribution specifically, not just
    the aggregate boot sequence.
    """
    from studio_evalhub.schema import ddl

    ddl_sql = ddl()
    assert ddl_sql  # P8 fills the P1 stub — must no longer be the empty string

    async with admin_pool.connection() as conn:
        await conn.execute(ddl_sql)
        await conn.execute(ddl_sql)

        cur = await conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'eval' ORDER BY table_name"
        )
        tables = {row[0] for row in await cur.fetchall()}
    assert tables == {"golden_sets", "scorecards"}
