---
phase: 1
title: "SessionContext Protocol + interpreter threading"
status: pending
plan: 260729-1244-day8-session-context-tenant-wall
created: 2026-07-29
harness_version: 5.3.0
harness_kit_digest: 251ed307796039124b44d71759b3f62d8bb9135c4bf3053156e38798587a50a8
harness_schema_version: 1.0
---

# Phase 1 — SessionContext Protocol + interpreter threading

## Overview
Cắt đường "client tự khai tenant": `interpreter.run()` nhận `session_context` (bắt buộc,
keyword-only) và lấy tenant từ đó cho **cả** `kb-retrieve` lẫn `TraceEvent`. Sau phase này
`interpreter.py` không còn đọc `recipe.tenant_id` ở bất kỳ dòng nào. Không phụ thuộc phase khác;
phụ thuộc ngoài: `packages/engine` đã sync `main` và cắt nhánh `day8/session-context-tenant-wall`.

## Files
- **Create** `packages/engine/src/studio_engine/session.py` — `SessionContext` Protocol
  (`@runtime_checkable`), 3 thành viên khai bằng `@property` (read-only, xem Probe bên dưới):
  `tenant_id -> UUID`, `user -> str`, `roles -> list[str]`. Module docstring viết đoạn
  **tag-vs-isolation** + **vì sao "nhờ LLM đừng nói" là fake fence**, tham chiếu chéo tới
  `executors.py:100-106` (đoạn fence-EXECUTOR đã có sẵn) và `trace.py:30` (`NOT NULL, INV-1`).
- **Modify** `packages/engine/src/studio_engine/interpreter.py`
  - chữ ký `run()` (dòng 109-116): thêm `session_context: SessionContext` keyword-only, **không
    default**, đặt ngay sau `recipe` trong khối `*`.
  - dòng ~219: `node.model_copy(update={"params": {..., "tenant_id": session_context.tenant_id}})`
    — thay `recipe.tenant_id`.
  - dòng ~271: `TraceEvent(tenant_id=session_context.tenant_id, ...)` — thay `recipe.tenant_id`.
  - cập nhật docstring `run()`: nêu rõ tenant đến từ session server-side, `recipe.tenant_id` bị
    bỏ qua có chủ đích (INV-1), và comment cũ ở dòng 211-218 (giải thích vì sao bơm
    `recipe.tenant_id`) phải được viết lại chứ không để lại gây hiểu nhầm.
- **Modify** `packages/engine/src/studio_engine/__init__.py` — export `SessionContext`, thêm vào
  `__all__` (giữ thứ tự alphabet như hiện tại).
- **Modify** `packages/engine/src/studio_engine/__main__.py` — dòng ~80 `interpreter.run(...)`:
  dựng một demo session context (frozen dataclass cục bộ trong file demo, `tenant_id=ANKOR_ID`
  vốn đã có ở dòng 35) và truyền vào.
- **Create** `packages/engine/tests/test_session_context_tenant_wall.py` — test money-shot.
- **Modify** (chỉ cập nhật call site `run()`, không đổi ý nghĩa test):
  `tests/test_cli_demo.py`, `tests/test_dag_edge_walk.py`, `tests/test_interpreter_behavior.py`,
  `tests/test_kb_retrieve_llm_step_threading.py`, `tests/test_llm_step_prompt_build.py`,
  `tests/test_refusal_from_grounding.py`, `tests/test_trace_event_emission.py`.
  Dùng **một** helper dựng session context dùng chung (đặt trong file test mới, import sang) để
  7 file kia không lặp lại định nghĩa.

## Probe (chạy TRƯỚC khi build tiếp — bắt buộc)
Rủi ro `[ASSUMED]` đã ghi ở `plan.md`: mypy có thể từ chối frozen dataclass khớp Protocol có
data-member mutable. Kiểm bằng thật, không suy luận:
1. Viết `session.py` với 3 thành viên khai bằng `@property`.
2. Viết trong test một `@dataclass(frozen=True, slots=True)` có đúng 3 field đó + một hàm
   `def _accepts(ctx: SessionContext) -> UUID: return ctx.tenant_id` và gọi nó với instance đó.
3. Chạy `mypy --strict packages/engine`. Phải **sạch**.
   - Nếu đỏ: Protocol không dùng được như thiết kế → **DỪNG, báo user** (quyết định "shape" phải
     mở lại: chuyển sang frozen dataclass cụ thể + adapter ở composition root). KHÔNG tự đổi
     hướng rồi build tiếp.

## TDD
- **Tests-before (RED)** — `test_session_context_tenant_wall.py`:
  - `test_kb_search_receives_session_tenant_not_recipe_tenant` — recipe khai `BOREA`, session
    mang `ANKOR`; spy `KbSearch` ghi lại `tenant_id` nhận được. Assert `== ANKOR` **và**
    `!= BOREA`. RED vì `run()` chưa nhận `session_context` (`TypeError`).
  - `test_trace_event_tenant_id_comes_from_session` — cùng recipe/session; assert **mọi**
    `TraceEvent` trong `result.events` có `tenant_id == ANKOR` (không chỉ event đầu).
  - `test_run_requires_session_context` — gọi `run()` thiếu `session_context` → `TypeError`.
  - `test_frozen_dataclass_satisfies_session_context_protocol` — chốt kết quả Probe ở tầng
    runtime (`isinstance` + gọi qua hàm nhận `SessionContext`).
- **Implement**: tạo `session.py`; sửa 3 điểm trong `interpreter.py`; export ở `__init__.py`;
  sửa `__main__.py`; cập nhật 7 call site test.
- **Regression**: `pytest packages/engine/tests -q` toàn bộ + `ruff check packages/engine` +
  `mypy --strict packages/engine` + `lint-imports`. Commit 1 lần khi cả 4 gate xanh.

## Success
- [ ] Probe mypy sạch (hoặc đã dừng và báo user nếu đỏ).
- [ ] `KbSearch.search()` nhận `tenant_id == ANKOR` khi recipe khai `BOREA` — assert cả
      `== ANKOR` lẫn `!= BOREA`.
- [ ] Mọi `TraceEvent.tenant_id` trong một run `== ANKOR` (session), không phải `BOREA` (recipe).
- [ ] `grep -n "recipe.tenant_id" packages/engine/src/studio_engine/interpreter.py` → **rỗng**.
- [ ] `run()` thiếu `session_context` → `TypeError`.
- [ ] `pytest packages/engine/tests -q` 100% pass; `ruff`/`mypy --strict`/`lint-imports` sạch.
- [ ] `session.py` docstring có đoạn tag-vs-isolation + fake fence.

## Risks
- **M — mypy vs frozen dataclass** (chi tiết + mitigation ở `plan.md`). Đã có bước Probe chặn
  trước; điều kiện dừng viết rõ: đỏ thì báo user, không tự xoay hướng.
- **L — sót call site.** `session_context` bắt buộc nên mọi chỗ sót đều nổ `TypeError` ngay khi
  chạy, không sót âm thầm. Verify bằng `pytest packages/engine/tests -q` full suite, không chỉ
  file test mới.
- **L — comment cũ `interpreter.py:211-218` mô tả hành vi đã chết** (giải thích vì sao bơm
  `recipe.tenant_id`). Để nguyên sẽ khiến người đọc sau tưởng code vẫn tin recipe. Bắt buộc viết
  lại comment này trong cùng commit, không để dọn sau.
