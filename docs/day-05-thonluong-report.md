# Day 5 — Kết quả thông luồng smoke-eval a→z (weekly demo #1)

> **Tác giả:** AIE-2 (Lưu Tiến Duy · `dholmes0207`) · **Ngày:** 2026-07-24 · **Sprint 1 / Day 5**
> **Phạm vi:** chứng minh smoke-eval chạy **xuyên 4 quadrant** trên luồng thật (đấu nối thông).
> **Kết quả:** **5/5 PASS** qua luồng thật; kb.search trả chunk đúng tenant/role; trace 4-event/run.

Báo cáo này trình bày: **format testcase**, **luồng chạy hiện tại**, **input/output**, và **kết quả**
chạy script `apps/studio/scripts/e2e_thonluong_demo.py`.

---

## 1. Format testcase (golden smoke-5, nguồn DE `callisto-smoke-5-v0`)

Mỗi case 8 field. Chia 2 nhóm: **input đẩy vào agent** và **nhãn kỳ vọng để chấm**.

| Field | Nhóm | Ý nghĩa |
|---|---|---|
| `case_id` | id | định danh case |
| `query` | **input** | câu hỏi gửi agent |
| `tenant` | **input** | tenant người hỏi (slug → resolve `tenant_id` UUID) |
| `section_roles` | **input** | quyền/vai người hỏi nắm |
| `expected_tenant` | nhãn | kho chứa đáp án (≠ `tenant` ⇒ refusal T1) |
| `expected_section_role` | nhãn | vai đáp án nằm ở (∉ `section_roles` ⇒ refusal T6) |
| `expected` | nhãn | cụm ngắn phải xuất hiện trong answer (hoặc `"refusal"`) |
| `expected_citation` | nhãn | `chunk_id` phải trích (mẫu số citation-accuracy; rỗng với refusal) |

**Nguyên tắc chấm (evalhub `score_case`):**
- **Trả-lời-được:** `success` = agent KHÔNG từ chối **VÀ** answer CHỨA cụm `expected` (token-contains).
  `citation_accuracy` = |`expected_citation` ∩ citations-đọc-từ-TRACE| / |`expected_citation`| (set-semantics).
- **Từ-chối** (T1 chéo-tenant HOẶC T6 chéo-vai): `success` = agent từ chối **VÀ** không citation trace nào
  thuộc `expected_tenant` (leak-check, fail-closed).
- **Nguồn citation để chấm = TRACE** (event trong `RunResult.events`), KHÔNG phải `answer.citations`
  (agent tự khai) — chấm theo *mặt quan sát thật*.

---

## 2. Luồng chạy hiện tại (a→z, xuyên 4 quadrant)

```
[input case]  query + tenant_id(UUID) + section_roles
   │
   ▼  workbench.create_recipe_d4(...)                 ← SWE: form→Recipe (tenant_id UUID)
   ▼  engine.interpreter.run(recipe, kb_search, llm, embedding, trace_writer)   ← AIE-1
   │     ├─ inject recipe.tenant_id → node kb-retrieve
   │     ├─ kb-retrieve → kb.StaticKbSearch.search(tenant_id, section_roles)     ← DE: fence RLS-UUID + role
   │     ├─ llm-step   → LLM.complete + grounding citation (∩ retrieved)
   │     ├─ tool-call / end
   │     └─ mỗi node emit 1 TraceEvent
   ▼  RunResult{run_id, events[4], final_state}
   ▼  studio_app.EngineAgentRunner.run_case → CaseRun{answer, events}   ← adapter #29 (AIE-1+AIE-2)
   ▼  evalhub.score_case(case, answer, citations-đọc-từ-trace)          ← AIE-2
   ▼  [output] SmokeResult{success, citation_accuracy}
```

**Phân quyền theo submodule:** workbench (recipe/SWE) · engine (interpreter/AIE-1) · kb (search+fence/DE) ·
studio_app (adapter+wiring/composition) · evalhub (scorecard/AIE-2). `.importlinter`: chỉ `studio_app`
được import cả 4 quadrant → adapter sống ở đây.

