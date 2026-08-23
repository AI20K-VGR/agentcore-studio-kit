"""Seam `run_agent_loop()` (engine) ⇄ `chunks_from_trace()` (evalhub) — bằng chứng retrieval của bộ
chấm đọc được trace do vòng lặp mới sinh ra.

**Vì sao bài này sống ở kit gốc chứ không ở `packages/evalhub/tests`:** `.importlinter` xếp 4
quadrant là sibling **không được import lẫn nhau**, nên không file test nào bên evalhub được phép
`import studio_engine`. Seam giữa hai quadrant chỉ kiểm được ở superproject — cùng lý do
`tests/e2e/` và `test_scorer_role_fence.py` nằm ở đây. Hệ quả kèm theo: bài này **chỉ đúng với con
trỏ submodule đang ghim**, nên nó phải đi cùng lần bump `packages/engine` lên `65731e5`
(`engine#36`), không tách ra được.

## Bài này khoá một tiền đề CỤ THỂ, và tiền đề đó suýt bị hiểu sai

Kế hoạch S3 (`redesign-scope-7d-review.md` §7.5) giả định vòng lặp mới sẽ phát kết quả `kb_search`
dưới dạng event `tool-call` mang `outputs["tool"] == "kb_search"`, và kết luận `chunks_from_trace`
**phải được sửa** để đọc thêm nguồn thứ hai — món đó được gắn nhãn "đường găng, land trong 48h".

Đọc `agent_loop.py` đã merge thì **không phải vậy**: nhánh `kb_search` phát
`NodeType.KB_RETRIEVE` với `outputs["chunks"]` (và `outputs["fenced"] = True` khi 0 chunk hợp lệ) —
đúng khuôn `interpreter.run()` cũ, như comment trong chính file đó ghi (*"same semantics as
`interpreter.py:434-439`"*). **Chỉ tool không-phải-kb** (`calculator`, `current_datetime`) mới phát
`NodeType.TOOL_CALL`. Nên `chunks_from_trace` khớp sẵn, không sửa một dòng.

⇒ Việc đúng không phải "vá bộ chấm" mà là **khoá tiền đề đó lại**. Nếu ngày nào đó `kb_search` đổi
sang phát `tool-call`, `chunks_from_trace` sẽ trả `None` cho **mọi** run — và `None` nghĩa là
*"không quan sát được"*, fail-closed ⇒ **mọi case từ-chối bị chấm sai**, `success_rate` tụt, không
một exception nào nổi lên. Đó là ca xanh-giả, và bài này là chỗ nó phải đỏ.

## Ba nghĩa của giá trị trả về, cả ba đều được assert

`None` / `[]` / `list` là **ba nghĩa khác nhau** (`harness.py:124-131`), và một bài chỉ kiểm nhánh
"có chunk" sẽ xanh với một bản gộp `None` vào `[]` — đúng lớp lỗi `evalhub#18` từng phải vá. Nên:

- `test_chunks_from_trace_doc_duoc_chunk_cua_vong_lap` — có chunk ⇒ list **không rỗng**, và
  `chunk_id` khớp đúng corpus (không chỉ "khác None");
- `test_retrieval_rong_ra_list_rong_khong_phai_none` — `kb_search` chạy nhưng 0 chunk ⇒ `[]`
  (*hàng rào chặn sạch*, bằng chứng TỐT), **không** `None`;
- `test_khong_goi_kb_search_ra_none_fail_closed` — LLM trả lời thẳng, không lượt `kb_search` nào ⇒
  `None` (*không quan sát được*), **không** `[]`.

Hai bài cuối là cặp đối xứng: gộp `None` với `[]` theo chiều nào cũng làm đúng một trong hai đỏ.
"""

from __future__ import annotations

import json
from uuid import UUID

import pytest
from studio_contracts import (
    AgentConfig,
    Dag,
    KbBinding,
    KbSearchResultItem,
    NodeType,
    Recipe,
    ScorecardThreshold,
    TraceEvent,
)
from studio_engine.agent_loop import run_agent_loop
from studio_engine.demo_stubs import EmptyEmbedding
from studio_evalhub.harness import chunks_from_trace

_TENANT = UUID("a0000000-0000-0000-0000-00000000000a")
_CHUNK_ID = "ankor-leave-001#c1"


class _Session:
    """Khớp `SessionContext` bằng shape (3 member `@property`), không cần adapter — cùng khuôn
    `_FrozenSessionContext` của engine, dựng lại tại chỗ vì helper test của quadrant khác không phải
    API công khai."""

    def __init__(self, tenant_id: UUID, roles: list[str]) -> None:
        self.tenant_id = tenant_id
        self.user = "seam-test"
        self.roles = roles


class _FixedKbSearch:
    """Trả đúng `items` đã dựng sẵn, bất kể query — bài này đo **đường đi của chunk vào trace**,
    không đo chất lượng retrieval."""

    def __init__(self, items: list[KbSearchResultItem]) -> None:
        self._items = items

    async def search(
        self, query: str, tenant_id: UUID, section_roles: list[str], top_k: int
    ) -> list[KbSearchResultItem]:
        del query, tenant_id, section_roles, top_k
        return list(self._items)


