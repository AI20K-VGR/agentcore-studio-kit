---
id: 260728-1116-day7-embedding-protocol-stub
title: "Day 7 AIE-1 - EmbeddingService Protocol + StubEmbedding (fixtures-first)"
status: completed
mode: fast
tdd: true
branch: day7/embedding-protocol-stub
created: 2026-07-28
author: user:tranbadat26072004@gmail.com
decisions: []
phases:
  - phases/phase-1-main.md
harness_version: 5.3.0
harness_kit_digest: 251ed307796039124b44d71759b3f62d8bb9135c4bf3053156e38798587a50a8
harness_schema_version: 1.0
---

# Plan: Day 7 AIE-1 - EmbeddingService Protocol + StubEmbedding (fixtures-first)

## Tổng quan
Task Day 7 AIE-1 (`docs/requirements/week-1/days/day-07.md:36`): "Bút `EmbeddingService`
Protocol + `StubEmbedding` (fixtures-first); interpreter đọc `agent_config` (instructions vào
prompt, tool_whitelist vào tool-call)". `EmbeddingService` Protocol đã tồn tại
(`packages/contracts/src/studio_contracts/protocols.py:16-23`); `LlmStepExecutor.__init__(llm,
embedding)` (`packages/engine/src/studio_engine/executors.py:146-148`) đã nhận `embedding` qua
constructor-DI từ Day 3 nhưng chưa dùng (docstring dòng 155-157: "Day 7 is the real usage");
`interpreter.run(..., embedding: EmbeddingService, ...)` (`interpreter.py:109-116`) đã thread
xuống `LlmStepExecutor` — seam sạch, swap `StubEmbedding`→`GatewayEmbedding` sau này KHÔNG cần
sửa `interpreter.py`. `tool_whitelist` đã chảy vào `ToolCallExecutor` (`interpreter.py:164`) —
không cần đụng. Còn thiếu: `StubEmbedding` impl thật (mirror `FixtureLLM`'s VCR-fixture
convention, `demo_stubs.py:42-58`) + thread `instructions`/`model` từ `recipe.agent_config` vào
`LlmStepExecutor`.

## Quyết định đã khoá
- `StubEmbedding` sống trong `packages/engine/src/studio_engine/demo_stubs.py`, ngay sau
  `EmptyEmbedding`, mirror đúng convention VCR case_id → JSON fixture của `FixtureLLM`. Vector
  width cố định 8 (khớp `packages/kb/src/studio_kb/schema.py:33::EMBEDDING_DIM`), chỉ ghi chú
  bằng comment — KHÔNG import `studio_kb` (`.importlinter` cấm `studio_engine` import
  `studio_kb`). `EmptyEmbedding` giữ nguyên, không xoá (nhiều test cũ dùng làm default).
- `build_prompt()` (`executors.py`) thêm tham số tùy chọn `instructions: str = ""` —
  backward-compatible với mọi call site 2-arg hiện có.
- `interpreter.py` nhánh `NodeType.LLM_STEP` thread thêm `instructions` và `model` từ
  `recipe.agent_config` vào `node.params` (cùng chỗ đang thread `retrieved_chunks`/`query`).
- `LlmStepExecutor.execute()` đọc `instructions` để build prompt khi recipe không tự khai
  `prompt`; đọc `model`, forward vào `kwargs["model"]` khi recipe chưa tự khai `kwargs["model"]`
  — chuẩn bị sẵn seam cho `GatewayLLM` tương lai đọc `model` mà không cần sửa lại
  interpreter/executor lần nữa (user đã chốt: thread cả 3 field theo nghĩa đen của DoD chung
  "Interpreter đọc `agent_config` đủ 3 field", dù `model` không có consumer thật hôm nay).
- Fixtures Callisto thật do DE cấp sau (`tests/fixtures/embedding/`, cùng convention) — không
  block scope AIE-1 hôm nay; PR này tự tạo 1 fixture tối thiểu (`smoke-01.json`) cho test riêng.
