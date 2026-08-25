"""Phase 10 — end-to-end Studio lifecycle harness (RED-by-design placeholder).

Ties the 8-step graduation demo (R-SPEC A5, `umbrella-contract.md:54-67` charter §2) into one
ordered test file — one test per step — so the 4 quadrant owners (DE/SWE/AIE-1/AIE-2) have a
single, system-level acceptance spec to fill in once their business logic lands (P5-P8 batch is
still `Protocol` + `NotImplementedError` as of P10; this file is intentionally RED-by-design until
then).

Each step is a placeholder: it documents the REAL behavior expected (not a vague TODO) but does
NOT fail the aggregate suite — `pytest.skip` keeps it non-blocking so this file never turns CI red
on its own (Regression Gate for P10: `uv run pytest tests/e2e -q` is expected skip/non-failing,
never a hard gate). An owner removes the skip and writes the real assertions once their quadrant's
`ddl()`/executor/UI wiring is real.

Money-shot steps (system-level ACs from plan.md "Acceptance (toàn plan)"):
  - Step 5 (fence-proof): the tenant fence must be provably zero-leak through the real app path —
    no admin/owner-role connection substituted at test time.
  - Step 7 (gate-block): the eval-gate must be a REAL hard gate — degrading `agent_config.instructions`
    must fail the re-eval and BLOCK publish + trigger rollback, not just warn.

See plans/260717-1516-studio-kit-template/phases/phase-10-frontend-e2e-docs.md,
plans/260717-1516-studio-kit-template/research/studio-spec-and-workspace.md (R-SPEC A5).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from psycopg import sql
from studio_contracts import (
    AgentConfig,
    Dag,
    Edge,
    KbBinding,
    Node,
    NodeType,
    Recipe,
    ScorecardThreshold,
    Tokens,
    TraceEvent,
)
from studio_evalhub.agent_runner import AgentAnswer, CaseRun
from studio_evalhub.golden_case import GoldenSet
from studio_evalhub.golden_loader import load_golden_set
from studio_evalhub.harness import EvalHarness
from studio_kb.doc_factory import TENANT_IDS
from studio_workbench.publish import publish, recipe_hash

E2E_PENDING_REASON = "e2e pending — owner fills after 4 quadrants land (P5-P8 business logic)"

# ── Bước 7 (money-shot AIE-2) — hằng số dùng chung ────────────────────────────────────────────
_GOLDEN_30 = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "kb"
    / "src"
    / "studio_kb"
    / "golden"
    / "callisto-golden-30-v1.yaml"
)
_REF = "callisto-golden-30-v1"

# Ngưỡng của RECIPE (`workbench/builder.py`), không phải của bộ chấm — viết ra để phép đo đọc được,
# không phải để sở hữu chúng (`DEC-D16-05`). Bài này **không** đụng hai số này: hạ ngưỡng để đổi
# verdict là đúng thứ `DEC-D20-03` cấm, và cũng làm bài mất sạch ý nghĩa.
_THRESHOLD_SUCCESS = 0.9
_THRESHOLD_CITATION = 0.95

# Câu lệnh phân biệt bản TỐT với bản HẠ. `_RunnerTheoInstructions` đọc đúng cụm này — nó đóng vai
# "agent hành xử theo prompt", tức thứ người dùng thật sự sửa khi họ làm hỏng một agent.
_MARKER_TOT = "TRÍCH DẪN NGUỒN"
_INSTRUCTIONS_TOT = (
    "Trả lời dựa trên tài liệu được truy xuất. Luôn TRÍCH DẪN NGUỒN. "
    "Từ chối khi câu hỏi nằm ngoài phạm vi kho tài liệu của người hỏi."
)
_INSTRUCTIONS_HA = "Trả lời ngắn gọn."


def test_step_1_form_creates_agent() -> None:
    """Step 1 (SWE, Workbench): opening the Workbench and submitting the agent-creation form
    creates a new agent recipe — authoring without writing code. Real assertion (owner fills):
    POST the form payload to the Workbench API, expect a persisted `recipe` row keyed by
    `agent_id`, `tenant` set from the authenticated session (not client-supplied)."""
    pytest.skip(reason=E2E_PENDING_REASON)


def test_step_2_attach_tools_and_kb_scope() -> None:
    """Step 2 (SWE + DE): attach 2 tools (from `tool_whitelist`) and 1 KB scoped to Tenant-X.
    Real assertion (owner fills): recipe.agent_config.tool_whitelist has exactly the 2 tool ids;
    recipe.kb_binding.scope == tenant-X section; a tool outside the whitelist is rejected by
    graph-lint before any run, not at execution time."""
    pytest.skip(reason=E2E_PENDING_REASON)


def test_step_3_canvas_draws_closed_dag() -> None:
    """Step 3 (SWE Workbench UI + AIE-1 graph-lint): draw a DAG on the canvas using ONLY the 6
    closed node-types (kb-retrieve -> llm-step -> condition -> tool-call). Real assertion (owner
    fills): graph-lint accepts the 4-node happy-path DAG; a 7th/invented node-type is rejected by
    the recipe validator before the run is ever interpreted (closed-set cap, R-SPEC A2)."""
    pytest.skip(reason=E2E_PENDING_REASON)


def test_step_4_test_run_emits_trace_with_cost() -> None:
    """Step 4 (AIE-1 interpreter + DE trace-sink): clicking Test executes the DAG and streams a
    trace_event per node (tokens, cost, inputs_hash) to the trace sink. Real assertion (owner
    fills): one trace_event per executed node, monotonic `ts` within the run, `cost` for the run
    matches across all 3 surfaces (Test UI live view, trace timeline, cost dashboard) — a mismatch
    across surfaces is itself a bug per the umbrella contract's cost-lineage invariant."""
    pytest.skip(reason=E2E_PENDING_REASON)


