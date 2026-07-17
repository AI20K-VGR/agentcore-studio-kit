"""Phase 10 — README + ONBOARDING.md onboarding-content gate tests.

Locks the onboarding surface (2-4-8 rule, "one engineer lives in one package", the 4-quadrant
ownership table from R-SPEC A4, and the run commands) in both `README.md` (extended, P1 already
seeded the 2-4-8 skeleton) and the new `docs/ONBOARDING.md`. See
plans/260717-1516-studio-kit-template/phases/phase-10-frontend-e2e-docs.md.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The 4 R-SPEC A4 owners and at least one artifact/package each owns — used to assert the
# ownership table actually names every quadrant, not just the word "ownership".
OWNERS_AND_ARTIFACTS = {
    "DE": ("packages/kb", "trace"),
    "SWE": ("packages/workbench", "Tenant-Wall"),
    "AIE-1": ("packages/engine", "interpreter"),
    "AIE-2": ("packages/evalhub", "scorecard"),
}


def test_readme_has_248_rule_and_one_package_per_engineer() -> None:
    text = (ROOT / "README.md").read_text()
    assert "2-4-8" in text, "README must state the 2-4-8 rule"
    assert "2 weeks" in text or "2 tuần" in text, "README must spell out the '2 weeks to stand up' part of 2-4-8"
    assert "4 owners" in text or "4 owner" in text, "README must spell out the '4 owners' part of 2-4-8"
    assert "8-step" in text or "8 bước" in text, "README must spell out the '8-step demo' part of 2-4-8"
    assert "one package" in text.lower(), "README must state each OJT engineer lives in ONE package"


def test_readme_has_4_quadrant_ownership_table() -> None:
    text = (ROOT / "README.md").read_text()
    for owner, artifacts in OWNERS_AND_ARTIFACTS.items():
        assert owner in text, f"README ownership table must name owner {owner!r}"
        for artifact in artifacts:
            assert artifact in text, f"README ownership table must mention {artifact!r} for owner {owner!r}"


def test_readme_has_run_commands() -> None:
    text = (ROOT / "README.md").read_text()
    for target in ("make setup", "make dev", "make test", "make leak-test", "make demo"):
        assert target in text, f"README must document `{target}`"


def test_readme_has_hướng_a_fallback() -> None:
    text = (ROOT / "README.md").read_text()
    assert "Hướng A" in text or "Huong A" in text, "README must document the Hướng A fallback"


def test_onboarding_doc_exists_and_covers_248_and_ownership() -> None:
    onboarding_path = ROOT / "docs" / "ONBOARDING.md"
    assert onboarding_path.exists(), "docs/ONBOARDING.md must exist (P10)"
    text = onboarding_path.read_text()
    assert "2-4-8" in text, "ONBOARDING.md must state the 2-4-8 rule"
    for owner in OWNERS_AND_ARTIFACTS:
        assert owner in text, f"ONBOARDING.md must name owner {owner!r}"
    assert "make setup" in text, "ONBOARDING.md must document the first `make setup` step"
