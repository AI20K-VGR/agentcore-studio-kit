---
phase: 1
title: "D18 Llm Step Fixtures"
status: completed
plan: 260812-1133-d18-d20-aie1-engine-daily-prs
created: 2026-08-12
completed_at: 2026-08-12
pr_link: "https://github.com/AI20K-VGR/agentcore-studio-engine/pull/23"
pr_commits: "52d8111, 8528883"
pr_branch: "aie-1/day18-llm-step-stability"
harness_version: 5.3.0
harness_kit_digest: 251ed307796039124b44d71759b3f62d8bb9135c4bf3053156e38798587a50a8
harness_schema_version: 1.0
---

# Phase 1 — D18: `llm-step` output ổn định cho judge + ES gateway-flag

Issue: kit#116. DoD ngày (issue body): LLM-judge cache+cap≤100 (AIE-2, không phải phần AIE-1) ·
agreement-check có số vs nhãn tay (AIE-2) · exact-match fallback sẵn (AIE-2) · **CI
deterministic** (phần thật AIE-1 phải giữ đúng). Việc của AIE-1 trong issue: *"Đảm bảo `llm-step`
output ổn định (fixtures) để judge chấm nhất quán; ES gateway-flag nếu demo."*

## Setup bắt buộc trước khi làm bất kỳ việc gì (đọc `plan.md §Quyết định đã khoá` trước)

```
git -C packages/engine fetch origin
git -C packages/engine switch -c aie-1/day18-llm-step-stability origin/main
```
Không cắt nhánh từ `main` local (detached HEAD, lệch `origin/main` 2 commit — xem plan.md).
Thêm `.claude/` vào `packages/engine/.gitignore` (untracked, không thuộc phase nào) trước commit
đầu tiên của phase này.

## Overview — đã sửa sau red-team (bản đầu có 1 lỗi thiết kế)

**Bản Probe đầu tiên của phase này liệt kê 3 "ứng viên" cho đường AIE-2's judge lấy output —
red-team xác nhận cả 3 đều KHÔNG dùng được, vì lý do khác nhau:**

| ứng viên | vì sao chết |
|---|---|
| `_GoldenAwareLLM` (`run_golden_batch.py:106`) | `studio_evalhub` bị `.importlinter` cấm import `studio_engine` (sibling quadrant) — evalhub không bao giờ gọi được double này |
| `ExtractiveFakeLLM` (`apps/studio/.../providers/fakes.py`) | Sống ở `apps/studio`, ngoài quyền ghi AIE-1 |
| `EngineAgentRunner` (giả thiết "an toàn") | Cũng ở `apps/studio/src/studio_app/eval_adapter.py` — ngoài quyền ghi AIE-1 |

**Câu trả lời thật, đọc trực tiếp từ code evalhub** (không cần đoán/hỏi AIE-2):
- `packages/evalhub/src/studio_evalhub/judge.py:31` — `LLMJudge.judge(case_id, expected,
  actual)` nhận `actual` là **string trần**. Judge không gọi harness nào của engine cả.
- `packages/evalhub/src/studio_evalhub/harness.py:375` — `actual=answer.answer`.
- `packages/evalhub/src/studio_evalhub/agent_runner.py:16-19` — chuỗi đó đi qua
  `EngineAgentRunner` (composition root), map `final_state[<llm-step node>]` → `AgentAnswer.answer`.

**Kết luận: phần AIE-1 chạm được, duy nhất, là chính field `answer` mà `LlmStepExecutor.execute()`
phát ra** (`executors.py:196-293`) — bất kể `apps/studio` inject `LLM` impl nào (fixture, fake,
gateway), format/tính ổn định của `answer` bắt nguồn từ logic executor + prompt-build
(`build_prompt`, `executors.py:54-76`) + fixture data nó đọc. Deliverable của phase này KHÔNG
phụ thuộc AIE-2 chọn harness nào — nó là: **mở rộng `tests/fixtures/llm_step/` (hiện chỉ 1 file
`smoke-01.json`) + khoá tính ổn định của `LlmStepExecutor` bằng test, độc lập với ai gọi nó.**
Nếu `apps/studio` cần AIE-1 xin `FixtureLLM` được inject cho judge — đó là 1 comment/issue,
không phải code AIE-1 viết trong repo mình.

## Files

- **Modify**: `packages/engine/.gitignore` — thêm `.claude/` (dọn untracked trước commit đầu).
- **Modify**: `packages/engine/src/studio_engine/executors.py::LlmStepExecutor.execute()`
  (`:196-293`) — thêm 1 field cờ gateway vào output dict trả về (return statement `:288-293`):
  `"llm_source": "stub"` (mặc định) hay `"llm_source": "gateway"` — quyết định bằng cách kiểm
  `type(self._llm).__name__` không phải `FixtureLLM`/double đã biết trong `demo_stubs.py`
  (KHÔNG cố nhận diện gateway thật vì chưa ship — mọi impl KHÔNG PHẢI double đã biết mặc định
  coi là `"gateway"`, an toàn theo hướng khai thật hơn là mặc định khai "stub" nhầm).
- **Create/Modify**: `packages/engine/tests/fixtures/llm_step/*.json` — thêm ≥2-3 case mới
  (case_id tự đặt, không phụ thuộc golden-set của DE) chứng minh `FixtureLLM` replay nhiều case
  khác nhau ổn định, không chỉ 1 case `smoke-01.json` như hiện tại.
- **Create**: `packages/engine/tests/test_llm_step_output_stability.py`.

## TDD