def test_step_5_fence_proof_zero_leak_money_shot() -> None:
    """Step 5 (DE fence-DATA + AIE-1 fence-EXECUTOR + SWE Tenant-Wall) — MONEY-SHOT.

    Asking a question whose answer exists ONLY in Tenant-Y's KB, while the running agent is
    scoped to Tenant-X, must produce a refusal + audit trail — NEVER a hallucinated or leaked
    answer. Real assertion (owner fills, through the REAL app path, no admin-role shortcut):
    - `kb.search` filters at retrieval (chunk-level, fail-closed) — a chunk from Tenant-Y's KB
      must never leave the function, even before it reaches the LLM step.
    - `section_roles` are resolved server-side from the session; a client-supplied
      `section_roles` override in the request is IGNORED (anti T6 label-spoof).
    - The end-to-end leakage count across the fenced query is exactly 0 (not "reduced") — this is
      the same zero-leak bar as the dedicated `packages/kb/tests/test_leak.py` CI job (F5), but
      exercised through the full lifecycle (form -> canvas -> Test) instead of the KB package in
      isolation.
    """
    pytest.skip(reason=E2E_PENDING_REASON)


async def test_step_6_eval_gate_pass_then_publish(pool: Any) -> None:
    """Step 6 (AIE-2 eval harness + SWE gate-wiring): running Eval scores the agent against the
    30-case golden set into a scorecard; a PASSing verdict unblocks Publish to a named endpoint.

    ## Bài này KHÔNG lặp lại bước 7, và đó là lý do nó tồn tại riêng

    Chiều `PASS ⇒ publish thành công` bước 7 đã chạy rồi ("Chiều 1"). Viết lại nó ở đây là thêm một
    bài xanh mà không thêm một bằng chứng nào. Hai vế dưới đây là thứ bước 7 **không** nói:

    **1. "against the 30-case golden set" — bước 7 không bao giờ đếm.** `success_rate` là một
    **tỉ lệ**: harness lặng lẽ chấm 3 case thì `3/3 = 1.0` vẫn vượt ngưỡng `0.9`, bước 7 vẫn xanh,
    và cổng đang gác một mẫu **không ai khai**. Mẫu số phải được khẳng định ở chính chỗ verdict được
    tin — cùng lý do `Judge.agreement` phải đi kèm mẫu số (`DEC-D16-03`).

    **2. "the publish endpoint only accepts a recipe whose MOST RECENT scorecard verdict is PASS"
    — trục ĐỘ TƯƠI, không phải trục chất lượng.** Bước 7 luôn ghép mỗi recipe với scorecard của
    **chính nó**, nên nó không hỏi được câu quan trọng nhất của mệnh đề trên: chuyện gì xảy ra khi
    ai đó trình một scorecard PASS **cũ** cho một recipe **mới**?

    Đó là đường vòng thật của cổng, và nó rẻ: hạ `instructions`, **giữ nguyên** scorecard PASS của
    bản tốt, gọi publish. Cổng 4 (`gate.verdict`) **không** chặn được — verdict ấy là `PASS` thật,
    do một lần chấm thật sinh ra. Thứ duy nhất đứng chắn là cổng 3
    (`scorecard.recipe_hash != recipe_hash(recipe)`, `DEC-D20-02`).

    Nên assert quyết định ở đây là **thông điệp nói `recipe_hash`, KHÔNG nói `verdict`** — đối xứng
    với assert phủ định của bước 7 (`"recipe_hash" not in str(bat.value)`). Hai bài cùng chặn, mỗi
    bài phải chứng minh nó chặn **ở đúng cổng của mình**; thiếu vế đó thì một `publish()` chặn mọi
    thứ vì một lý do duy nhất vẫn làm cả hai xanh.

    Không đụng ngưỡng (`DEC-D20-03`) và không đụng `instructions` của bản tốt — biến duy nhất giữa
    hai lần gọi `publish()` là **scorecard nào được trình**.
    """
    golden = load_golden_set(_GOLDEN_30, expect_ref=_REF)
    agent_id = "e2e-step6-stale-scorecard"

    # ── Vế 1: mẫu số của verdict phải là 30, khẳng định tại chỗ verdict được tin ───────────────
    assert len(golden.cases) == 30, f"bộ golden phải đủ 30 case, có {len(golden.cases)}"

    tot = _recipe(agent_id, _INSTRUCTIONS_TOT)
    sc_tot = await _cham(tot, golden)

    assert sc_tot.gate.verdict == "PASS", (
        f"bản tốt phải PASS, nhận {sc_tot.gate.verdict!r} "
        f"(success={sc_tot.aggregate.success_rate}, citation={sc_tot.aggregate.citation_accuracy})"
    )
    assert len(sc_tot.results) == 30, (
        f"verdict PASS này chấm trên {len(sc_tot.results)} case, không phải 30 — `success_rate` là "
        "một tỉ lệ, nên một mẫu nhỏ hơn vẫn vượt ngưỡng mà không đo cùng một thứ"
    )
    # Scorecard PASS này chứng nhận ĐÚNG recipe vừa chấm — tiền đề của vế 2 bên dưới.
    assert sc_tot.recipe_hash == recipe_hash(tot)

    async with pool.connection() as conn, conn.transaction():
        await _bind_tenant(conn, TENANT_IDS["ankor"])
        await publish(tot, sc_tot, conn)
    assert await _rows(pool, agent_id) == [(1, "published")]

    # ── Vế 2: scorecard PASS CŨ + recipe MỚI ⇒ chặn ở cổng recipe_hash, không phải cổng verdict ─
    ha = _recipe(agent_id, _INSTRUCTIONS_HA)
    assert recipe_hash(ha) != recipe_hash(tot), "hai bản phải khác hash, nếu không vế này vô nghĩa"

    # `pytest.raises` nằm BÊN TRONG transaction — cùng lý do đã ghi ở bước 7: route bắt `ValueError`
    # rồi ném `HTTPException`, nên connection thoát sạch và psycopg COMMIT. Bọc ra ngoài là đo một
    # đường không tồn tại trong production.
    async with pool.connection() as conn, conn.transaction():
        await _bind_tenant(conn, TENANT_IDS["ankor"])
        with pytest.raises(ValueError, match="recipe_hash") as bat:
            await publish(ha, sc_tot, conn)

    # Cổng 4 KHÔNG phải thứ chặn ở đây — verdict được trình vẫn là `PASS` thật. Nếu thông điệp nói
    # `verdict` thì hoặc cổng 3 đã biến mất, hoặc `publish()` chặn vì một lý do khác thứ bài này đo.
    assert "verdict" not in str(bat.value), (
        f"chặn sai cổng: thông điệp nói verdict, nhưng scorecard được trình có "
        f"verdict={sc_tot.gate.verdict!r} — vế này phải bị cổng recipe_hash chặn"
    )

    # Bản hạ KHÔNG được ghi, bản tốt v1 vẫn phục vụ — một scorecard PASS cũ không mở được cổng cho
    # một recipe khác.
    assert await _rows(pool, agent_id) == [(1, "published")], (
        "scorecard PASS cũ đã publish được một recipe KHÁC — cổng chỉ đo verdict, không đo scorecard "
        "này chứng nhận recipe nào"
    )


