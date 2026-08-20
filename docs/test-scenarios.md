# Test Scenarios — agentcore-studio-kit

> **Ghi chú nguồn:** tài liệu này viết dựa trực tiếp trên `docs/srs.md` (đọc ngày 2026-08-20), theo đúng
> khung 8-bước spine (UC-01 → UC-07). Mỗi *Main flow* / *Exception flow* trong SRS được tách thành 1
> kịch bản riêng (nguồn: **SRS**). Ngoài ra, với các FR/NFR đánh dấu `PARTIAL`/`SPEC` trong SRS mục 5.1,
> có thêm kịch bản mô tả **hành vi thật hiện tại** (nguồn: **Suy luận**) — các kịch bản này KHÔNG giả
> định hệ thống làm đúng như thiết kế lý tưởng, mà ghi lại đúng những gì code thật trả về, để không tạo
> test-scenario sai lệch với thực tế.
>
> **Nhãn nguồn kịch bản:**
> - `[SRS]` — dịch trực tiếp từ Main/Exception flow đã có trong `srs.md`, không thêm suy luận.
> - `[Suy luận]` — bổ sung từ ghi chú `PARTIAL`/`SPEC`/"chưa xác nhận" trong SRS; cần verify thật (chạy
>   qua code) trước khi dùng làm căn cứ PASS/FAIL chính thức ở gate.
>
> **Trạng thái** (copy nguyên từ SRS, không tự nâng cấp): `WIRED` / `PARTIAL` / `SPEC`.

## Tổng quan

| UC | Chức năng | Số kịch bản |
|---|---|---|
| UC-01 | Login | 3 |
| UC-02 | Ingest | 3 |
| UC-03 | Build recipe | 3 |
| UC-04 | Run + Trace | 4 |
| UC-05 | Eval | 3 |
| UC-06 | Gate / Publish | 3 |
| UC-07 | Chat | 4 |

---

## UC-01 — Login

#### SC-UC01-01 — Login thành công `[SRS]`
- **Actor:** bất kỳ user đã có account
- **Precondition:** `core.users` đã tồn tại
- **Bước:**
  1. Nhập email/password ở `Login.tsx`
  2. `POST /api/auth/login` verify bcrypt + rate-limit theo IP
  3. Server ký JWT HS256 (`STUDIO_JWT_EXPIRE_MINUTES` mặc định 480 phút)
  4. Client lưu `access_token`+`tenantId`+`tenantName`+`user`+`roles` vào `localStorage`
- **Kết quả kỳ vọng:** session hợp lệ; mọi request sau đó đính `Authorization: Bearer <token>` và
  middleware fail-closed resolve đúng tenant
- **Trạng thái:** WIRED
- **Tham chiếu:** `auth.py:98`

#### SC-UC01-02 — Sai mật khẩu / rate-limit `[SRS]`
- **Actor:** bất kỳ user
- **Precondition:** đã có tài khoản (hoặc không)
- **Bước:** 1. Nhập sai password nhiều lần liên tiếp từ cùng 1 IP
- **Kết quả kỳ vọng:** 401 (sai mật khẩu) hoặc 429 (rate-limit) — không lưu session, không phát JWT
- **Trạng thái:** WIRED
- **Tham chiếu:** `auth.py:98`

#### SC-UC01-03 — Token hết hạn, không có refresh-token `[Suy luận]`
- **Actor:** user đã login
- **Precondition:** đã có `access_token` hợp lệ
- **Bước:** 1. Giữ session quá 480 phút (`STUDIO_JWT_EXPIRE_MINUTES`) rồi gọi API bất kỳ
- **Kết quả kỳ vọng:** request bị từ chối (401), KHÔNG có cơ chế refresh-token tự động — user buộc phải
  login lại từ đầu, mất mọi state client chưa lưu (VD: recipe đang vẽ dở trên canvas)
- **Trạng thái:** WIRED (theo thiết kế "không có refresh-token" ghi trong SRS) — cần verify UI có cảnh
  báo trước khi hết hạn hay không
- **Tham chiếu:** UC-01 main flow bước 3, `auth.py:98`

---

## UC-02 — Ingest (nạp tài liệu vào KB)