**Giới hạn skeleton hiện tại (đã biết, có chủ đích):**
1. **Recipe dựng in-code** bằng `create_recipe_d4` (chưa nối form UI / recipe-store thật).
2. **Interpreter walk CỨNG** (`_WALK_ORDER = kb-retrieve→llm-step→tool-call→end`), **chưa đọc
   `recipe.dag.edges`** để duyệt động — theo thiết kế, dynamic-DAG là **Day 6** (plan risk R2).
3. **LLM stub** (recorded per-case): llm-step chưa build prompt từ chunk retrieved nên LLM generic
   chưa phân biệt case → tạm cấp câu trả lời recorded. Prompt-grounding là bước tiếp (AIE-1/SWE).

---

## 3. Input / Output từng case

**Input (đẩy vào run):**

| case | query | tenant → tenant_id | section_roles | kiểm |
|---|---|---|---|---|
| SC-01 | "Nhân viên xin nghỉ phép cần báo trước bao lâu?" | ankor → `a0000000…01` | `[public]` | answerable |
| SC-02 | *(cùng query SC-01)* | borea → `b0000000…01` | `[public]` | tenant isolation |
| SC-03 | "Trưởng nhóm được duyệt chi tối đa bao nhiêu?" | ankor → `a0000000…01` | `[finance]` | đúng vai finance |
| SC-04 | "Hạn mức chi của Borea là bao nhiêu?" | ankor → `a0000000…01` | `[public]` | refusal T1 (chéo-tenant) |
| SC-05 | "Thang lương của công ty gồm những bậc nào?" | ankor → `a0000000…01` | `[engineering]` | refusal T6 (chéo-vai) |

**Output (từ luồng thật):**