def _recipe(agent_id: str, instructions: str) -> Recipe:
    """DAG tối thiểu qua đủ 7 luật `graph_lint` (`publish()` gọi nó ở cổng 1). Chỉ `instructions`
    đổi giữa hai bản — mọi field khác giữ nguyên để `recipe_hash` chỉ lệch **vì** thứ đang đo."""
    nodes = [
        Node(id="n_kb", type=NodeType.KB_RETRIEVE, params={"query": "q", "section_roles": ["public"], "top_k": 5}),
        Node(id="n_llm", type=NodeType.LLM_STEP, params={}),
        Node(id="n_end", type=NodeType.END, params={}),
    ]
    return Recipe(
        agent_id=agent_id,
        tenant_id=TENANT_IDS["ankor"],
        agent_config=AgentConfig(system_prompt=instructions, model="fake", tool_whitelist=[]),
        dag=Dag(nodes=nodes, edges=[Edge(from_="n_kb", to="n_llm"), Edge(from_="n_llm", to="n_end")]),
        kb_binding=KbBinding(kb_id="kb-1", scope="ankor/public"),
        golden_set_ref=_REF,
        scorecard_threshold=ScorecardThreshold(success=_THRESHOLD_SUCCESS, citation_accuracy=_THRESHOLD_CITATION),
    )