#### SC-UC02-01 — Upload tài liệu thành công `[SRS]`
- **Actor:** Admin/Superadmin
- **Precondition:** đã login, có quyền admin trên tenant
- **Bước:**
  1. Upload document qua UI Admin
  2. `POST /api/admin/documents` (multipart)
  3. `KbPipeline.chunker → embed_invoke → index` ghi `kb.chunks` đúng `tenant_id`
- **Kết quả kỳ vọng:** KB tenant có thêm chunk tìm kiếm được, dùng lại ở UC-04
- **Trạng thái:** WIRED
- **Tham chiếu:** FR-KB-03, `kb/pipeline.py:40-89`

#### SC-UC02-02 — Consent purge, chưa xác nhận route HTTP `[SRS]`
- **Actor:** Admin/Superadmin
- **Precondition:** tenant đã có chunk trong `kb.chunks`
- **Bước:** 1. Gọi `KbPipeline.consent_purge` để xoá toàn bộ chunk của 1 tenant
- **Kết quả kỳ vọng:** toàn bộ chunk tenant đó bị xoá khỏi `kb.chunks`
- **Trạng thái:** WIRED (hàm) / **chưa xác nhận** có route HTTP riêng trong danh sách 23 route đã verify
  — kịch bản này PHẢI verify qua API surface thật trước khi coi là "người dùng cuối gọi được", không
  chỉ vì hàm Python tồn tại
- **Tham chiếu:** FR-KB-04, `kb/pipeline.py:91-119`

#### SC-UC02-03 — UI ingest: tên file "Placeholder", chưa xác nhận hoàn chỉnh `[Suy luận]`
- **Actor:** Admin/Superadmin
- **Precondition:** đã login
- **Bước:** 1. Mở tab Ingest trên UI Admin, kiểm tra toàn bộ luồng upload → feedback → danh sách document
- **Kết quả kỳ vọng:** backend route thật đã wire (SC-UC02-01 PASS), nhưng UI thực tế nằm trong file tên
  `DocumentsPlaceholderTab.tsx` — cần kiểm tra bằng mắt/manual test xem UI đã hoàn chỉnh hay vẫn ở dạng
  khung trước khi dùng cho demo Day-25 (P1 clean-clone demo)
- **Trạng thái:** WIRED (backend) / UI chưa verify
- **Tham chiếu:** UC-02 Ghi chú, `srs.md` dòng 219-220

---

## UC-03 — Build recipe (tạo + cấu hình + vẽ agent)

#### SC-UC03-01 — Dựng recipe hợp lệ `[SRS]`
- **Actor:** Tenant Builder
- **Precondition:** đã login, role builder/admin
- **Bước:**
  1. Bấm "Tạo agent" → đặt tên `agent_id` → khung rỗng trên canvas
  2. Điền 8 field cấu hình (agentId, instructions, model, toolWhitelist, kbId, goldenSetRef,
     successThreshold, citationThreshold)
  3. Kéo-thả node (6 loại), nối cạnh
  4. `graph_lint()` chạy real-time, không báo lỗi
- **Kết quả kỳ vọng:** có 1 `WireRecipe` hợp lệ, nút Test/Publish mở khoá
- **Trạng thái:** WIRED
- **Tham chiếu:** FR-WB-01, FR-WB-02, UR-01, UR-02, `workbench/validator.py:49-165`

#### SC-UC03-02 — Vi phạm từng luật trong 7 luật `graph_lint` `[SRS]`
- **Actor:** Tenant Builder
- **Precondition:** đang vẽ recipe trên canvas
- **Bước (7 case con, mỗi case vi phạm đúng 1 luật):**
  1. Node-type sai (không thuộc 6 loại hợp lệ)
  2. Edge không resolve được (trỏ tới node không tồn tại)
  3. Có >1 start-node
  4. Có >1 outgoing-edge trên cùng 1 node
  5. Đồ thị có cycle
  6. Có nhánh walk không kết thúc ở node `end`
  7. `tool-call` gọi tool ngoài `toolWhitelist`
- **Kết quả kỳ vọng:** mỗi case → banner đỏ, khoá nút Test/Publish, không có đường vòng lấy được JSON
  recipe khi đang đỏ
- **Trạng thái:** WIRED
- **Tham chiếu:** FR-WB-01, `workbench/validator.py:49-165`

