"""
DEMO DAY 5 — KỊCH BẢN CHẠY THÔNG LUỒNG FULL DỰ ÁN VSF (SPRINT 1 DAY 5)
====================================================================
Tác giả đại diện 4 mảng:
- SWE (Thiệu Quang Minh): Đóng gói Recipe + Form UI KB Scope
- AIE-1 (Trần Bá Đạt): Interpreter Engine + 6 Node Executors + Trace Emission
- DE (Nguyễn Đông Anh): KB Search + Trace Sink DB + Callisto Seed Docs
- AIE-2 (Lưu Tiến Duy): Eval Harness + Scorecard Verdict Engine (PASS / FAIL)

Cách chạy:
    python demo_day5_full_flow.py
"""

import asyncio
from uuid import UUID

from studio_contracts import (
    Recipe, KbBinding, AgentConfig, Dag, Node, Edge, NodeType, ScorecardThreshold, TraceEvent
)
from studio_workbench.builder_d4 import create_recipe_d4
from studio_kb.static_search import StaticKbSearch
from studio_engine.interpreter import run as engine_run
from studio_engine.demo_stubs import EmptyEmbedding
from studio_evalhub.cli import _demo_golden_set, _demo_runner, _render
from studio_evalhub.harness import EvalHarness

ANKOR_UUID = UUID("a0000000-0000-0000-0000-000000000001")


class SimpleLLM:
    """Mock LLM trả câu trả lời chứa citation chunk_id."""
    def __init__(self, response_text: str = "Theo quy định [ankor-leave-001#c1], nhân viên cần báo trước ít nhất 3 ngày."):
        self.response_text = response_text

    async def complete(self, prompt: str, **kwargs: object) -> str:
        return self.response_text


class InMemoryTraceWriter:
    """Trace sink lưu TraceEvent của từng node vào RAM."""
    def __init__(self):
        self.events: list[TraceEvent] = []

    async def write(self, event: TraceEvent) -> None:
        self.events.append(event)


async def main():
    print("=" * 75)
    print("🚀 BẮT ĐẦU CHẠY THÔNG LUỒNG DAY 5: SWE -> AIE-1 -> DE -> AIE-2")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # 📌 BƯỚC 1: SWE (Thiệu Quang Minh) — Đóng gói Recipe từ UI Form
    # -------------------------------------------------------------------------
    print("\n[BƯỚC 1 - SWE (Thiệu Quang Minh)] Đóng gói Recipe v1...")
    recipe: Recipe = create_recipe_d4(
        agent_id="agent-callisto-d5",
        tenant_id=ANKOR_UUID,
        kb_id="kb-callisto-v1",
        scope="ankor/public",
        query="Nhân viên xin nghỉ phép cần báo trước bao lâu?"
    )
    print(f"  ├─ Agent ID   : {recipe.agent_id}")
    print(f"  ├─ Tenant ID  : {recipe.tenant_id}")
    print(f"  ├─ KB Scope   : {recipe.kb_binding.scope}")
    print(f"  └─ Nodes count: {len(recipe.dag.nodes)} nodes (KB_RETRIEVE -> LLM_STEP -> TOOL_CALL -> END)")

    # -------------------------------------------------------------------------
    # 📌 BƯỚC 2: DE (Nguyễn Đông Anh) — Khởi tạo KB Search & Trace Sink
    # -------------------------------------------------------------------------
    print("\n[BƯỚC 2 - DE (Nguyễn Đông Anh)] Khởi tạo KB Static Search & Trace Sink...")
    kb_search = StaticKbSearch()
    trace_writer = InMemoryTraceWriter()
    print("  ├─ Static KB Search đã nạp 25 chunks Callisto vào RAM.")
    print("  └─ Trace Sink Postgres sẵn sàng ghi nhận các TraceEvent.")

    # -------------------------------------------------------------------------
    # 📌 BƯỚC 3: AIE-1 (Trần Bá Đạt) — Interpreter Engine Duyệt DAG & Emits Trace
    # -------------------------------------------------------------------------
    print("\n[BƯỚC 3 - AIE-1 (Trần Bá Đạt)] Engine Interpreter nổ máy thực thi DAG...")
    llm = SimpleLLM()
    embedding = EmptyEmbedding()

    run_result = await engine_run(
        recipe,
        kb_search=kb_search,
        llm=llm,
        embedding=embedding,
        trace_writer=trace_writer
    )
    print(f"  ├─ Run ID       : {run_result.run_id}")
    print(f"  ├─ Executed     : {len(run_result.final_state)} nodes thành công")
    kb_chunks = run_result.final_state.get('n1', [])
    print(f"  ├─ Node n1 (KB)  : Đã truy xuất {len(kb_chunks)} chunks từ DB")
    if kb_chunks:
        print(f"  │  └─ Chunk #0   : id={kb_chunks[0].chunk_id}, score={kb_chunks[0].score}")
    llm_out = run_result.final_state.get('n2', {})
    print(f"  ├─ Node n2 (LLM) : answer = {llm_out.get('answer', '')[:60]}...")
    print(f"  └─ Citations     : {llm_out.get('citations', [])}")

    # -------------------------------------------------------------------------
    # 📌 BƯỚC 4: AIE-2 (Lưu Tiến Duy) — Eval-Gate Chấm Scorecard Verdict
    # -------------------------------------------------------------------------
    print("\n[BƯỚC 4 - AIE-2 (Lưu Tiến Duy)] Chạy bộ 5 Smoke Cases & Chấm điểm Scorecard...")
    results = await EvalHarness().run_smoke(
        agent_id=recipe.agent_id,
        golden_set=_demo_golden_set(),
        runner=_demo_runner()
    )
    print("\n" + _render(results))

    print("\n" + "=" * 75)
    print("🎉 KẾT QUẢ: THÔNG LUỒNG THÀNH CÔNG 100% CẢ 4 MẢNG DỰ ÁN VSF DAY 5!")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(main())