class _KbThenAnswerLLM:
    """Lượt 1 gọi `kb_search`, lượt 2 trả lời — hình dạng tối thiểu để vòng lặp phát đủ một event
    `KB_RETRIEVE` rồi kết thúc."""

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, prompt: str, **kwargs: object) -> str:
        del prompt, kwargs
        self.calls += 1
        if self.calls == 1:
            return f"TOOL_CALL: {json.dumps({'tool': 'kb_search', 'params': {'query': 'q'}})}"
        return f"Theo tài liệu, câu trả lời có căn cứ tại [{_CHUNK_ID}]."


class _AnswerNowLLM:
    """Trả lời ngay lượt đầu, **không gọi tool nào** — dựng ca 'không có event `kb-retrieve`'."""

    async def complete(self, prompt: str, **kwargs: object) -> str:
        del prompt, kwargs
        return "Tôi không tìm thấy thông tin phù hợp trong tài liệu."


class _CollectingTraceWriter:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    async def write(self, event: TraceEvent) -> None:
        self.events.append(event)


def _recipe() -> Recipe:
    """`dag` rỗng có chủ đích — `run_agent_loop` là DAG-blind (K8); chỉ `agent_config`/`kb_binding`
    có ý nghĩa với nó."""
    return Recipe(
        agent_id="agent-seam-test",
        tenant_id=_TENANT,
        agent_config=AgentConfig(instructions="", model="", tool_whitelist=["calculator"]),
        dag=Dag(nodes=[], edges=[]),
        kb_binding=KbBinding(kb_id="kb-1", scope="ankor/public"),
        golden_set_ref="golden-1",
        scorecard_threshold=ScorecardThreshold(success=0.8, citation_accuracy=0.8),
    )


async def _run(llm: object, items: list[KbSearchResultItem]) -> list[TraceEvent]:
    writer = _CollectingTraceWriter()
    await run_agent_loop(
        _recipe(),
        # `_Session` khớp `SessionContext` bằng shape (structural), không cần `type: ignore` —
        # đúng lý do `SessionContext` khai 3 member là `@property`.
        session_context=_Session(_TENANT, ["public"]),
        kb_search=_FixedKbSearch(items),
        llm=llm,  # type: ignore[arg-type]
        embedding=EmptyEmbedding(),
        trace_writer=writer,
        question="Nhân viên được bao nhiêu ngày phép?",
    )
    return writer.events


def _item(chunk_id: str) -> KbSearchResultItem:
    return KbSearchResultItem(
        chunk_id=chunk_id, text="Nhân viên chính thức được 12 ngày phép.", score=0.9,
        tenant_id=_TENANT, section_role="public",
    )


async def test_chunks_from_trace_doc_duoc_chunk_cua_vong_lap() -> None:
    """Chunk `kb_search` trả về đi tới `chunks_from_trace` **nguyên vẹn và nhận dạng được**.

    Assert trên `chunk_id` chứ không chỉ `is not None`: một bản cài đặt phát event `KB_RETRIEVE`
    **rỗng** vẫn qua được phép kiểm "khác None", trong khi bằng chứng no-leak cần đúng danh tính
    chunk đã rời khỏi retrieval.

    Bài này cũng là chỗ khẳng định `kb_search` phát `KB_RETRIEVE` **chứ không phải** `TOOL_CALL` —
    đổi sang `TOOL_CALL` thì `chunks_from_trace` trả `None` và bài đỏ ngay tại đây."""
    events = await _run(_KbThenAnswerLLM(), [_item(_CHUNK_ID)])

    chunks = chunks_from_trace(events)

    assert chunks is not None, "vòng lặp không phát event KB_RETRIEVE nào — seam đã gãy"
    assert [chunk["chunk_id"] for chunk in chunks] == [_CHUNK_ID]
    # Neo tiền đề cho người đọc sau: đúng node_type nào mang chunk.
    assert [e.node_type for e in events if e.outputs.get("chunks") is not None] == [NodeType.KB_RETRIEVE]


async def test_retrieval_rong_ra_list_rong_khong_phai_none() -> None:
    """`kb_search` CÓ chạy nhưng trả 0 chunk ⇒ `[]` = *hàng rào chặn sạch*, **không** `None`.

    Đây là bằng chứng TỐT của nhánh từ-chối: nó nói *"đã hỏi, và không có gì rời khỏi retrieval"*.
    Đọc thành `None` (*không quan sát được*) sẽ biến một run chứng minh được thành một run không
    chứng minh được gì, và `score_case` cho `success = False` vô điều kiện."""
    events = await _run(_KbThenAnswerLLM(), [])

    chunks = chunks_from_trace(events)

    assert chunks == [], f"retrieval rỗng phải ra [] (chặn sạch), nhận {chunks!r}"
    # Vòng lặp đánh dấu đúng ca này bằng cờ audit `fenced` — vế "có ghi audit" của money-shot.
    kb_events = [e for e in events if e.node_type is NodeType.KB_RETRIEVE]
    assert [e.outputs.get("fenced") for e in kb_events] == [True]


