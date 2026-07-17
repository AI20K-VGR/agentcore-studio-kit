"""Phase 8 — eval-gate ĐỎ-by-design tests (spec AIE-2, R-SPEC A7 INV-6/INV-7).

`harness.py`/`judge.py`/`compute.py` are intentionally empty (`NotImplementedError`) at P8 —
the OJT spec surface AIE-2 fills next. These tests pin the SHAPE of that gap rather than pretend
it is closed: the eval-gate money-shot ("sửa instructions tệ → verdict FAIL → chặn + rollback",
R-SPEC A7 INV-6) cannot run for real yet because nothing produces a real verdict.

Marked `xfail(strict=False)` (builtin pytest marker — no root pyproject.toml edit) so this gap is
VISIBLE in the suite (not silently green, not silently deleted) without blocking the P8 regression
gate. `strict=False` means an unexpected pass (once AIE-2 implements the seam) is reported as
XPASS, not a failure — main tracks these to flip green as AIE-2's OJT progresses, never edits this
file to fake a pass today.

Boundary (R-SPEC A4): these tests exercise ONLY the eval-harness/judge/scorecard seam AIE-2 owns —
they do NOT stand up a real golden-set (DE's job), a real DAG interpreter (AIE-1's job), or
publish/rollback wiring (SWE's job); those are consumed, not asserted, here.
"""

from __future__ import annotations

import pytest
from studio_contracts import CaseResult, Judge
from studio_evalhub.compute import compute_scorecard
from studio_evalhub.harness import EvalHarness
from studio_evalhub.judge import LLMJudge


@pytest.mark.xfail(reason="spec AIE-2 fills harness/judge/compute", strict=False)
async def test_gate_blocks_on_fail() -> None:
    """Money-shot (R-SPEC A7 INV-6, umbrella-contract step 7): an agent recipe with bad
    instructions runs the 30-case golden set through `EvalHarness.run`, `compute_scorecard`
    decides `gate.verdict == "FAIL"`, and SWE's publish/rollback wiring (not exercised here —
    ownership fence) blocks + rolls back on that verdict. Currently unreachable — `EvalHarness.run`
    raises `NotImplementedError`, so there is no real verdict to gate on yet. This is the ĐỎ this
    test records until AIE-2 implements the seam, at which point the assertion below is the real
    contract to satisfy."""
    harness = EvalHarness()
    scorecard = await harness.run(agent_id="agent-bad-instructions", golden_set_ref="golden-set-eval-1")

    assert scorecard.gate.verdict == "FAIL"


@pytest.mark.xfail(reason="spec AIE-2 fills harness/judge/compute", strict=False)
async def test_harness_judge_compute_not_implemented() -> None:
    """KHÓA: spec AIE-2 seams (`EvalHarness.run`, `LLMJudge.judge`, `compute_scorecard`) all have
    an intentionally empty body — each MUST raise `NotImplementedError`, not silently return a
    fabricated result, until AIE-2 fills them in. A red-teamer or reviewer "making this green" by
    stubbing a fake return value (instead of implementing the real seam) would be caught by this
    assertion flipping from raise-NotImplementedError to no-raise."""
    harness = EvalHarness()
    judge = LLMJudge()

    with pytest.raises(NotImplementedError):
        await harness.run(agent_id="agent-1", golden_set_ref="golden-set-eval-1")

    with pytest.raises(NotImplementedError):
        await judge.judge(case_id="case-1", expected="A", actual="A")

    with pytest.raises(NotImplementedError):
        compute_scorecard(
            agent_id="agent-1",
            golden_set_ref="golden-set-eval-1",
            results=[
                CaseResult(
                    case_id="case-1",
                    expected="A",
                    actual="A",
                    success=True,
                    citation_accuracy=1.0,
                    judge=Judge(label="pass", agreement=0.95),
                )
            ],
            threshold_success=0.9,
            threshold_citation_accuracy=0.9,
        )
