---
phase: 1
title: "Main"
status: pending
plan: 260728-1116-day7-embedding-protocol-stub
created: 2026-07-28
harness_version: 5.3.0
harness_kit_digest: 251ed307796039124b44d71759b3f62d8bb9135c4bf3053156e38798587a50a8
harness_schema_version: 1.0
---

# Phase 1 — Main

## Overview
Nối `StubEmbedding` (fixtures-first `EmbeddingService` impl) vào `packages/engine`, và làm
`interpreter.py`/`LlmStepExecutor` đọc đủ `agent_config.instructions`/`model` (`tool_whitelist`
đã xong từ Day 6). Không phụ thuộc phase nào khác trong plan này (plan chỉ có 1 phase); phụ
thuộc ngoài: Phase 0 (sync submodule, đã chạy xong trước khi mở plan này — `packages/engine`
đã ở `main` mới nhất, nhánh làm việc `day7/embedding-protocol-stub` đã tạo).

## Files
- **Modify** `packages/engine/src/studio_engine/demo_stubs.py` — thêm class `StubEmbedding`
  ngay sau `EmptyEmbedding` (dòng ~68), + hằng `_EMBED_FIXTURES_DIR`.
- **Modify** `packages/engine/src/studio_engine/executors.py` — `build_prompt()` thêm tham số
  tùy chọn `instructions: str = ""`; `LlmStepExecutor.execute()` đọc `instructions`/`model` từ
  `node.params`, forward vào prompt/kwargs.
- **Modify** `packages/engine/src/studio_engine/interpreter.py` — nhánh `NodeType.LLM_STEP`
  (quanh dòng 220-225) thread thêm `"instructions": recipe.agent_config.instructions` và
  `"model": recipe.agent_config.model` vào `node.params`.
- **Create** `packages/engine/tests/fixtures/embedding/smoke-01.json` — fixture VCR-style
  (`case_id`/`request.texts`/`response`: list vector, mỗi vector đúng 8 phần tử float).
- **Create** `packages/engine/tests/test_stub_embedding.py` — test `StubEmbedding`.
- **Modify** `packages/engine/tests/test_llm_step_prompt_build.py` — thêm test cho
  `build_prompt(..., instructions=...)` + test interpreter-level cho `instructions`/`model`
  threading.

## TDD
- **Tests-before (RED)**:
  - `test_stub_embedding.py::test_stub_embedding_replays_fixture_vectors` — fail vì
    `StubEmbedding` chưa tồn tại (`ImportError`).
  - `test_llm_step_prompt_build.py::test_build_prompt_includes_instructions_when_given` — fail
    vì `build_prompt()` chưa nhận `instructions`.
  - `test_llm_step_prompt_build.py::test_interpreter_threads_agent_config_instructions_and_model_into_llm_step`
    — fail vì `interpreter.py` chưa thread 2 field này.
- **Implement**: thêm `StubEmbedding` (mirror `FixtureLLM`) + fixture JSON; sửa `build_prompt`
  (tham số optional, default rỗng giữ nguyên hành vi cũ); sửa nhánh `LLM_STEP` của
  `interpreter.py`; sửa `LlmStepExecutor.execute()` đọc `instructions`/`model`.
- **Regression**: `pytest packages/engine/tests -q` (toàn bộ, không riêng test mới) +
  `ruff check packages/engine` + `mypy --strict packages/engine` + `lint-imports`; commit 1 lần
  khi cả 4 gate xanh.

## Success
- [ ] `StubEmbedding("smoke-01").embed(["a", "b"])` trả đúng list vector ghi trong
      `smoke-01.json`, mỗi vector `len == 8`; gọi lại lần 2 ra y hệt (assert `==`, không chỉ
      "không lỗi").
- [ ] `build_prompt(query, chunks, instructions="X")` — output chứa `"X"`; `build_prompt(query,
      chunks)` (2-arg, không instructions) — output giống hệt hành vi cũ (test cũ không sửa vẫn
      xanh).
- [ ] Chạy `interpreter.run(...)` với recipe có `agent_config.instructions="Y"` và node `llm-step`
      không tự khai `params["prompt"]` → `llm.prompts[-1]` chứa `"Y"`.
- [ ] Chạy tương tự với `agent_config.model="m-x"`, node không tự khai `kwargs["model"]` →
      `llm.kwargs[-1]["model"] == "m-x"`.
- [ ] `pytest packages/engine/tests -q` 100% pass, `ruff`/`mypy --strict`/`lint-imports` sạch.

## Risks
- **L — sửa `build_prompt` signature phá call site cũ** nếu default sai. Mitigation: default
  `instructions=""` giữ `header == _PROMPT_HEADER` y hệt trước — mọi test cũ gọi 2-arg không đổi
  hành vi, verify bằng chạy lại `test_llm_step_prompt_build.py` full suite sau khi sửa (không chỉ
  test mới).
- **L — thread `model` đè `kwargs["model"]` recipe tự khai.** Mitigation: guard
  `if model and "model" not in kwargs` trước khi set — recipe-declared thắng, giống pattern
  `declared_prompt or build_prompt(...)` đã có.
