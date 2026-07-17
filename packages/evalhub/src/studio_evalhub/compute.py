"""Scorecard-compute seam — spec AIE-2 (R-SPEC A7 INV-6, umbrella-contract.md:146-158).

Aggregates a golden-set run's per-case `CaseResult`s (P2 `studio_contracts.CaseResult`) into
`success_rate` + `citation_accuracy` (`Aggregate`), then decides `gate.verdict` (PASS|FAIL) against
the recipe's `ScorecardThreshold`. `gate.verdict == "FAIL"` is a HARD gate for Publish (INV-6,
umbrella-contract's "money-shot" step 7: "sửa instructions tệ → verdict FAIL → chặn publish +
rollback") — SWE's publish/rollback pipeline reads this field and blocks + rolls back, never
advisory-only. This module produces the verdict; it does NOT wire the publish/rollback gate itself
(that stays SWE's ownership, R-SPEC A4).

Body intentionally empty (`NotImplementedError`) — this is the OJT spec surface for AIE-2 to fill.
"""

from __future__ import annotations

from studio_contracts import CaseResult, Scorecard


def compute_scorecard(
    agent_id: str,
    golden_set_ref: str,
    results: list[CaseResult],
    threshold_success: float,
    threshold_citation_accuracy: float,
) -> Scorecard:
    """Aggregate `results` (one per golden-set case) into a `Scorecard`: `aggregate.success_rate`
    and `aggregate.citation_accuracy` are computed across `results`, and `gate.verdict` is `"PASS"`
    when both meet `threshold_success`/`threshold_citation_accuracy`, else `"FAIL"`. Spec AIE-2 —
    not yet implemented."""
    raise NotImplementedError("compute_scorecard — spec AIE-2, not yet implemented")
