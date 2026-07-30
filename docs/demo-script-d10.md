# Demo script a→z — GATE-1 (D10, 31/07)

> **Chung** (`day-09.md:47-49`, `day-10.md:44`): **một** kịch bản duy nhất chạy xuyên cả 4 quadrant,
> không phải 4 demo rời. Kế thừa `docs/day-05-thonluong-report.md` (weekly demo #1, Day 5) — bản đó
> **đã lỗi thời**: script đổi tên (`e2e_thonluong_demo.py` → `e2e_smoke_eval.py`), thêm `build_prompt`
> grounding thật (engine#10) + 2 RED-CHECK, và chưa có leg INV-1/trace-Postgres. Tài liệu này thay thế
> cho mục đích D10.
>
> Mọi lệnh dưới đây **đã chạy thật** trong phiên soạn tài liệu (không chép từ mô tả), trừ leg §3 —
> đánh dấu rõ **[CHƯA CHẠY LẠI PHIÊN NÀY]** vì cần Docker Postgres không sẵn có lúc soạn; lệnh đó đã
> được DE xác nhận chạy thật cùng ngày trong `packages/kb/docs/evidence-d9.md` §1.

---

## 0. Người demo mảnh nào (khớp `day-10.md:36-42`, mỗi người 5')

| Vai | Mảnh trong luồng | Lệnh của mình (§ tương ứng) |
|---|---|---|
| SWE | form → recipe (`create_recipe_d6`) + INV-1 client-khai-tenant bị ignore | §2 |
| AIE-1 | interpreter 3-node walk qua `recipe.dag.edges`, fixture-replay | §1 (thân chạy) |
| DE | `kb.search` fence + trace Postgres timeline đọc lại đúng thứ tự | §3 |
| AIE-2 | smoke-eval 5 case → bảng điểm, citation từ trace (1 nguồn số) | §1 (đầu ra) |

---

## 1. Thân luồng — form → interpreter → KB → prompt → adapter → smoke-eval

Không cần Docker (dùng `_NoopTraceWriter` cục bộ trong script — trace Postgres thật là §3 riêng).

```bash
python apps/studio/scripts/e2e_smoke_eval.py
```

**Đã chạy thật, kết quả (rút gọn — bảng đầy đủ + 2 RED-CHECK nằm trong output thật của script):**

```text
====================================================================================================
E2E SMOKE-EVAL — callisto-smoke-5-v0 (5 case) qua luồng thật
THẬT: recipe · interpreter · kb.search (fence) · trace · build_prompt · grounding · adapter · scorer
FIXTURE: ExtractiveFakeLLM — chỉ đọc prompt, không thấy golden (ý @DongAnh2704)
====================================================================================================
----------------------------------------------------------------------------------------------------
        ─ ĐẤU-NỐI (luồng thật) ─          ─ CHẤT-LƯỢNG ─  ─ CHẨN ĐOÁN ─
case    #ev 1run ts↑ tenant #chunk THÔNG? success cit_acc KB     quy-trách-nhiệm
----------------------------------------------------------------------------------------------------
SC-01   4   ✓    ✓   ✓      3      THÔNG  PASS    1.00    1/1    —
SC-02   4   ✓    ✓   ✓      3      THÔNG  PASS    1.00    1/1    —
SC-03   4   ✓    ✓   ✓      1      THÔNG  PASS    1.00    1/1    —
SC-04   4   ✓    ✓   ✓      3      THÔNG  FAIL    n/a*    —      LLM — không từ chối dù đoạn trích không trả lời được
SC-05   4   ✓    ✓   ✓      0      THÔNG  PASS    n/a*    —      —
----------------------------------------------------------------------------------------------------
XF-01   4   ✓    ✓   ✓      3      THÔNG  FAIL    0.00    0/1    nhãn golden cố ý sai (expected + #c999 bịa)  ← PHẢI đỏ (thiết kế)
XF-02   4   ✓    ✓   ✓      3      THÔNG  FAIL    n/a*    —      KB cố ý hỏng fence → conjunct no_leak bắt được  ← PHẢI đỏ (thiết kế)
----------------------------------------------------------------------------------------------------
ĐẤU-NỐI (wiring) : 5/5 THÔNG
CHẤT-LƯỢNG TRÊN FIXTURE ĐỌC PROMPT: 4/5 PASS — chấm trên ExtractiveFakeLLM, KHÔNG phải model thật
RED-CHECK : 2/2 FAIL → bộ chấm biết đỏ ✓
```

Exit code `0` (script's own CLI-hygiene gate — luồng thông + RED-CHECK bắt đúng; **không** có nghĩa
mọi case đạt quality gate, xem `exit code` trong docstring script).

**Đọc bảng thế nào:** `SC-04` đỏ (`success=FAIL`) là **kết quả đo thật** trên `ExtractiveFakeLLM`
(fixture chỉ chép đoạn trích đầu tiên, không có năng lực từ chối) — không phải lỗi hạ tầng, cột
`quy-trách-nhiệm` nói rõ đỏ vì tầng nào. 2 case `XF-*` **PHẢI đỏ theo thiết kế** (negative-control của
chính bộ chấm) — nếu chúng PASS thì bộ chấm mới là thứ đang hỏng.

**Giới hạn đã biết (khai trong chính docstring script, không giấu ở D10):**
`ExtractiveFakeLLM` là fixture, không phải model thật — mục "≥1 case FAIL với LLM thật" (#59) còn
treo, cần 1 lượt Gemini thật (P9). `citation_accuracy` nhánh từ-chối in `n/a*` vì hằng cứng 1.0 chưa
đo gì (điểm gãy #9, agenda freeze D11).

---

## 2. INV-1 — client-khai-tenant bị ignore (vai SWE)

```bash
pytest packages/workbench/tests/test_wiring_d8.py::test_resolve_tenant_ignores_client_declared_tenant_in_body -v
pytest packages/kb/tests/test_tenant_wall.py::test_tenant_la_tra_rong_fail_closed -v
```

**Đã chạy thật (phiên soạn tài liệu):**

```text
packages/workbench/tests/test_wiring_d8.py::test_resolve_tenant_ignores_client_declared_tenant_in_body PASSED
packages/kb/tests/test_tenant_wall.py::test_tenant_la_tra_rong_fail_closed PASSED
```

Bài đầu chứng minh SWE: server resolve tenant từ session, **không đọc tenant client tự khai trong
body**. Bài sau chứng minh DE: `kb.search` với tenant lệch fail-closed → **trả rỗng**, không leak.

---

## 3. Trace Postgres — timeline đọc lại đúng thứ tự (vai DE) — [CHƯA CHẠY LẠI PHIÊN NÀY]

Cần Docker (không có ở máy soạn tài liệu lúc này — daemon không chạy). Lệnh dưới **đã được DE xác
nhận chạy thật hôm nay** (`packages/kb/docs/evidence-d9.md` §1, "68 passed" bao gồm 2 bài này):

```bash
docker compose -f docker-compose.test.yml up -d --wait
export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test

pytest packages/kb/tests/test_trace_reader.py::test_db_doc_lai_dung_thu_tu_va_bao_0_gap -v   # rebuild-read, 0-gap
pytest packages/kb/tests/test_trace_reader.py::test_db_khong_doc_cheo_tenant -v              # cách ly tenant khi đọc trace
```

⚠️ **Trước gate thật (31/07), người cầm demo phải tự chạy lại 2 lệnh này** — tài liệu này không thay
được một lượt chạy thật ngay tại chỗ. Không có Docker = không demo được leg này, không phải "coi như
qua".

---

## 4. Bảng điểm — 1 nguồn số (vai AIE-2)

Đã nằm trong §1 (cột `success`/`cit_acc` của script `e2e_smoke_eval.py`) — **không** phải bảng điểm
tính rời. Nguồn citation để chấm luôn đọc từ `citations_from_trace(case_run.events)` — trace do
interpreter (AIE-1) emit, DE lưu — đúng luật "một nguồn số" (`day-09.md:42`).

Chạy lại 2 lần để xác nhận ra cùng số (bảng điểm ổn định — DoD `day-09.md:54`):

```bash
python apps/studio/scripts/e2e_smoke_eval.py   # lần 1
python apps/studio/scripts/e2e_smoke_eval.py   # lần 2, so THÔNG/PASS/cit_acc từng dòng phải giống hệt
```

---

## 5. Dữ liệu tại từng bước — cái gì, ở đâu

Ví dụ thật lấy từ đúng lần chạy §1 ở trên, case `SC-01` (không bịa số):
`run_id=c2ae813b…`, tenant `ankor` (`a0000000-0000…`), 3 chunk, citation `ankor-leave-001#c1`.

| # | Bước | Ai giữ | Hàm | Dữ liệu VÀO | Dữ liệu RA (ví dụ thật SC-01) | Sống ở đâu |
|---|---|---|---|---|---|---|
| 1 | Form → Recipe | SWE | `create_recipe_d4(agent_id, tenant_id, scope, query)` | `query="Nhân viên xin nghỉ phép..."`, `tenant_id=UUID(ankor)`, `scope="t/public"` | `Recipe{agent_id, tenant_id, dag: 4 Node (n1 kb-retrieve → n2 llm-step → n3 tool-call → n4 end) qua 3 Edge, kb_binding, agent_config}` | in-memory (pydantic `Recipe`), chưa persist — recipe-store thật là nợ đã biết ở mục cuối |
| 2 | Resolve identity | SWE (`tenant_wall.resolve_session`) | `resolve_session({tenant_id, user, roles})` | dict thô từ session/harness | `session_context` (tenant server-resolve) — **INV-1**: nếu `recipe.tenant_id` lệch với session, session thắng, không phải recipe | in-memory, tách biệt khỏi `Recipe.tenant_id` (đó chính là điểm engine#12 chốt) |
| 3 | `kb-retrieve` (node n1) | AIE-1 gọi, DE trả | `interpreter.run()` → `kb_search.search(query, tenant_id **từ session**, section_roles, top_k=3)` | tenant từ session (không phải `node.params`/recipe) | `list[KbSearchResultItem]` — 3 item, mỗi item `{chunk_id: "ankor-leave-001#c1", text: "...", score: float, tenant_id, section_role: "public"}` | in-memory trong `RunState`; nguồn thật là `kb.chunks` (Postgres, `packages/kb/src/studio_kb/schema.py`) qua `StaticKbSearch` |
| 4 | `llm-step` (node n2) | AIE-1 | `build_prompt(query, chunks)` → `llm.complete(prompt)` | prompt render `[chunk_id]\ntext` từ 3 chunk | `{answer: str, citations: ["ankor-leave-001#c1"], refused: False}` — citations ở đây là LLM **tự khai**, chưa phải số chấm điểm | in-memory, ghi vào `RunResult.final_state["n2"]` |
| 5 | `tool-call`/`end` (n3, n4) | AIE-1 | stub dispatch + terminate | — | `{"tool": ..., "status": "stub-dispatched"}`, `{"terminated": True}` | `RunResult.final_state["n3"]`/`["n4"]` |
| 6 | Mỗi node emit trace | AIE-1 phát, DE lưu | `trace_writer.write(TraceEvent)` sau MỖI node | `node_id, node_type, outputs, tokens, cost, citations` của node đó | 4 dòng `TraceEvent`, `run_id=c2ae813b…` chung cho cả 4, `ts` tăng dần µs, `inputs_hash=sha256(...)` | §1 demo: `_NoopTraceWriter` — chỉ giữ tạm trên `RunResult.events` (RAM, mất khi process thoát). §3 demo (Postgres thật): `PgTraceWriter` — `INSERT INTO obs.trace_events` (bảng thật, xem schema dưới) |
| 7 | Đọc lại trace (chỉ leg §3) | DE | `PgTraceReader.read_run(run_id)` | `run_id` | 4 `TraceEvent` **đọc lại từ Postgres**, đúng thứ tự `ts`, báo thiếu nếu 0-gap vỡ | Postgres `obs.trace_events`, WHERE `run_id = ...` |
| 8 | Adapter map | AIE-1+AIE-2 (`studio_app.eval_adapter`) | `EngineAgentRunner.run_case()` | `RunResult{final_state, events}` | `CaseRun{answer: AgentAnswer{answer, citations, refused}, events: list[TraceEvent]}` | in-memory, composition root (`studio_app`) — nơi duy nhất được import cả 4 quadrant |
| 9 | Citations CHẤM ĐIỂM | AIE-2 | `citations_from_trace(case_run.events)` | 4 `TraceEvent` | `["ankor-leave-001#c1"]` — đọc lại từ **trace** (`event.citations`), KHÔNG phải `answer.citations` ở bước 4 (agent tự khai) | in-memory, tính lại mỗi lần chấm — đây chính là "1 nguồn số" |
| 10 | Chấm điểm | AIE-2 | `score_case(case, answer, grounded_citations)` | `GoldenCase` (nhãn kỳ vọng) + citations bước 9 | `success=True, citation_accuracy=1.00` | in-memory; publish thật (`Scorecard`/`Gate`) là tầng ngoài script này |

**Bảng `obs.trace_events` thật (leg §3, Postgres) — cột khớp `TraceEvent` từng trường:**

```sql
CREATE TABLE obs.trace_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    tenant_id UUID NOT NULL,      -- NOT NULL, INV-1: không node nào thiếu tenant
    node_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    ts TEXT NOT NULL,             -- ISO8601, đơn điệu trong 1 run_id
    inputs_hash TEXT NOT NULL,
    outputs JSONB NOT NULL DEFAULT '{}'::jsonb,
    tokens JSONB NOT NULL DEFAULT '{}'::jsonb,
    cost NUMERIC NOT NULL DEFAULT 0,
    citations JSONB               -- chỉ non-null ở node llm-step
);
```

**Điểm hay bị hiểu nhầm — 2 nơi "citations" khác nhau, KHÔNG phải 1 số:**
`answer.citations` (bước 4, LLM tự khai trong `final_state`) và `event.citations` đọc qua
`citations_from_trace` (bước 9, dùng để chấm điểm) **là 2 field khác nhau ở 2 tầng khác nhau** — chỉ
trùng giá trị khi LLM không nói dối. `score_case` cố tình đọc **trace**, không đọc `answer`, đúng luật
"chấm theo mặt quan sát thật" (`docs/day-05-thonluong-report.md` §1) chứ không tin lời agent tự khai.

---

## Nợ đã biết của chính demo script này (khai ra, không giấu)

- **§1 không đi qua Postgres** — dùng `_NoopTraceWriter` cục bộ để không cần Docker cho luồng chính.
  §3 là leg riêng chứng minh trace Postgres, **chưa hợp nhất vào cùng 1 lệnh chạy** — người demo D10
  chạy 2 lệnh (§1 rồi §3), không phải 1 lệnh duy nhất xuyên hết. Hợp nhất là việc nên làm ở S2 nếu
  D10 cần đúng nghĩa "1 luồng" ở mức lệnh, không chỉ ở mức khái niệm.
- **Recipe dựng qua `_demo_golden_set()` in-code**, chưa đọc `packages/kb/golden/smoke-5.yaml` hay
  bộ 10 case của DE (`smoke-10.yaml`) — chặn bởi `pyyaml` chưa khai được ở `apps/studio` (`uv.lock`
  nằm ở repo cha), xem docstring `e2e_smoke_eval.py` "Nợ đã biết".
- **`ExtractiveFakeLLM`, không phải model thật** — xem §1 "Giới hạn đã biết". Đây chính là "điểm
  skeleton sẽ gãy khi lên Sprint 2" phần AIE-2/AIE-1 phải nêu ở D10 (`day-10.md:48`): quality số hiện
  tại chấm trên một double, không phải năng lực model thật.
