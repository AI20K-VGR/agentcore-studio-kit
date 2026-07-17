"""LLM-judge seam — spec AIE-2 (R-SPEC A7, INV-4, INV-7).

Scores subjective (non-exact-match) golden-set cases via an LLM judge. Two invariants this seam's
real implementation MUST carry, per R-SPEC A7 and the umbrella-contract invariants:

- **Agreement-check vs hand labels (required, R-SPEC A7)**: a judge that is never checked against
  a human-labeled baseline is not trustworthy alone — every judged case's agreement score
  (`Judge.agreement`, P2 `studio_contracts.scorecard.Judge`) must be derivable from a real
  comparison against a hand label, not a constant/placeholder value.
- **Cap ≤100 calls/day + cache (INV-4)**: the real `judge()` MUST check a cache keyed on
  `(case_id, actual)` before making an LLM call, and MUST refuse (not silently proceed) once the
  day's cap of 100 calls is reached.
- **Descope-guard (INV-7)**: when the daily cap is hit, or the judge provider is unavailable, the
  caller (`harness.py`) falls back to an exact-match scorer instead of failing the whole eval run
  — this module's contract is to make that capped/unavailable state observable (e.g. by raising or
  returning a sentinel the harness can detect), not to implement the fallback itself.

Rubric note (R-SPEC A7 :161): D3·Rigor is NOT activated here — 30 cases + the ≤100/day cap is the
intended DoD; this module does not need deep statistical calibration of judge agreement.

Body intentionally empty (`NotImplementedError`) — this is the OJT spec surface for AIE-2 to fill.
"""

from __future__ import annotations


class LLMJudge:
    """LLM-judge for subjective eval cases — cap ≤100 calls/day + cache (INV-4), required
    agreement-check against hand labels (R-SPEC A7), descope-guard to exact-match (INV-7)."""

    async def judge(self, case_id: str, expected: str, actual: str) -> tuple[bool, float]:
        """Return `(success, agreement)` for one case, judging `actual` against `expected`.
        `agreement` is the judge's agreement score against a hand label for this case (R-SPEC A7).
        Spec AIE-2 — not yet implemented."""
        raise NotImplementedError("LLMJudge.judge — spec AIE-2, not yet implemented")
