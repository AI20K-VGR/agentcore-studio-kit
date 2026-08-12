---
phase: 2
title: "D19 Tokens Idempotent Retrieval Failure Modes"
status: pending
plan: 260812-1133-d18-d20-aie1-engine-daily-prs
created: 2026-08-12
harness_version: 5.3.0
harness_kit_digest: 251ed307796039124b44d71759b3f62d8bb9135c4bf3053156e38798587a50a8
harness_schema_version: 1.0
---

# Phase 2 — D19: token accounting thật + idempotent-qua-replay + failure-mode retrieval

Issue: kit#121. DoD ngày (chung 4 người): Cost cùng-1-số khớp UI-test↔trace (tái lập) ·
hardening happy-path · failure-mode list nhìn đầu (honest-TODO). Việc AIE-1: *"Executor emit
`tokens` chuẩn (nguồn cost); xác nhận idempotent qua replay; ghi failure-mode retrieval."*

## Setup bắt buộc trước khi làm bất kỳ việc gì

```
git -C packages/engine fetch origin
git -C packages/engine switch -c aie-1/day19-tokens-idempotent-failure-modes origin/main
```
Nhánh này chỉ tồn tại SAU KHI PR phase 1 đã merge (`origin/main` lúc này đã chứa field
`llm_source` của phase 1) — chạy `git -C packages/engine log --oneline -3 origin/main` xác nhận
commit phase 1 đã có trên `main` trước khi bắt đầu, đừng giả định.

## Overview