def _trace_events(
    tenant_id: UUID, citations: list[str], chunks: list[dict[str, object]] | None = None
) -> list[TraceEvent]:
    """Trace tối thiểu **đúng carrier theo node**: `chunks` ở `kb-retrieve`, `citations` ở `llm-step`.

    Bản đầu dồn cả hai vào **một** event `KB_RETRIEVE` — @DongAnh2704 bắt đúng ở review `kit#208`:
    theo `agent_loop.py` thật, event `KB_RETRIEVE` **luôn** `citations=None`, chỉ lượt trả-lời-cuối
    (`LLM_STEP`) mới mang `citations` (cổng C-1). Bài vẫn xanh hôm nay **chỉ vì**
    `citations_from_trace` cố ý node-agnostic — nên ngày carrier được siết theo node, mọi case ở đây
    rơi về `citation_accuracy = 0` dù chất lượng không đổi một chút nào, và người đọc sẽ đi tìm
    regression ở chỗ không có.

    Dựng đúng hai event thay vì để lại một cờ theo dõi: fixture khớp producer thật thì nó không cần
    ai nhớ tới nó nữa."""
    kb = TraceEvent(
        event_id="e1",
        run_id="r1",
        agent_id="a1",
        tenant_id=tenant_id,
        node_id="n_kb",
        node_type=NodeType.KB_RETRIEVE,
        ts="2026-08-23T00:00:00.000000",
        inputs_hash="h",
        outputs={"chunks": chunks if chunks is not None else []},
        tokens=Tokens(prompt=0, completion=0),
        cost=0.0,
        citations=None,
    )
    llm = TraceEvent(
        event_id="e2",
        run_id="r1",
        agent_id="a1",
        tenant_id=tenant_id,
        node_id="n_llm",
        node_type=NodeType.LLM_STEP,
        ts="2026-08-23T00:00:01.000000",
        inputs_hash="h",
        outputs={"answer": "x", "refused": False, "citations": citations},
        tokens=Tokens(prompt=0, completion=0),
        cost=0.0,
        citations=citations,
    )
    return [kb, llm]


