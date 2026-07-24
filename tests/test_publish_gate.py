"""Integration tests for Publish Manager & Eval-Gate Wiring (Issue #19 — Day 5 SWE)."""

from __future__ import annotations

from dataclasses import dataclass
import pytest

from studio_workbench.builder_d4 import create_recipe_d4
from studio_workbench.publish_manager import handle_publish_request


@dataclass
class MockScorecard:
    pass_gate: bool
    overall_score: float


@pytest.mark.asyncio
async def test_publish_gate_pass() -> None:
    sample_recipe = create_recipe_d4()
    mock_scorecard = MockScorecard(pass_gate=True, overall_score=0.90)
    res = await handle_publish_request("agent-1", sample_recipe, mock_scorecard)
    assert res["status"] == "SUCCESS"
    assert res["published_version"] == "v1.0.0"
    assert "Xuất bản thành công" in res["message"]


@pytest.mark.asyncio
async def test_publish_gate_fail_rollback() -> None:
    sample_recipe = create_recipe_d4()
    mock_scorecard = MockScorecard(pass_gate=False, overall_score=0.65)
    res = await handle_publish_request("agent-1", sample_recipe, mock_scorecard)
    assert res["status"] == "ROLLBACKED"
    assert res["active_version"] == "v0.9.0"
    assert "Xuất bản thất bại" in res["message"]