`LlmStepExecutor.execute()` (đọc lại state thật đầu phase — có thể đã đổi shape sau phase 1's
field `llm_source`) hard-code `Tokens(prompt=0, completion=0)` — chưa có accounting thật. DE's
D19 task (kit#120, "chủ công cost-lineage") tính `cost` từ `tokens` engine phát ra
(`DL-11.A1-5` đã chốt design này từ D11: "executor chỉ cấp `tokens`, sink tính `cost`") — nếu
`tokens` vẫn `(0, 0)` cứng, cost DE tính ra sẽ luôn 0, không phải "cost cùng-1-số" thật.

**Test hiện có sẽ cố ý bị làm đỏ rồi sửa cùng lúc** (không phải regression bỏ sót):
`test_executors_behavior.py:114` hiện khoá `result["tokens"] == Tokens(prompt=0, completion=0)`
— literal cũ. Đây là test PHẢI sửa trong phase này, nằm trong Files bên dưới.

3 việc con của issue, độc lập nhau về file/test:

1. **Token accounting thật** — thay `Tokens(0, 0)` bằng số đếm thật từ prompt+answer.
2. **Idempotent qua replay** — chạy cùng 1 fixture-backed case 2 lần → cùng `tokens`.
3. **Failure-mode retrieval** — tài liệu (không phải code) liệt kê cách `kb-retrieve` có thể hỏng
   ở tầng engine, mỗi mục có anchor code/test thật đi kèm.

## Files

- **Modify**: `packages/engine/src/studio_engine/executors.py::LlmStepExecutor.execute()` —
  tính `Tokens(prompt=N, completion=M)` thật. Nguồn đếm: whitespace-split trên `prompt`/`answer`
  (deterministic, không cần tokenizer gateway thật — gateway không ship trong kit, R-6). Ghi 1
  dòng quyết định trong PR + docstring: "đếm theo split-whitespace, không phải tokenizer
  BPE/model thật — xấp xỉ đủ dùng cho cost-lineage nội bộ, DE cần biết đơn giá tính trên gì."
- **Modify**: `packages/engine/tests/test_executors_behavior.py:114` — cập nhật assertion khớp
  hành vi mới (không còn `Tokens(0, 0)` cứng); nếu file có nhiều assertion literal khác liên
  quan tokens, rà toàn file trước khi sửa (không chỉ đúng 1 dòng đã biết).
- **Create**: `packages/engine/tests/test_llm_step_token_accounting.py` — test tokens thật +
  idempotent qua replay.
- **Create**: `packages/engine/docs/design-notes/aie1-day19-retrieval-failure-modes.md` — theo
  đúng convention đã có (`packages/engine/docs/design-notes/aie1-dayNN-*.md`), liệt kê
  failure-mode của `KbRetrieveExecutor`: tenant_id không phải UUID (đã có `PermissionError` ở
  `executors.py:169-177` — ghi lại, không phải case mới), `section_roles` rỗng/malformed
  (deny-all `[]`, đã có ở `executors.py:180`), `KbSearch.search()` raise (chưa bắt ở tầng
  executor — dispatch qua `interpreter.py:375` không có try/except quanh nó, ghi rõ đây là
  "chưa xử lý" không phải "đã xử lý"), retrieval trả `[]` hợp lệ (không phải lỗi, theo
  `packages/kb/docs/contracts/kb-search.v0.md §6.1`) vs retrieval trả `[]` do bug (không phân
  biệt được ở tầng engine hôm nay — ghi honest-TODO).

## TDD

- **Tests-before (RED)**:
  1. Test token thật: gọi `LlmStepExecutor.execute()` với 1 case có prompt/answer cố định →
     assert `tokens.prompt > 0` và `tokens.completion > 0` (RED vì hiện tại luôn `0, 0`; đồng
     thời `test_executors_behavior.py:114` cũng đỏ cùng lúc — dự kiến, sửa chung 1 commit).
  2. Test idempotent: chạy cùng input 2 lần trong cùng process → `tokens` 2 lần bằng nhau; VÀ
     qua `subprocess` 2 `PYTHONHASHSEED` khác nhau (mẫu `DL-11.A1-9`) → `tokens` bằng nhau qua
     tiến trình, không chỉ trong 1 lần chạy.
  3. Test tồn tại + không rỗng của design-note (khoá "đã viết", KHÔNG khoá nội dung/anchor bên
     trong — nội dung do người review đọc bằng mắt, test không tự động verify từng `file:line`
     trong prose là đúng).
- **Implement** → xanh. Không đổi shape `Tokens` (`prompt`/`completion` đã đủ, `packages/
  contracts/src/studio_contracts/trace.py:17-21` — không cần field mới, không chạm `contracts`).
- **Regression** (chạy từ kit-root):
  ```
  uv run --package agentcore-studio-engine pytest packages/engine/tests -q
  uv run python packages/engine/scripts/run_golden_batch.py
  uv run ruff check packages/engine
  uv run ruff format --check packages/engine
  uv run mypy packages/engine
  uv run lint-imports
  ```
  `run_golden_batch.py` xác nhận D16 harness không đỏ — nó đi qua `LlmStepExecutor.execute()`
  cho phần tokens/citations (dù dùng `_GoldenAwareLLM` cho phần answer), nên đổi cách tính
  tokens ở đây phải giữ harness đó xanh.

## PR (bắt buộc — không gộp với phase 1/3)

1. Đã tạo branch ở bước Setup (`aie-1/day19-tokens-idempotent-failure-modes`, từ `origin/main`
   SAU KHI phase 1 merge).
2. Commit conventional, dẫn `kit#121`.
3. `gh pr create --repo AI20K-VGR/agentcore-studio-engine --base main --head
   aie-1/day19-tokens-idempotent-failure-modes`.
4. Xác nhận `gh pr checks <N> --repo AI20K-VGR/agentcore-studio-engine` xanh THẬT trước khi báo
   done.
5. Reviewer: DE (Đông Anh) — bên tiêu thụ trực tiếp `tokens` cho cost aggregator (kit#120, cùng
   ngày).
6. **Merge PR NÀY xong rồi mới chạy `/hs:cook <plan> --phase 3`.**

## Success

- [ ] `tokens.prompt`/`tokens.completion` > 0 cho case có nội dung thật, đếm được lại từ
      prompt/answer (không phải placeholder).
- [ ] `test_executors_behavior.py:114` cập nhật khớp hành vi mới, không còn khoá literal cũ.
- [ ] Idempotent xác nhận qua ≥2 lần gọi cùng process + ≥2 `PYTHONHASHSEED` khác nhau.
- [ ] Design-note failure-mode retrieval tồn tại, không rỗng, mỗi mục dẫn `file:line` cụ thể
      (review bằng mắt xác nhận đúng — không phải test tự động verify).
- [ ] `run_golden_batch.py` (D16) vẫn xanh sau khi đổi cách tính tokens.
- [ ] 5 lệnh regression sạch. PR riêng mở + merge, CI xanh xác nhận qua `gh pr checks`.

## Risks

- **[M] Chọn cách đếm token (word-split) là quyết định tự chọn, không có "đúng" tuyệt đối** vì
  gateway thật không ship trong kit — ghi rõ trong PR + docstring, để DE biết đơn giá tính trên
  gì.
- **[L]** Phase 1 có thể đã đổi shape output `LlmStepExecutor.execute()` (thêm `llm_source`) —
  đọc lại file thật đầu phase 2 (đã nhắc ở Setup + Overview), không giả định state trong plan
  này còn khớp 100% nếu phase 1 lệch khỏi kế hoạch lúc thực thi.