- **Tests-before (RED)**:
  1. Test gateway-flag: gọi `LlmStepExecutor.execute()` với `FixtureLLM` (double đã biết) →
     assert output có key `llm_source == "stub"`. RED trước khi thêm field (`KeyError`).
  2. Test gateway-flag mặc định an toàn: gọi với 1 `LLM` impl giả lập KHÔNG PHẢI double đã biết
     (1 fake nhỏ viết ngay trong test) → assert `llm_source == "gateway"`. RED trước khi có
     logic phân loại.
  3. Test ổn định — **ghi rõ đây là characterization/fence test, KHÔNG phải red→green thật**:
     `FixtureLLM.complete()` (`demo_stubs.py:131-146`) chỉ đọc file + trả string, không có nguồn
     ngẫu nhiên (`random`/`time`/`id()`-order) — test này XANH ngay cả TRƯỚC khi sửa gì, vai trò
     của nó là khoá lại tính chất đã đúng, không phải bắt 1 lỗi đang có. Chạy 2 lần cùng process
     + qua `subprocess` với `PYTHONHASHSEED=0` và `PYTHONHASHSEED=424242` (mẫu `DL-11.A1-9`,
     `packages/engine/docs/decisions/decision-log.md` dòng ~38) → cùng `answer`/`citations`.
- **Implement** → xanh. Field mới `llm_source` chỉ THÊM vào dict trả về — an toàn: đã kiểm
  không có test nào assert full-dict-literal trên output `llm-step` (các test assert full-dict
  chỉ có ở `tool-call`/`end`/`hitl-pause`/`kb-retrieve` — `test_executors_behavior.py:172,194,205`,
  `test_trace_event_emission.py:185,232` — không đụng `llm-step`). `interpreter.py:418-422`
  pass-through mọi key vào `TraceEvent.outputs` dạng JSON-safe, không cần đổi gì ở interpreter.
- **Regression** (chạy từ kit-root `C:\Users\COLOR FULL\Desktop\agentcore-studio-kit`):
  ```
  uv run --package agentcore-studio-engine pytest packages/engine/tests -q
  uv run ruff check packages/engine
  uv run ruff format --check packages/engine
  uv run mypy packages/engine
  uv run lint-imports
  ```
  Commit khi cả 5 lệnh sạch.

## PR (bắt buộc — không gộp với phase 2/3)

1. [x] Đã tạo branch ở bước Setup đầu phase (`aie-1/day18-llm-step-stability`, từ `origin/main`).
2. [x] Commit conventional (`feat(engine): ...` / `test(engine): ...`), message dẫn `kit#116`.
3. [x] `gh pr create --repo AI20K-VGR/agentcore-studio-engine --base main --head
   aie-1/day18-llm-step-stability` — PR#23 mở, mô tả nêu rõ: deliverable là ổn định
   `LlmStepExecutor` nội bộ, không phụ thuộc harness AIE-2 chọn (xem §Overview).
4. [x] Xác nhận `gh pr checks` xanh THẬT — `gh pr checks 23 --repo AI20K-VGR/agentcore-studio-engine`
   exit 0, mọi check `pass`/`skipping` (`ci / test-reconstructed`, `TTS deep-facts` x2, `ci /
   lint-shallow` skip có chủ đích), không còn `pending`. Xác nhận sau khi Monitor nền timeout
   không kết luận được (10 phút, script có vấn đề trên môi trường này) — gọi `gh pr checks` trực
   tiếp thay thế và đọc exit code thật.
5. [ ] **Reviewer: AIE-2 (Lưu Tiến Duy)** — chờ review (không nằm trong cook run).
6. [ ] **Merge PR vào main của `agentcore-studio-engine`** — chờ approval rồi merge (gates phase 2,
   không nằm trong cook run).

## Success

- [x] `LlmStepExecutor.execute()` output có field `llm_source`, mặc định đúng theo double đang
      dùng, khai `"gateway"` khi gặp impl lạ (an toàn theo hướng khai thật hơn).
- [x] `tests/fixtures/llm_step/` có ≥3 case (thêm ≥2 so với hiện tại), test ổn định qua 2 lần
      gọi + 3 `PYTHONHASHSEED` xanh (nâng từ 2 lên 3 seed ở vòng sửa code-review W-2).
- [x] `run_golden_batch.py` (D16) không đổi hành vi (chạy `_GoldenAwareLLM`, không đụng hành vi
      cũ — xác nhận bằng cách chạy lại harness thật 2 lần, không suy đoán).
- [x] 5 lệnh regression (`pytest`/`ruff check`/`ruff format --check`/`mypy`/`lint-imports`) sạch.
- [ ] PR riêng mở vào `agentcore-studio-engine` (PR#23, branch `aie-1/day18-llm-step-stability`,
      commits `52d8111`+`8528883`) — **mở xong, CI xanh xác nhận (xem PR §4), merge CHƯA xác
      nhận**. Tiêu chí gốc của mục này là "mở + merge", cook run này dừng ở "mở + CI xanh" vì
      merge là hành động con người ngoài phạm vi cook — không tự đánh dấu đạt tiêu chí gốc khi
      chỉ mới đạt một phần.

## Risks

- **[L]** Nếu AIE-2 (kit#118) sau này thật sự cần AIE-1 wire `FixtureLLM` vào
  `EngineAgentRunner` (ở `apps/studio`) để judge chấm qua fixture — đó là việc nằm ngoài quyền
  ghi AIE-1, cần AIE-2 hoặc mentor tự làm ở `apps/studio`, hoặc AIE-1 mở PR review-only đề nghị.
  Không tự ý sửa `apps/studio` trong phase này.
- **[L]** Field `llm_source` là quyết định thiết kế mới (không có trong issue gốc theo nghĩa
  đen "gateway-flag") — ghi rõ trong PR để review xác nhận tên field/giá trị hợp lý, không phải
  chờ tới lúc merge mới biết.