class _RunnerTheoInstructions:
    """Agent double **hành xử theo `instructions`** — mắt xích mà hai file gate-2 hiện có không dựng.

    Dựng từ `recipe.agent_config.instructions` chứ không nhận nó trong `run_case`, vì
    `AgentRunner.run_case` cấu trúc mà nói **không thấy recipe** (`agent_runner.py`) — runner được
    composition root dựng theo từng recipe, đúng như `routes/publish.py::_evaluate` dựng
    `EngineAgentRunner(recipe=recipe)`. Double này mô phỏng đúng quan hệ đó, không phải né nó.

    Bản **tốt** (instructions còn câu trích-dẫn-nguồn): trả lời đúng theo golden, trích đúng nguồn,
    và **từ chối** đúng case cần từ chối. Bản **hạ**: trả lời chung chung, **không** trích nguồn, và
    — chỗ nguy hiểm nhất — **thôi từ chối** ở case đáng từ chối. Đó là dạng hỏng thật khi ai đó gọt
    prompt cho "ngắn gọn": agent mất luôn hàng rào phạm vi chứ không chỉ mất chất lượng văn phong."""

    def __init__(self, golden: GoldenSet, tenant_map: Mapping[str, UUID], instructions: str) -> None:
        self._tot = _MARKER_TOT in instructions
        self._fixtures: dict[tuple[str, UUID, tuple[str, ...]], CaseRun] = {}
        for case in golden.cases:
            tenant_id = tenant_map[case.tenant]
            # Khoá 3 thành phần — golden-30 có cặp trùng `(query, tenant_id)` khác `section_roles`
            # (trục T6); khoá 2 thành phần sẽ nuốt một nửa mỗi cặp.
            key = (case.query, tenant_id, tuple(case.section_roles))
            role = case.section_roles[0] if case.section_roles else "public"
            chunk_id = f"{case.tenant}-handbook-000#c1"
            chunk: dict[str, object] = {
                "chunk_id": chunk_id,
                "tenant_id": str(tenant_id),
                "section_role": role,
                "score": 0.5,
                "text": "t",
            }
            if self._tot:
                if case.expects_refusal:
                    answer = AgentAnswer(answer="Tôi không thể trả lời câu hỏi này.", citations=[], refused=True)
                    events = _trace_events(tenant_id, [chunk_id], chunks=[chunk])
                else:
                    answer = AgentAnswer(
                        answer=f"Theo tài liệu, {case.expected}.",
                        citations=list(case.expected_citation),
                        refused=False,
                    )
                    events = _trace_events(tenant_id, list(case.expected_citation))
            else:
                # Bản hạ: không trích nguồn, và KHÔNG từ chối kể cả khi đáng từ chối.
                answer = AgentAnswer(answer="Bạn nên xem lại tài liệu nội bộ.", citations=[], refused=False)
                events = _trace_events(tenant_id, [], chunks=[chunk])
            self._fixtures[key] = CaseRun(answer=answer, events=events)

    async def run_case(self, *, agent_id: str, query: str, tenant_id: UUID, section_roles: list[str]) -> CaseRun:
        del agent_id
        return self._fixtures[(query, tenant_id, tuple(section_roles))]


async def _bind_tenant(conn: Any, tenant_id: UUID) -> None:
    """`wb.recipes` có `ENABLE`+`FORCE` RLS — không set biến phiên thì ghi/đọc 0 row, im lặng."""
    await conn.execute(sql.SQL("SET LOCAL app.tenant_id = {}").format(sql.Literal(str(tenant_id))))


async def _rows(pool: Any, agent_id: str) -> list[tuple[int, str]]:
    async with pool.connection() as conn, conn.transaction():
        await _bind_tenant(conn, TENANT_IDS["ankor"])
        cur = await conn.execute(
            "SELECT version, status FROM wb.recipes WHERE agent_id = %s ORDER BY version",
            (agent_id,),
        )
        return [(int(v), str(s)) for v, s in await cur.fetchall()]


async def _cham(recipe: Recipe, golden: GoldenSet) -> Any:
    """Chấm recipe bằng `EvalHarness` THẬT — `Scorecard` ra từ `compute_scorecard`, không dựng tay.

    `recipe_hash=` truyền vào để qua được cổng 2/3 của `publish()`, nên thứ quyết định ở cổng 4 là
    `verdict` chứ không phải hash — cùng lý do `test_gate2_publish_money_shot.py` bài 2/3 phải làm
    vậy."""
    return await EvalHarness().run(
        recipe.agent_id,
        _REF,
        golden_set_path=_GOLDEN_30,
        runner=_RunnerTheoInstructions(golden, TENANT_IDS, recipe.agent_config.system_prompt),
        tenant_ids=TENANT_IDS,
        threshold_success=_THRESHOLD_SUCCESS,
        threshold_citation_accuracy=_THRESHOLD_CITATION,
        recipe_hash=recipe_hash(recipe),
    )