#### SC-UC03-03 — Đối xứng lint client-side vs server-side `[Probe]`
- **Actor:** Tenant Builder
- **Precondition:** recipe đang vi phạm 1 trong 7 luật
- **Bước tự động (đã có sẵn script, không cần viết mới):**
  1. `cd apps/web && pnpm check-parity` (hoặc `npm run check-parity`) — chạy
     `apps/web/scripts/check-lint-parity.ts`
  2. Script dựng 9 biến thể recipe (1 happy + 8 vi phạm, mirror đúng
     `packages/workbench/tests/test_wiring_d12.py` + `test_graph_lint.py`), chạy `graphLint.ts`
     (client) trên từng biến thể, so `rule` trả về với đúng luật Python raise
- **Kết quả kỳ vọng:** UR-02 yêu cầu lint tức thời client-side "không cần round-trip server", nghĩa là
  2 bên phải cho cùng kết quả trên cả 7 luật
- **Đã chạy thật (2026-08-20):** `pnpm check-parity` → **9/9 case khớp**, PASS sạch — bằng chứng thật,
  không còn là suy luận
- **Trạng thái:** WIRED — nhưng script **không nằm trong CI** (grep `.github/` không match) — không ai
  chạy tự động khi có PR sửa 1 trong 2 bản lint; có thể lệch âm thầm nếu 1 bên sửa mà quên bên kia,
  đến lúc chạy tay mới phát hiện
- **Tham chiếu:** UR-02, FR-WB-01/02, `apps/web/scripts/check-lint-parity.ts`

---

## UC-04 — Run + Trace

#### SC-UC04-01 — Test recipe chạy thành công, trace khớp `[SRS]`
- **Actor:** Tenant Builder
- **Precondition:** recipe hiện tại pass `graph_lint`
- **Bước:**
  1. Bấm "Test" → `POST /api/runs` → `interpreter.run()` walk DAG, ghi 1 `TraceEvent`/node
  2. Interpreter inject `session_context.tenant_id`+`section_roles` đè `node.params` sau spread
  3. Client GET riêng `/api/runs/{run_id}` (`fetchTrace`) để xác nhận wiring
  4. `TraceViewer` hiện `agentIdsMatch`+`wiringOk`+`monotonic`
- **Kết quả kỳ vọng:** `RunResult`/trace đầy đủ, khớp đúng `run_id`/`agent_id`/`tenant_id`
- **Trạng thái:** WIRED
- **Tham chiếu:** FR-ENGINE-01..07, UR-03, `engine/interpreter.py:160-460`

#### SC-UC04-02 — Cross-tenant refusal (fence proof) `[SRS]`
- **Actor:** Tenant Builder (đóng vai kiểm chứng fence)
- **Precondition:** câu hỏi chỉ trả lời được bằng KB của tenant khác
- **Bước:**
  1. Chạy Test với câu hỏi mà đáp án chỉ nằm trong KB tenant khác
  2. `KbRetrieveExecutor` trả 0 chunk (RLS + `session_context` chặn)
  3. `LlmStepExecutor` không trích được citation
- **Kết quả kỳ vọng:** `refused=true`, KHÔNG bịa câu trả lời; event vẫn ghi đủ vào trace làm audit
- **Trạng thái:** WIRED
- **Tham chiếu:** UR-04, FR-ENGINE-02/03, `engine/executors.py:87-183,222-366`

#### SC-UC04-03 — Node `condition`/`tool-call`/`hitl-pause` — hành vi thật khác thiết kế `[Suy luận]`
- **Actor:** Tenant Builder
- **Precondition:** recipe có chứa 1 trong 3 loại node này
- **Bước:**
  1. Chạy recipe có node `condition` với 2 nhánh khác nhau theo `when`
  2. Chạy recipe có node `tool-call` khi không có dispatcher wire sẵn
  3. Chạy recipe có node `hitl-pause`
- **Kết quả kỳ vọng (ghi đúng thực tế, KHÔNG phải kỳ vọng lý tưởng):**
  1. `ConditionExecutor` evaluate `when` nhưng KHÔNG branch-walk theo `result` — walk vẫn đi theo cạnh
     mặc định
  2. `ToolCallExecutor` raise nếu `dispatcher=None`; chỉ chạy được khi walk thật đã wire dispatcher sẵn
  3. `HitlPauseExecutor` trả shape `{"paused": true}` nhưng KHÔNG dừng walk thật, không có resume —
     dùng kịch bản này để chứng minh P4 (HITL-pause) chưa production-ready, không phải để báo PASS
