"""Phase 10 — docs-update NOTE gate test.

Locks `docs/DOCS-UPDATE-NOTE.md` before it exists (RED) — it must list the 3 divergence points
between the training docs `agentcore-studio/**` and this production kit (K1 layout, K2 Python
3.12->3.14, storage-ladder SQLite->Postgres), per R-SPEC A6 and Decision #10 (plan.md). This is a
pointer NOTE only — updating `agentcore-studio/**` itself is a separate out-of-scope task; this
test does not touch those docs. See
plans/260717-1516-studio-kit-template/phases/phase-10-frontend-e2e-docs.md.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_docs_note_lists_divergence() -> None:
    """KHÓA: NOTE liệt kê K1 (layout) / K2 (Python 3.12->3.14) / storage-ladder SQLite->Postgres."""
    note_path = ROOT / "docs" / "DOCS-UPDATE-NOTE.md"
    assert note_path.exists(), "docs/DOCS-UPDATE-NOTE.md must exist (P10 pointer NOTE)"

    text = note_path.read_text()

    # K1 — layout divergence (mentor-cadence.md:55 flat quadrant dirs vs this kit's uv workspace
    # packages/* + apps/*).
    assert "K1" in text, "NOTE must reference K1 (layout divergence)"
    assert "mentor-cadence.md" in text, "NOTE must anchor K1 to mentor-cadence.md:55"
    assert "packages/" in text, "NOTE must contrast K1's flat layout against this kit's packages/* layout"

    # K2 — Python 3.12 (docs, charter.md:96 DEC-E7) vs 3.14 (this kit).
    assert "K2" in text, "NOTE must reference K2 (Python version divergence)"
    assert "charter.md" in text, "NOTE must anchor K2 to charter.md:96 (DEC-E7)"
    assert "3.12" in text and "3.14" in text, "NOTE must state both Python versions (docs 3.12 vs kit 3.14)"

    # storage-ladder — SQLite (docs, umbrella-contract.md Section 4) vs Postgres (this kit).
    assert "umbrella-contract.md" in text, "NOTE must anchor storage-ladder divergence to umbrella-contract.md"
    assert "SQLite" in text and "Postgres" in text, "NOTE must state both storage mechanisms (docs vs kit)"

    # Out-of-scope guard: this NOTE must not claim to have edited agentcore-studio/** itself.
    assert "out" in text.lower() and "scope" in text.lower(), (
        "NOTE must state updating agentcore-studio/** docs is a separate out-of-scope task"
    )