async def test_step_7_regression_blocks_gate_and_rolls_back_money_shot(pool: Any) -> None:
    """Step 7 (AIE-2 eval-gate + SWE publish/rollback wiring) — MONEY-SHOT.

    Degrading `agent_config.instructions` (a deliberate regression) and re-running Eval must
    produce a FAILing scorecard verdict, and that FAIL must be a REAL hard gate: Publish is
    BLOCKED and the previously-published version is rolled back automatically — never just a
    warning banner a human can click past.

    ## Mắt xích bài này thêm vào — KHÔNG trùng hai file gate-2 đã có

    | File | Khoá đoạn nào của chuỗi |
    |---|---|
    | `apps/studio/tests/test_gate2_publish_money_shot.py` | `verdict` → chặn publish + rollback (verdict **cho sẵn**) |
    | `apps/studio/tests/test_gate2_verdict_from_live_spine.py` | chất lượng **runner** → `verdict` (đổi runner) |
    | **bài này** | **`instructions` → chất lượng → `verdict` → chặn + bản cũ vẫn phục vụ** |

    Hai file kia chứng minh từng nửa; không file nào nối chuỗi từ **thứ con người thật sự sửa**.
    Money-shot bước 7 nói về một **regression do người gây ra**, nên mắt xích `instructions` là
    phần không thể thiếu — thiếu nó thì bài chỉ chứng minh cổng đọc được một field.

    ## Chạy HAI CHIỀU, và đó là điều kiện chứ không phải cho đủ

    `FAIL` là giá trị **dễ trúng nhất**: runner chết, golden lệch, harness hỏng, hay
    `compute_scorecard` trả hằng `"FAIL"` — mọi thứ hỏng đều ra `FAIL`. Một bài chỉ assert chiều hạ
    sẽ **xanh với tất cả những thứ đó**, và khi đó nó chứng minh *cổng có chặn*, **không** chứng minh
    *cổng chặn vì chất lượng*. Chiều PASS là đối chứng bắt buộc.

    Bài này **không** đụng ngưỡng (`0.9/0.95` giữ nguyên, `DEC-D20-03`): thứ được đổi giữa hai chiều
    là `instructions`, đúng một biến."""
    golden = load_golden_set(_GOLDEN_30, expect_ref=_REF)
    agent_id = "e2e-step7-instructions-regression"

    # ── Chiều 1: bản TỐT ⇒ PASS ⇒ publish thành công ──────────────────────────────────────────
    tot = _recipe(agent_id, _INSTRUCTIONS_TOT)
    sc_tot = await _cham(tot, golden)
    assert sc_tot.gate.verdict == "PASS", (
        f"bản tốt phải PASS, nhận {sc_tot.gate.verdict!r} "
        f"(success={sc_tot.aggregate.success_rate}, citation={sc_tot.aggregate.citation_accuracy})"
    )
    async with pool.connection() as conn, conn.transaction():
        await _bind_tenant(conn, TENANT_IDS["ankor"])
        await publish(tot, sc_tot, conn)
    assert await _rows(pool, agent_id) == [(1, "published")]

    # ── Chiều 2: HẠ instructions ⇒ FAIL ⇒ publish bị chặn ─────────────────────────────────────
    ha = _recipe(agent_id, _INSTRUCTIONS_HA)
    sc_ha = await _cham(ha, golden)
    assert sc_ha.gate.verdict == "FAIL", "hạ instructions mà verdict không lật ⇒ cổng không đo chất lượng"
    # Điểm phải tụt THẬT, không chỉ verdict lật — verdict là hệ quả, số mới là bằng chứng.
    assert sc_ha.aggregate.success_rate < sc_tot.aggregate.success_rate

    # `pytest.raises` nằm **BÊN TRONG** transaction, không bọc ngoài — mô phỏng đúng
    # `routes/publish.py::publish_agent`: route **bắt** `ValueError` rồi ném `HTTPException(409)`,
    # Starlette biến nó thành Response **trước khi** thoát khỏi `async with pool.connection()` của
    # `tenant_context_middleware`, nên connection exit **sạch** ⇒ psycopg **COMMIT**. Bọc
    # `pytest.raises` ra ngoài sẽ để `ValueError` thoát khỏi `transaction()` ⇒ rollback toàn bộ —
    # một đường **không tồn tại trong production**, và mọi assert sau đó đo nhầm thứ.
    async with pool.connection() as conn, conn.transaction():
        await _bind_tenant(conn, TENANT_IDS["ankor"])
        with pytest.raises(ValueError, match=r"gate\.verdict='FAIL'") as bat:
            await publish(ha, sc_ha, conn)

    # Chặn phải VÌ verdict. `publish()` nội suy `agent_id` vào thông điệp nên `match="verdict"` trần
    # có thể khớp vào chính tên nhánh mình đặt — assert phủ định này mới là thứ phân biệt cổng 4 với
    # cổng 2/3 (tiền lệ: `test_gate2_publish_money_shot.py` bài 2, mutant `M-G4`).
    assert "recipe_hash" not in str(bat.value), "chặn sai cổng: thông điệp nói recipe_hash, không phải verdict"

    # Bản tốt v1 VẪN đứng `published`, bản hạ KHÔNG bao giờ được ghi.
    #
    # ⚠️ **Khẳng định này CỐ Ý hẹp, và đó là kết quả của review @DongAnh2704 (`kit#208`).** Bản đầu
    # ghi *"⇒ rollback đã chạy"* — sai, và DE bắt đúng. Đào tiếp thì lý do sâu hơn cả điều DE nêu:
    #
    # `_reassert_last_published` là **no-op ở MỌI trạng thái tới được**, nên không assertion nào —
    # và không cách bố trí transaction nào — phân biệt được "nó chạy" với "nó bị xoá":
    #
    #   • chưa có bản nào `published` ⇒ nó `return` sớm (`publish.py`, nhánh `row is None`);
    #   • có vN `published` ⇒ `rollback(to_version=N)` thấy hàng vN **tồn tại** ⇒ `UPDATE … 'rolled_back'
    #     WHERE status='published'` rồi `UPDATE … 'published' WHERE id=<vN>` — **hạ rồi nâng lại đúng
    #     hàng đó**, trạng thái cuối y hệt.
    #
    # Nhánh **có** tác dụng (`existing is None` trong `rollback()`, dựng lại hàng từ
    # `wb.recipe_versions`) không tới được từ `_reassert_last_published`, vì `to_version` luôn là
    # version của chính hàng vừa tìm thấy đang `published`.
    #
    # Đã gieo mutant "xoá hẳn `_reassert_last_published`": **sống sót**, đúng như phân tích. Đó là
    # tính chất của `publish.py`, không phải lỗ hổng của bài này — nên bài này khẳng định đúng thứ
    # nó chứng minh được, và finding về code đã báo riêng ở review.
    #
    # Vế "rollback" của money-shot vẫn đứng, chỉ khác cơ chế: v1 còn phục vụ **vì nhánh FAIL không
    # bao giờ hạ nó xuống `draft`** (câu `UPDATE … SET status='draft'` nằm SAU cổng verdict), chứ
    # không phải vì có ai khôi phục lại.
    assert await _rows(pool, agent_id) == [(1, "published")], (
        "bản tốt v1 phải còn `published` và bản hạ không được ghi — endpoint tiếp tục phục vụ bản "
        "đã biết là tốt sau khi publish bị chặn"
    )


def test_step_8_hitl_pause_resumes_after_approval() -> None:
    """Step 8 (SWE playground wiring + AIE-1 executor): a `hitl-pause` node in the flow suspends
    the run mid-DAG inside the playground, waiting for an external approval, then resumes exactly
    where it left off (first-class pause, not a hack). Real assertion (owner fills): the run's
    trace shows a paused state at the hitl-pause node with no further node execution until an
    approval action is recorded; after approval, execution resumes from the paused node (not
    restarted from the top) and completes to `end`."""
    pytest.skip(reason=E2E_PENDING_REASON)