async def test_khong_goi_kb_search_ra_none_fail_closed() -> None:
    """LLM trả lời thẳng, **không lượt `kb_search` nào** ⇒ không event `KB_RETRIEVE` ⇒ `None`.

    Đối xứng với bài trên, và cặp này là thứ chặn việc gộp hai giá trị: gộp theo chiều nào cũng làm
    đúng một trong hai bài đỏ. `None` ở đây đúng nghĩa fail-closed — không có phép đo nào để nói
    hàng rào đã chặn, nên không được đọc thành 'chặn sạch'."""
    events = await _run(_AnswerNowLLM(), [_item(_CHUNK_ID)])

    assert not [e for e in events if e.node_type is NodeType.KB_RETRIEVE]
    assert chunks_from_trace(events) is None


@pytest.mark.parametrize("tool_name", ["calculator"])
async def test_tool_khong_phai_kb_phat_tool_call_va_khong_mang_chunks(tool_name: str) -> None:
    """Vế còn lại của tiền đề: tool **không phải** `kb_search` phát `TOOL_CALL`, và event đó
    **không** mang `chunks`.

    Không có bài này thì tiền đề mới chỉ được khoá một nửa — một bản cài đặt nhét `chunks` vào mọi
    event tool sẽ làm `chunks_from_trace` đọc phải kết quả `calculator` như thể là bằng chứng
    retrieval, và cả 3 bài trên vẫn xanh."""

    class _ToolThenAnswerLLM:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, prompt: str, **kwargs: object) -> str:
            del prompt, kwargs
            self.calls += 1
            if self.calls == 1:
                return f"TOOL_CALL: {json.dumps({'tool': tool_name, 'params': {'expression': '1+1'}})}"
            return "Kết quả là 2."

    events = await _run(_ToolThenAnswerLLM(), [_item(_CHUNK_ID)])

    tool_events = [e for e in events if e.node_type is NodeType.TOOL_CALL]
    assert tool_events, f"{tool_name} phải phát một event TOOL_CALL"
    assert all(e.outputs.get("chunks") is None for e in tool_events)
    # Không có event KB_RETRIEVE nào ⇒ bộ chấm đọc đúng là 'không quan sát được'.
    assert chunks_from_trace(events) is None


async def test_moi_event_tool_deu_khong_mang_citations() -> None:
    """Cổng C-1: **chỉ lượt trả-lời-cuối** được mang `citations`; mọi event tool đều `None`.

    Bỏ cổng này là mở fail-open thẳng vào `citation_accuracy` — một tool tự khai `citations` sẽ ăn
    điểm trích dẫn mà không có câu trả lời nào thật sự dựa vào nó. Khoá ở đây vì `citations_from_trace`
    (evalhub) gom `.citations` từ **mọi** event, cố ý node-agnostic, nên nó không tự phân biệt được.

    **Phải đi qua CẢ HAI nhánh tool trong một run** (`kb_search` **và** một tool không-phải-kb), vì
    hai nhánh dựng `TraceEvent` ở hai chỗ khác nhau trong `agent_loop.py` — event `KB_RETRIEVE` và
    event `TOOL_CALL`. Đo được: bản đầu của bài này chỉ chạy `kb_search`, và mutant gieo
    `citations=[...]` vào **event tool không-phải-kb** đã **sống sót** — dòng đó chưa từng được
    chạy. Một bài C-1 chỉ phủ một nhánh là bài không khoá được cổng C-1."""

    class _KbThenCalcThenAnswerLLM:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, prompt: str, **kwargs: object) -> str:
            del prompt, kwargs
            self.calls += 1
            if self.calls == 1:
                return f"TOOL_CALL: {json.dumps({'tool': 'kb_search', 'params': {'query': 'q'}})}"
            if self.calls == 2:
                return f"TOOL_CALL: {json.dumps({'tool': 'calculator', 'params': {'expression': '1+1'}})}"
            return f"Theo tài liệu, câu trả lời có căn cứ tại [{_CHUNK_ID}]."

    events = await _run(_KbThenCalcThenAnswerLLM(), [_item(_CHUNK_ID)])

    # Cưỡng chế tiền đề của chính bài này: thiếu một trong hai loại event tool thì bài mất răng ở
    # đúng nhánh mutant sống sót lần trước.
    assert any(e.node_type is NodeType.KB_RETRIEVE for e in events), "run không đi qua nhánh kb_search"
    assert any(e.node_type is NodeType.TOOL_CALL for e in events), "run không đi qua nhánh tool không-phải-kb"

    non_final = [e for e in events if e.node_type is not NodeType.LLM_STEP or "answer" not in e.outputs]
    assert non_final, "không dựng được event non-final nào — bài mất răng"
    assert all(e.citations is None for e in non_final), (
        f"event non-final mang citations: {[(e.node_type, e.citations) for e in non_final if e.citations]}"
    )
