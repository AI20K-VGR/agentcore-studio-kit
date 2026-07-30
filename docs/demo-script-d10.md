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