- Daily-note D7 làm thủ công sau, KHÔNG qua `hs:cook` (tiết kiệm token theo yêu cầu user).

## Ràng buộc (constraint-scan)
`harness/data/ownership.yaml` chỉ khai 4 zone hẹp (`docs/`, `.harness/state/`, `harness/standards/`,
`plans/`) — không chi phối `packages/engine/**`, không có constraint chặn. `harness/data/
stage-policy.yaml`: `push`/`pr`/`merge`/`ship`/`deploy` đều `hard: true`, đòi `verification` +
`review-decision` (+ `plan-approval` trừ `push`) — cook's Step 4 (artifacts) + Step 5 (review) tự
thoả mãn, không cần hành động thêm. Không có `schemas/` riêng chi phối `packages/engine`.
Layer import (`code-standards.md` §7, `.importlinter`): `studio_engine` chỉ được import
`studio_contracts` — `StubEmbedding` không được import `studio_kb` (đã note ở trên).

## Phases
| # | Theme | Phụ thuộc | Cỡ |
|---|---|---|---|
| 1 | StubEmbedding + agent_config threading (demo_stubs.py, executors.py, interpreter.py + tests) | Phase 0 sync submodule đã xong (main) | nhỏ |

## Out of scope
`KbRetrieveExecutor` (embedding của kb-retrieve là việc nội bộ `PgKbSearch`/DE, không phải
`packages/engine`); `ConditionExecutor`/`HitlPauseExecutor` (giữ nguyên `NotImplementedError`);
fixtures Callisto thật (DE cấp sau); daily-note D7 (thủ công, ngoài cook).

## Acceptance (toàn plan)
- [ ] Test mới (`test_stub_embedding.py`, bổ sung `test_llm_step_prompt_build.py`) — RED trước
      khi sửa code, GREEN sau.
- [ ] `pytest packages/engine/tests -q` toàn bộ xanh (baseline + test mới).
- [ ] `ruff check packages/engine` + `mypy --strict packages/engine` + `lint-imports` sạch.
- [ ] `StubEmbedding("smoke-01").embed([...])` trả đúng vector 8 chiều từ fixture, deterministic
      (gọi 2 lần ra cùng kết quả).
- [ ] `recipe.agent_config.instructions` xuất hiện trong prompt gửi LLM khi recipe không tự khai
      `prompt`; `recipe.agent_config.model` xuất hiện trong `kwargs["model"]` khi recipe không tự
      khai `kwargs["model"]`. `tool_whitelist` hành vi không đổi (đã xanh từ Day 6).
- [ ] Swap `StubEmbedding`→`GatewayEmbedding` (giả lập bằng 1 double khác trong test) không cần
      sửa `interpreter.py` — chỉ đổi impl truyền vào `interpreter.run(embedding=...)`.

## Rollback
1 phase = 1 commit trên nhánh `day7/embedding-protocol-stub` (`packages/engine`, đã tạo từ `main`
đã sync). Hoàn tác: `git revert <sha>`, chạy lại `pytest packages/engine/tests -q` để xác nhận về
trạng thái Day 6 (StubEmbedding/instructions/model chưa có, hành vi cũ nguyên vẹn).

## Risks
- **L — thread `model` vào `kwargs` có thể va với `kwargs` đã có sẵn key khác từ recipe.** Mitigation:
  chỉ set khi `"model" not in kwargs` (recipe-declared thắng), `FixtureLLM.complete` đã ignore mọi
  kwargs nên không phá test cũ.
- **L — fixture `embedding/smoke-01.json` của AIE-1 và fixture Callisto thật của DE (sau này) lệch
  convention.** Mitigation: mirror 1:1 shape `llm_step` fixture (`case_id`/`request`/`response`),
  DE chỉ cần thêm file mới cùng thư mục, không sửa `StubEmbedding`.