- **Trạng thái:** PARTIAL (1, 2) / PARTIAL-SPEC (3)
- **Tham chiếu:** FR-ENGINE-04 (`executors.py:429-523`), FR-ENGINE-05 (`executors.py:538-566`),
  FR-ENGINE-06 (`executors.py:569-589`); production-block P4, `CLAUDE.md` mục 6

#### SC-UC04-04 — Cost mỗi event luôn 0.0 `[Suy luận]`
- **Actor:** Tenant Builder / Mentor (kiểm tra cost tracking)
- **Precondition:** có ≥1 run hoàn tất
- **Bước:** 1. Mở `TraceViewer`, kiểm tra trường `cost` của từng event
- **Kết quả kỳ vọng:** `cost` luôn = `0.0` (hằng số viết chết `_NO_COST=0.0`) — đây LÀ hành vi đúng thiết
  kế hiện tại (D19/kit#120 cost-lineage chưa làm), KHÔNG phải bug UI; token count thì đã đo thật
- **Trạng thái:** PARTIAL
- **Tham chiếu:** NFR "Cost tracking", `srs.md` dòng 188, 254-255

---

## UC-05 — Eval (chấm điểm golden set)

#### SC-UC05-01 — Chấm điểm, verdict PASS `[SRS]`
- **Actor:** Tenant Builder
- **Precondition:** recipe pass `graph_lint`, có `golden_set_ref` hợp lệ
- **Bước:**
  1. Bấm "Chấm điểm" → `POST /api/agents/{id}/evaluate`
  2. `load_golden_set()` nạp YAML, assert khớp `golden_set_ref`
  3. `EvalHarness.run()` loop từng case, `_score_case_run` (exact-match citation), fallback
     `LLMJudge.judge` nếu exact-match không bắt được
  4. `compute_scorecard()` gộp thành `Scorecard`
- **Kết quả kỳ vọng:** `Scorecard` hiện trên UI với `aggregate.success_rate`/`citation_accuracy`/
  `gate.verdict`
- **Trạng thái:** WIRED
- **Tham chiếu:** FR-EVAL-01..05, UR-05

#### SC-UC05-02 — `LLMJudge` quá cap/lỗi → descope `[SRS]`
- **Actor:** Tenant Builder
- **Precondition:** đang chạy eval, có case cần `LLMJudge` fallback
- **Bước:** 1. `LLMJudge` gọi lỗi hoặc vượt cap → raise `JudgeUnavailable`
- **Kết quả kỳ vọng:** case đó bị descope khỏi tính verdict — KHÔNG giả định pass hay fail, verdict
  cuối tính trên phần case còn lại
- **Trạng thái:** WIRED
- **Tham chiếu:** FR-EVAL-04, `evalhub/judge.py:141-274`

#### SC-UC05-03 — Vượt quota 100 case/ngày `[Suy luận]`
- **Actor:** Tenant Builder
- **Precondition:** đã chạy đủ 100 case judge trong ngày cho tenant
- **Bước:** 1. Chạy eval case thứ 101 trong cùng ngày (cùng tenant)
- **Kết quả kỳ vọng:** case thứ 101 trả `JudgeUnavailable` do vượt cap 100/ngày; nếu case này trùng
  `(case_id, actual)` với case đã cache trước đó trong ngày thì có thể trả kết quả cache thay vì gọi
  lại — cần verify thực tế thứ tự ưu tiên cache-vs-cap khi triển khai kịch bản
- **Trạng thái:** WIRED
- **Tham chiếu:** NFR "Judge quota", `srs.md` dòng 189

---

## UC-06 — Gate / Publish (+ Rollback)

#### SC-UC06-01 — Publish thành công `[SRS]`
- **Actor:** Tenant Builder
- **Precondition:** đã Chấm điểm verdict=PASS cho đúng recipe hiện tại
- **Bước:**
  1. Bấm "Publish" → `POST /api/agents/{id}/publish`
  2. `publish()` kiểm 5 điều kiện: `graph_lint` pass, `scorecard.recipe_hash` khớp `recipe_hash(recipe)`,
     `scorecard.agent_id` khớp, verdict≠FAIL
  3. Ghi 3 bảng cùng transaction: `wb.recipes`, `wb.recipe_versions`, `eval.scorecards`
- **Kết quả kỳ vọng:** agent có version mới live
- **Trạng thái:** WIRED
- **Tham chiếu:** FR-WB-03..05, UR-06, `workbench/publish.py:145-258`

#### SC-UC06-02 — Gate chặn + auto-rollback `[SRS]`
- **Actor:** Tenant Builder
- **Precondition:** verdict=FAIL, hoặc `recipe_hash` không khớp recipe hiện tại
- **Bước:** 1. Bấm "Publish" trong tình trạng trên
- **Kết quả kỳ vọng:** 409, `_reassert_last_published()` tự rollback về bản published gần nhất — hệ
  thống không treo ở trạng thái lỗi, version cũ vẫn giữ nguyên là bản live
- **Trạng thái:** WIRED
- **Tham chiếu:** FR-WB-03, UR-06, `workbench/publish.py:145-258`

#### SC-UC06-03 — Rollback thủ công `[SRS]`
- **Actor:** Tenant Builder
- **Precondition:** đã có ≥2 version trong `wb.recipe_versions`
- **Bước:** 1. `POST /api/agents/{id}/rollback` với `to_version` cụ thể
- **Kết quả kỳ vọng:** agent quay về đúng version chỉ định, ghi audit vào `wb.recipe_versions`
- **Trạng thái:** WIRED
- **Tham chiếu:** FR-WB-04, `workbench/publish.py:261-317`, `agents.py:180`

---

## UC-07 — Chat (dùng agent đã publish)

#### SC-UC07-01 — Chat thành công, có trích dẫn `[SRS]`
- **Actor:** Employee/End-user
- **Precondition:** agent có ≥1 version published
- **Bước:**
  1. Vào tab Chat, chọn agent (`GET /api/agents`)
  2. Gõ câu hỏi → `POST /api/agents/{id}/chat`
  3. Server chạy interpreter tương tự UC-04, trả `{answer, citations, refused, version, run_id}`
  4. Client GET `/api/runs/{run_id}` riêng để hiện trace
- **Kết quả kỳ vọng:** câu trả lời có trích dẫn rõ ràng, khớp trace
- **Trạng thái:** WIRED
- **Tham chiếu:** FR-STUDIO (`chat.py:77`), UR-07

#### SC-UC07-02 — Agent refused `[SRS]`
- **Actor:** Employee/End-user
- **Precondition:** câu hỏi không có tài liệu phù hợp trong KB scope
- **Bước:** 1. Gõ câu hỏi ngoài phạm vi KB → gửi chat
- **Kết quả kỳ vọng:** hiện rõ "Từ chối trả lời — không có tài liệu phù hợp", không im lặng bịa câu trả
  lời không căn cứ
- **Trạng thái:** WIRED
- **Tham chiếu:** UR-07, `chat.py:77`

#### SC-UC07-03 — Admin "Thử vai trò" chỉ được thu hẹp `[SRS]`
- **Actor:** Admin (test-role)
- **Precondition:** đang ở chế độ test-role trên tab Chat
- **Bước:**
  1. Mở panel "Thử vai trò", check 1 hoặc nhiều section hẹp hơn section thật của mình
  2. Gửi `as_roles` kèm request chat
  3. Thử set `as_roles` rộng hơn section thật (cố tình mở rộng)
- **Kết quả kỳ vọng:** case (1)(2) cho câu trả lời đúng theo scope hẹp hơn; case (3) server chỉ cho THU
  HẸP — request mở rộng vượt section thật phải bị chặn/không có hiệu lực, không được coi là request hợp
  lệ
- **Trạng thái:** WIRED
- **Tham chiếu:** UR-08, `chat.py::require_admin`

#### SC-UC07-04 — Lịch sử chat không xác nhận persist server-side `[Suy luận]`
- **Actor:** Employee/End-user
- **Precondition:** đã chat vài lượt trong session hiện tại
- **Bước:** 1. Reload trang (hoặc mở lại từ thiết bị khác cùng tài khoản) sau khi đã chat
- **Kết quả kỳ vọng:** SRS ghi nhận lịch sử chat "hiện trong session hiện tại (state client)" — cần
  verify thật xem sau reload lịch sử có mất hay không; nếu mất, đây là gap cần nêu rõ với mentor thay vì
  giả định có persist server-side
- **Trạng thái:** chưa xác nhận (không có FR ghi WIRED cho persist chat history)
- **Tham chiếu:** UC-07 Postcondition, `srs.md` dòng 307-308
