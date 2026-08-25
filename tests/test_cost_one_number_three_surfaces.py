"""Bất biến **"một số, ba mặt"** cho `cost` — ô GATE-3 số 3 (`kit#167`).

> *"Eval-gate chặn và rollback thật … Và số cost phải khớp ở **cả ba chỗ** nó xuất hiện (trace,
> bảng cost, scorecard)"* — mentor tự tay test.

**Vì sao bài này sống ở kit gốc.** Ba mặt nằm ở ba quadrant, và `.importlinter` xếp chúng là sibling
**không được import lẫn nhau**: `studio_kb.cost` (DE) và `studio_evalhub.run_report` (AIE-2) mỗi bên
tự cộng dồn, cố ý **trùng tên field + trùng luật** vì đó là thứ duy nhất giữ hai bên đối chiếu được
(xem docstring `RunCost` cả hai phía). Không file test nào trong một repo con được phép nhìn cả hai.
Chỉ superproject kiểm được — cùng lý do `test_agent_loop_chunks_seam.py` nằm ở đây.

## Ba mặt hôm nay là gì

| # | Mặt | Ai giữ | Hiện trạng |
|---|---|---|---|
| 1 | `TraceEvent.cost` mỗi event → `obs.trace_events` | AIE-1 emit · DE sink | **luôn `0.0`** |
| 2 | bảng cost per-run (`RunCost`) | DE `cost.py` · AIE-2 `run_report.py` | cộng dồn mặt 1 |
| 3 | `Scorecard` | `packages/contracts` | **không có field `cost`** |

Mặt 3 vắng là **quyết định**, không phải sót — `DEC-D19-02` (docstring `RunCost` bên evalhub) lập
luận: đặt một trục đang bằng `0.0` cạnh `gate.verdict` là dựng sẵn chỗ cho ai đó gate lên nó, và một
gate trên hằng số 0 sẽ PASS mọi thứ tới ngày nối giá thật rồi FAIL mọi thứ hôm sau. Bài này **không**
tự quyết mặt 3 là gì — việc đó cần ADR (`docs/decisions/scorecard.md`). Nó khoá hai mặt đang tồn
tại, và khoá cái điều kiện khiến mặt 3 có nghĩa: **con số phải thật trước đã**.

## `xfail` đã gỡ — chuông kêu đúng lúc, và đây là bản ghi của nó

Bài `test_emit_uses_the_single_price_source` sống dưới `xfail(strict=True)` từ `kit#213` tới lần
bump con trỏ này. Lý do lúc đó: `studio_kb.cost` giữ **bảng đơn giá — nguồn giá DUY NHẤT** cùng lưới
`price_mismatches()`, và docstring của lưới viết *"Hôm nay mọi `cost=0` **và `tokens=0`** →
`cost_of=0`, khớp"*. Vế *"và tokens=0"* đã hết đúng từ D19 (`kit#121`) — executor đếm token thật —
nên lưới **đang kêu trên mọi run thật** mà không ai nghe, vì chưa bài nào gọi nó trên trace thật.

Chọn `xfail(strict=True)` chứ không `skip` là để **CI tự nhắc**: ngày nối giá xong, bài `XPASS ⇒ đỏ`,
buộc người sửa gỡ cờ thay vì để một bài `skip` im lặng mãi. Nó hoạt động đúng như thế —
`contracts#11` (dời `cost_of` xuống `contracts`, gỡ chướng ngại `.importlinter`) + `kb#54` +
`engine#41` (wire `cost=cost_of(tokens)` tại cả 5 điểm emit) merge, con trỏ bump, và bài này đỏ vì
XPASS. Commit này gỡ cờ.

Đo tại thời điểm gỡ, một run 2 lượt qua `run_agent_loop`:

```text
llm-step     tokens=90/6   cost=0.00036
kb-retrieve  tokens=0/0    cost=0.0        ← 0 token ⇒ 0 cost, "đo được và bằng 0"
llm-step     tokens=95/4   cost=0.000345

price_mismatches           : []
studio_kb.aggregate_run_cost      : 0.000705
studio_evalhub.run_cost_from_trace: 0.000705    ← hai mặt KHỚP, trên số THẬT
run_cost.priced            : True     ⇒ render.py thôi in "chưa-nối-giá"
```

Bất biến *"một số, ba mặt"* từ đây đứng trên một số thật thay vì `0 == 0 == (không có)`. Nợ này mở
từ `DEC-D19-06` (13/08) và đóng ở đây — **11 ngày**, và thứ giữ nó sống suốt quãng đó là một cái
`xfail` chứ không phải trí nhớ của ai.
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
    Recipe,
    ScorecardThreshold,
    TraceEvent,
)
from studio_engine.agent_loop import run_agent_loop
from studio_engine.demo_stubs import EmptyEmbedding
from studio_evalhub.run_report import run_cost_from_trace
from studio_kb.cost import aggregate_run_cost, cost_of, price_mismatches

_TENANT = UUID("a0000000-0000-0000-0000-00000000000c")
_CHUNK_ID = "ankor-leave-001#c1"


class _Session:
    """Khớp `SessionContext` bằng shape (3 member), không cần adapter — cùng khuôn
    `test_agent_loop_chunks_seam.py`."""

    def __init__(self, tenant_id: UUID) -> None:
        self.tenant_id = tenant_id
        self.user = "cost-seam-test"
        self.roles = ["public"]


class _FixedKbSearch:
    async def search(
        self, query: str, tenant_id: UUID, section_roles: list[str], top_k: int
    ) -> list[KbSearchResultItem]:
        del query, tenant_id, section_roles, top_k
        return [
            KbSearchResultItem(
                chunk_id=_CHUNK_ID,
                text="Nhân viên được 12 ngày phép mỗi năm.",
                score=0.9,
                doc_id="ankor-leave-001",
                section_role="public",
                tenant_id=_TENANT,
            )
        ]


class _KbThenAnswerLLM:
    """Hai lượt — đủ để vòng lặp phát nhiều event mang token khác nhau, tức bài cộng dồn có gì để
    cộng. Một lượt duy nhất sẽ để lọt một bản cộng dồn chỉ đọc event đầu."""

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, prompt: str, **kwargs: object) -> str:
        del kwargs
        self.calls += 1
        if self.calls == 1:
            return f"TOOL_CALL: {json.dumps({'tool': 'kb_search', 'params': {'query': 'phép năm'}})}"
        return f"Nhân viên được 12 ngày phép mỗi năm [{_CHUNK_ID}]."


class _CollectingTraceWriter:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    async def write(self, event: TraceEvent) -> None:
        self.events.append(event)


def _recipe() -> Recipe:
    """`dag` rỗng có chủ đích — `run_agent_loop` là DAG-blind (K8)."""
    return Recipe(
        agent_id="agent-cost-seam",
        tenant_id=_TENANT,
        agent_config=AgentConfig(system_prompt="", model="", tool_whitelist=["calculator"]),
        dag=Dag(nodes=[], edges=[]),
        kb_binding=KbBinding(kb_id="kb-1", scope="ankor/public"),
        golden_set_ref="golden-1",
        scorecard_threshold=ScorecardThreshold(success=0.8, citation_accuracy=0.8),
    )


@pytest.fixture
async def run_events() -> list[TraceEvent]:
    """Trace của MỘT run thật qua `run_agent_loop` — không dựng `TraceEvent` bằng tay.

    Dựng tay thì bài này chỉ kiểm hai hàm cộng dồn cộng đúng phép cộng; đi qua vòng lặp thật mới
    kiểm được thứ đang hỏng: **giá trị `cost` mà điểm emit ghi vào trace**."""
    writer = _CollectingTraceWriter()
    await run_agent_loop(
        _recipe(),
        session_context=_Session(_TENANT),
        kb_search=_FixedKbSearch(),
        llm=_KbThenAnswerLLM(),
        embedding=EmptyEmbedding(),
        trace_writer=writer,
        question="Nhân viên được bao nhiêu ngày phép?",
    )
    return writer.events


async def test_the_two_aggregators_report_the_same_run_cost(run_events: list[TraceEvent]) -> None:
    """MẶT 1 ⇄ MẶT 2: hai bản cộng dồn ở hai quadrant phải ra **cùng một `RunCost`**.

    `studio_kb.cost.aggregate_run_cost` (DE) và `studio_evalhub.run_report.run_cost_from_trace`
    (AIE-2) là **hai cài đặt độc lập** của cùng một luật, viết riêng vì `.importlinter` cấm import
    chéo. Hai bên chỉ giữ được đồng bộ nhờ *"tên field + luật giống hệt"* — một quy ước, không phải
    một ràng buộc máy kiểm được. Bài này là chỗ quy ước đó thành ràng buộc.

    So **cả bốn** trường chứ không riêng `cost`: một bản cộng nhầm `prompt_tokens` sang
    `completion_tokens` vẫn ra đúng tổng `cost` (đơn giá khác nhau nên thực ra không, nhưng một bản
    bỏ sót `event_count` thì có) — so từng trường mới chỉ ra được chỗ lệch."""
    from_kb = aggregate_run_cost(run_events)
    from_evalhub = run_cost_from_trace(run_events)

    assert from_kb.run_id == from_evalhub.run_id
    assert from_kb.tenant_id == from_evalhub.tenant_id
    assert from_kb.prompt_tokens == from_evalhub.prompt_tokens
    assert from_kb.completion_tokens == from_evalhub.completion_tokens
    assert from_kb.event_count == from_evalhub.event_count
    assert from_kb.cost == from_evalhub.cost


async def test_the_run_actually_carries_tokens(run_events: list[TraceEvent]) -> None:
    """CHỐNG RỖNG cho bài dưới — bắt buộc, không phải thừa.

    `price_mismatches` so `event.cost` với `cost_of(event.tokens)`. Nếu mọi `tokens` đều `0` thì
    `cost_of` ra `0`, khớp với `cost=0`, và bài dưới sẽ **XANH vì không có gì để so** — đúng giả
    định mà docstring `price_mismatches` đang dựa vào và nó đã hết đúng. Bài này chốt rằng run thật
    có token thật, nên phép so ở dưới có nội dung."""
    total_tokens = sum(e.tokens.prompt + e.tokens.completion for e in run_events)
    assert total_tokens > 0, "run không mang token nào — bài price_mismatches bên dưới sẽ xanh rỗng"

    priced = [e for e in run_events if cost_of(e.tokens) > 0.0]
    assert priced, "không event nào có tokens đủ để ra giá > 0 — cùng lý do trên"


async def test_emit_uses_the_single_price_source(run_events: list[TraceEvent]) -> None:
    """MẶT 1 phải là số THẬT: mỗi `event.cost` bằng `cost_of(event.tokens)` của chính nó.

    Đây là điều kiện khiến hai mặt kia có nghĩa. Không có nó thì `RunCost.cost` cộng dồn một cột
    toàn `0.0`, và câu *"số cost khớp ở cả ba chỗ"* thành `0 == 0 == (không có)` — khớp một cách
    rỗng tuếch, đúng thứ ô GATE-3 số 3 không hỏi.

    `price_mismatches` là lưới của DE (`studio_kb/cost.py`), dựng sẵn cho đúng khoảnh khắc này.
    Bài này chỉ **gọi nó trên trace thật** — thứ chưa ai làm."""
    assert price_mismatches(run_events) == []
