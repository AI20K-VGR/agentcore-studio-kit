---
phase: 2
title: "KbRetrieveExecutor fail-closed (executor không tự set tenant)"
status: pending
plan: 260729-1244-day8-session-context-tenant-wall
created: 2026-07-29
harness_version: 5.3.0
harness_kit_digest: 251ed307796039124b44d71759b3f62d8bb9135c4bf3053156e38798587a50a8
harness_schema_version: 1.0
---

# Phase 2 — KbRetrieveExecutor fail-closed

## Overview
Vế thứ hai của DoD #37: *"executor không tự set tenant"*. Hiện `executors.py:138` khi
`node.params` thiếu `tenant_id` thì lặng lẽ rơi về `_NO_TENANT_ID = UUID(int=0)`
(`executors.py:21`) — tức executor **tự bịa** một tenant. Nil-UUID tình cờ khớp 0 dòng nên "có
vẻ" fail-closed, nhưng đó là **fail-closed do may mắn, không do hợp đồng**: một lỗi wiring
(interpreter quên bơm tenant) sẽ biểu hiện thành "0 kết quả" — trông y hệt "tenant này thật sự
không có tài liệu", không ai phát hiện ra. Đổi thành raise tường minh.

Phụ thuộc Phase 1 (interpreter luôn bơm tenant từ session → nhánh raise không bao giờ chạm
trong luồng bình thường; đây là defense-in-depth cho trường hợp executor bị construct/gọi
trực tiếp, không qua interpreter).

## Files
- **Modify** `packages/engine/src/studio_engine/executors.py`
  - xoá hằng `_NO_TENANT_ID` (dòng 21) + comment kèm theo.
  - `KbRetrieveExecutor.execute()` (dòng ~133-141): `raw_tenant_id = node.params.get("tenant_id")`
    → nếu **không phải** `UUID` (thiếu, `None`, hoặc là slug string như `"ankor"`) thì
    `raise PermissionError` với thông điệp nêu rõ INV-1 + nói thẳng tenant phải do
    session server-side cấp qua interpreter, executor không tự suy ra.
  - cập nhật docstring `execute()` (dòng 124-131): câu *"Day 3 has no real server-side
    session/tenant context to resolve `section_roles` from, so this stub passes through..."*
    đã hết đúng sau Phase 1 — viết lại cho khớp thực tế.
- **Modify** `packages/engine/tests/test_executors_behavior.py` — thêm test fail-closed.

## TDD
- **Tests-before (RED)** — `test_executors_behavior.py`:
  - `test_kb_retrieve_raises_when_tenant_id_absent` — node `kb-retrieve` không có `tenant_id`
    trong `params` → `pytest.raises(PermissionError)`. RED vì hiện đang trả `[]` lặng lẽ.
  - `test_kb_retrieve_raises_when_tenant_id_is_slug_not_uuid` — `params={"tenant_id": "ankor"}`
    (đúng cái bug D-13 đã sửa ở tầng contract, chặn nốt ở tầng executor) → `PermissionError`.
  - Cả 2 test phải assert **raise**, không assert "trả list rỗng" — phân biệt rạch ròi
    "fail-closed có hợp đồng" với "0 kết quả do nil-UUID".
- **Implement**: xoá sentinel, thêm nhánh raise, viết lại docstring.
- **Regression**: `pytest packages/engine/tests -q` toàn bộ (đặc biệt `test_executors_behavior.py`
  dòng 54 đang truyền `tenant_id=ANKOR_ID` tường minh → phải vẫn xanh, không bị nhánh raise chạm)
  + `ruff check packages/engine` + `mypy --strict packages/engine` + `lint-imports`.

## Success
- [ ] Node `kb-retrieve` thiếu `tenant_id` → `PermissionError`, **không** trả `[]`.
- [ ] Node có `tenant_id` là slug `"ankor"` (không phải UUID) → `PermissionError`.
- [ ] `grep -rn "_NO_TENANT_ID" packages/` → **rỗng** (sentinel biến mất hoàn toàn).
- [ ] Đường bình thường không đổi: test cũ `test_executors_behavior.py` (truyền `ANKOR_ID`
      tường minh) vẫn xanh nguyên, không sửa.
- [ ] `pytest packages/engine/tests -q` 100% pass; `ruff`/`mypy --strict`/`lint-imports` sạch.

## Risks
- **L — `PermissionError` vs `ValueError`.** Chọn `PermissionError` cho khớp với
  `resolve_tenant()`/`resolve_session()` của SWE (`tenant_wall.py`, PR #6) — cùng một họ lỗi
  fence trên toàn hệ thống thì log/handler sau này bắt được bằng một `except`. Nếu cook thấy
  repo đã có quy ước khác cho lỗi fence, ưu tiên quy ước có sẵn và ghi lý do vào commit message.
- **L — nhánh raise gần như bất khả đạt qua interpreter sau Phase 1.** Đây là chủ đích
  (defense-in-depth), không phải code chết: test gọi thẳng `KbRetrieveExecutor.execute()` nên
  vẫn được cover thật. Không viết test đi vòng qua interpreter để "ép" nhánh này chạy.