| case | kb.search (#chunk) | refused | citations (grounded, từ trace) | success | citation_acc |
|---|---|---|---|---|---|
| SC-01 | 3 (ankor) | False | `[ankor-leave-001#c1]` | PASS | 1.00 |
| SC-02 | 3 (borea) | False | `[borea-leave-001#c1]` | PASS | 1.00 |
| SC-03 | 1 (ankor/finance) | False | `[ankor-expense-001#c2]` | PASS | 1.00 |
| SC-04 | 3 (ankor, **0 borea**) | True | `[]` | PASS | 1.00 |
| SC-05 | 0 (engineering ⊄ hr) | True | `[]` | PASS | 1.00 |

> **Đọc cột `#chunk` vs `citations`:** `#chunk` = số chunk kb.search **quét được**; `citations` = số chunk
> agent **trích**. SC-04 quét 3 chunk **ankor** (fence chặn borea → 0 leak) rồi **từ chối** → citations rỗng:
> hai số khác nhau, đều đúng. SC-04 chính là ca chứng minh `refused` phải đọc từ *sentinel khai báo* chứ
> không suy từ "retrieval rỗng" (retrieval có 3 chunk mà vẫn refuse đúng).

---

## 4. Kết quả chạy `e2e_thonluong_demo.py`

```text
==============================================================================
E2E ĐẤU NỐI THÔNG — smoke-5 qua luồng thật (workbench→engine→kb→trace→adapter→eval)
THẬT: recipe/interpreter/kb.search/trace/grounding/adapter/scorecard · STUB: LLM (recorded)
==============================================================================

SC-01 | tenant=ankor (a0000000-0000…) roles=['public'] | kb.search → 3 chunk
  TRACE: run_id=0f71bcae… · 4 event · 1 run_id duy nhất · ts đơn điệu=True  (1 run xuyên mọi node)
  # node_id node_type    ts (giờ.µs)       tenant_id      tok(p/c) cost  citations
  --------------------------------------------------------------------------------
  1 n1      kb-retrieve  10:59:37.911543Z  a0000000-0000… 0/0      0.00  —
  2 n2      llm-step     10:59:37.911636Z  a0000000-0000… 0/0      0.00  ankor-leave-001#c1
  3 n3      tool-call    10:59:37.911723Z  a0000000-0000… 0/0      0.00  —
  4 n4      end          10:59:37.911746Z  a0000000-0000… 0/0      0.00  —
  → refused=False | grounded citations=['ankor-leave-001#c1'] | success=True citation_acc=1.00

SC-02 | tenant=borea (b0000000-0000…) roles=['public'] | kb.search → 3 chunk
  → trace tenant_id=b0000000… (borea) · grounded=['borea-leave-001#c1'] · success=True acc=1.00

SC-03 | tenant=ankor roles=['finance'] | kb.search → 1 chunk (role finance → chỉ #c2)
  → grounded=['ankor-expense-001#c2'] · success=True acc=1.00

SC-04 | tenant=ankor roles=['public'] (hỏi Borea) | kb.search → 3 chunk (toàn ankor, 0 borea)
  → refused=True · grounded=[] · success=True acc=1.00

SC-05 | tenant=ankor roles=['engineering'] | kb.search → 0 chunk (engineering ⊄ hr salary)
  → refused=True · grounded=[] · success=True acc=1.00

------------------------------------------------------------------------------
case_id   success   citation_acc  #chunk (kb thật)
SC-01     PASS      1.00          3
SC-02     PASS      1.00          3
SC-03     PASS      1.00          1
SC-04     PASS      1.00          3
SC-05     PASS      1.00          0
------------------------------------------------------------------------------
5/5 PASS
```

**Bằng chứng "đấu nối thông" (mỗi case tự chứng minh từ trace):**
1. **1 `run_id` duy nhất** xuyên 4 event → một run chảy suốt workbench→engine→kb→trace.
2. **4 event** (kb-retrieve→llm-step→tool-call→end) → mọi node emit (DoD).
3. **`ts` đơn điệu tăng** → đúng thứ tự, 0-gap.
4. **`tenant_id` UUID nhất quán** mọi event (SC-02 = `b0000000…` borea) → tenant_id threaded xuyên submodule.
5. **Fence:** SC-04 quét ankor-only (0 borea leak, T1) · SC-05 engineering→0 chunk salary(hr) (T6).
6. **Grounding:** citations trên `llm-step` = chunk thực sự truy (∩ retrieved) → evalhub chấm từ trace.

---

## 5. THẬT vs STUB (minh bạch)

| Thành phần | Trạng thái |
|---|---|
| workbench recipe · engine interpreter · kb.search (fence tenant/role) · trace 4-event · grounding · adapter · scorecard | **THẬT** (chạy code các quadrant) |
| LLM | **STUB** (recorded per-case) — vì llm-step chưa build prompt từ chunk |
| tenant_id resolve | fixed UUID (`TENANT_IDS`: ankor `a0…01`, borea `b0…01`) — chưa seed `core.tenants` runtime |

Con số **5/5 minh hoạ đấu nối**; phần "chất lượng LLM thật" (prompt-grounding) là bước kế.

---

## 6. Follow-up (đã ghi nhận)

- **AIE-1/SWE:** llm-step build prompt từ retrieved chunk → LLM thật tự cite (bỏ canned).
- **AIE-1:** thêm `packages/engine/src/studio_engine/py.typed` (engine là package duy nhất thiếu → strict-mypy adapter báo import-untyped).
- **Day 6:** interpreter đọc `recipe.dag.edges` duyệt DAG động (bỏ walk cứng) + form→recipe→store thật.
- **Adapter #29:** `EngineAgentRunner` (`apps/studio`) mở PR co-author AIE-1 khi feature-branch merge main.

---

## 7. Cách chạy lại

Các fix Day-5 đang ở feature-branch (chưa merge main) → cần checkout franken-workspace:

```bash
cd <repo-cha>
git -C packages/workbench checkout main                              && git -C packages/workbench pull --ff-only
git -C packages/engine    checkout day5/fix-tenant-id-contract-sync  && git -C packages/engine  pull --ff-only
git -C packages/kb        checkout feat/day5-reader-d13              && git -C packages/kb      pull --ff-only
git -C packages/evalhub   checkout aie-2/day-05-scorecard-read-trace
uv sync
uv run python apps/studio/scripts/e2e_thonluong_demo.py
```

Kỳ vọng: **5/5 PASS**, cột `#chunk` = `3 / 3 / 1 / 3 / 0`.
