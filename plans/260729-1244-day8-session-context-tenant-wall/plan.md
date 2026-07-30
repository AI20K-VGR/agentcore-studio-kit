---
id: 260729-1244-day8-session-context-tenant-wall
title: "Day 8 AIE-1 - Interpreter truyền session context (INV-1 Tenant-Wall)"
status: completed
mode: fast
tdd: true
branch: day8/session-context-tenant-wall
created: 2026-07-29
author: user:tranbadat26072004@gmail.com
decisions: [DEC-1]
phases:
  - phases/phase-1-session-context-threading.md
  - phases/phase-2-executor-fail-closed.md
harness_version: 5.3.0
harness_kit_digest: 251ed307796039124b44d71759b3f62d8bb9135c4bf3053156e38798587a50a8
harness_schema_version: 1.0
---

# Plan: Day 8 AIE-1 - Interpreter truyền session context (INV-1 Tenant-Wall)

## Tổng quan
Task Day 8 AIE-1 (issue #37, `docs/requirements/week-1/days/day-08.md`): "Interpreter **truyền
`session` context** (không truyền tenant do client khai); executor không tự set tenant".

Hiện trạng đã probe (OBSERVED, đọc trực tiếp source):
- `interpreter.py:219` bơm `recipe.tenant_id` vào `node.params["tenant_id"]` cho `kb-retrieve`.
- `interpreter.py:271` dùng `recipe.tenant_id` làm `TraceEvent.tenant_id`.
- `recipe.tenant_id` (`packages/contracts/src/studio_contracts/recipe.py:89`) đến từ recipe do
  workbench/client dựng — **chính là đường "client tự khai tenant"** mà Day 8 phải giết.
- `executors.py:138` khi `node.params` thiếu `tenant_id` thì lặng lẽ rơi về sentinel
  `_NO_TENANT_ID = UUID(int=0)` (`executors.py:21`) — executor **tự bịa** một tenant. Đây đúng
  là thứ DoD cấm ("executor không tự set tenant"). Grep toàn repo: sentinel này chỉ xuất hiện ở
  2 dòng trong `executors.py`, **không test nào ghim hành vi này** → thay được an toàn.

`run()` là chữ ký AIE-1-owned, đổi tự do không cần mentor-approval — **DEC-1**
(`docs/decisions.md:12-14`) đã nói thẳng: *"Day 4 (kb.search that) / Day 6 (doc dag dong) /
**Day 8 (session ctx)** build len chu ky nay"*. Plan này chính là phần Day 8 mà DEC-1 dự trù.

## Quyết định đã khoá
(3 điểm rẽ dưới đây user đã chốt trong phiên plan, không phải mặc định của tôi)

- **Shape = Protocol trong engine.** `.importlinter` (root repo) khai layers
  `studio_app > (studio_kb | studio_engine | studio_workbench | studio_evalhub) > studio_contracts`
  → `studio_engine` **bị cấm** import `studio_workbench`, nên `ResolvedContext` của SWE
  (`packages/workbench/src/studio_workbench/tenant_wall.py`, PR #6) **không tái sử dụng được**.
  Giải: khai `SessionContext` Protocol mới trong `packages/engine/src/studio_engine/session.py`
  với đúng 3 thuộc tính `tenant_id: UUID` / `user: str` / `roles: list[str]`. Structural typing
  → `ResolvedContext` của SWE khớp sẵn, composition root (`apps/studio`, được phép import cả
  2 quadrant) truyền thẳng, **không cần import chéo, không cần adapter**.
- **`session_context` là tham số BẮT BUỘC** (keyword-only, không default). Không ai gọi `run()`
  mà lách được fence. Đánh đổi đã chấp nhận: 6 call site bên `packages/workbench/tests`
  (`test_builder.py`, `test_wiring_d3/d4/d5/d6/d7.py` — repo SWE own) sẽ đỏ khi kit bump
  submodule pointer của engine. Breakage này là **cố ý và nhìn thấy được**, không phải tai nạn.
- **Mismatch = bỏ qua `recipe.tenant_id`, luôn dùng session.** Không raise. Đúng nghĩa đen DoD:
  *"Client gửi `tenant=borea` khi session là `ankor` → `kb.search` **chỉ** trả ankor"* — request
  vẫn chạy, chỉ bị thu hẹp scope về ankor. Sau plan này `interpreter.py` **không còn đọc
  `recipe.tenant_id` ở bất kỳ đâu**; đó là bằng chứng mạnh nhất cho "client tự khai bị bỏ qua".
- **Giữ đủ 3 field kể cả khi chưa có consumer.** Hôm nay chỉ `tenant_id` có người dùng thật;
  `user`/`roles` được mang theo cho khớp shape của SWE và cho Sprint 3 (`section_role` filter).
  Cùng tiền lệ với quyết định Day 7 (thread `model` dù chưa có consumer).
- **2 DoD "giải thích" đặt vào docstring, không chỉ daily-note.** Module docstring của
  `session.py` viết đoạn tag-vs-isolation + vì sao "nhờ LLM đừng nói" là fake fence. Lý do:
  docstring sống cùng code, daily-note thì không ai đọc lại. (`executors.py:100-106` đã có sẵn
  một đoạn fence-EXECUTOR nhắc "fake fence" — viết cho nhất quán, tham chiếu chéo tới nó.)
- Daily-note D8 làm thủ công sau, **KHÔNG** qua `hs:cook` (tiết kiệm token, giống Day 7).

## Điểm xuất phát (đã verify 2026-07-29)
- `packages/engine` đang ở nhánh `day7/embedding-protocol-stub`, **không còn commit lẻ**
  (`git log origin/main..HEAD` rỗng) — Day 7 đã merge vào `origin/main` tại `a65c9d6`
  ("Merge pull request #11 from AI20K-VGR/day7/embedding-protocol-stub").
- Bước đầu tiên của cook (trước Phase 1):
  ```
  git -C packages/engine checkout main
  git -C packages/engine pull --ff-only          # tới a65c9d6
  git -C packages/engine checkout -b day8/session-context-tenant-wall
  ```
- Baseline phải xanh TRƯỚC khi sửa gì: `pytest packages/engine/tests -q`. Nếu baseline đã đỏ,
  dừng và báo user — không build lên nền đỏ.

## Ràng buộc (constraint-scan)
- `.importlinter`: `studio_engine` chỉ được import `studio_contracts`. `SessionContext` **phải**
  tự khai trong engine, cấm import `studio_workbench`. Gate `lint-imports` sẽ bắt nếu vi phạm.
- `harness/data/ownership.yaml` chỉ khai 4 zone (`docs/`, `.harness/state/`, `harness/standards/`,
  `plans/`) — không chi phối `packages/engine/**`, không có constraint chặn.
- `harness/data/stage-policy.yaml`: `push`/`pr`/`merge`/`ship`/`deploy` đều `hard: true`, đòi
  `verification` + `review-decision` (+ `plan-approval` trừ `push`) — cook Step 4/5 tự thoả.
- `studio_contracts` KHÔNG bị đụng trong plan này → không cần DEC mới, không bump
  `SCHEMA_VERSION`. `TraceEvent.tenant_id` (`trace.py:30`, ghi chú `NOT NULL, INV-1`) giữ nguyên
  kiểu, chỉ đổi **nguồn** giá trị.
- Issue #37 cấp WRITE đúng `agentcore-studio-engine`; `agentcore-studio-kit` là READ.

## Phases
| # | Theme | Phụ thuộc | Cỡ |
|---|---|---|---|
| 1 | `SessionContext` Protocol + `run()` nhận session bắt buộc + tenant lấy từ session (9 call site trong engine cập nhật theo) | — | vừa |
| 2 | `KbRetrieveExecutor` fail-closed: bỏ sentinel `_NO_TENANT_ID`, thiếu tenant → raise | Phase 1 | nhỏ |

Cả 2 phase đều kết thúc ở trạng thái suite xanh → mỗi phase là 1 commit revert được độc lập.

## Out of scope
- **Wiring composition root** (`apps/studio`): đã probe `apps/studio/src/studio_app/app.py` —
  **chưa có route nào gọi `interpreter.run()`**, nên không có chỗ để nối end-to-end hôm nay.
  Ngoài ra `apps/studio` không nằm trong WRITE scope của issue #37.
- **`apps/studio/src/studio_app/middleware.py:41-68`** — middleware thật vẫn tin header
  `x-tenant-id` do client gửi (comment dòng 51-56 tự nhận là "DEV-TIME STUB — NOT
  production-grade"). Đây là lỗ hổng THẬT của DoD chung #40 nhưng không thuộc AIE-1; cần nêu
  với SWE/nhóm, không tự sửa.
- 6 call site `run()` bên `packages/workbench/tests` (repo SWE own).
- `kb.search` áp filter server-side (DE, issue #36); smoke-eval tenant scope (AIE-2, issue #39).
- Daily-note D8 + đề xuất đẩy `SessionContext` lên `studio_contracts` (việc ngày sau, cần DEC).

## Acceptance (toàn plan)
- [ ] Test mới RED trước khi sửa code, GREEN sau (bằng chứng: log 2 lần chạy trong verification).
- [ ] **Money-shot DoD**: recipe khai `tenant_id = BOREA`, session context mang `ANKOR` →
      `KbSearch.search()` nhận đúng `tenant_id == ANKOR`, và `TraceEvent.tenant_id == ANKOR`.
      Assert cả 2 mặt: **bằng ANKOR** và **khác BOREA** (không chỉ "không lỗi").
- [ ] `grep -n "recipe.tenant_id" packages/engine/src/studio_engine/interpreter.py` trả về
      **rỗng** — bằng chứng cơ học rằng đường client-khai đã bị cắt hẳn.
- [ ] Gọi `run()` thiếu `session_context` → `TypeError` ngay (bắt buộc, không default).
- [ ] `KbRetrieveExecutor.execute()` với node thiếu `tenant_id` → raise fail-closed, **không**
      trả list rỗng lặng lẽ. `_NO_TENANT_ID` biến mất khỏi codebase.
- [ ] `pytest packages/engine/tests -q` 100% pass (toàn bộ, không riêng test mới).
- [ ] `ruff check packages/engine` + `mypy --strict packages/engine` + `lint-imports` sạch.
- [ ] Module docstring `session.py` có đoạn tag-vs-isolation + fake fence (2 DoD "giải thích").

## Rollback
2 phase = 2 commit trên nhánh `day8/session-context-tenant-wall` (submodule `packages/engine`,
cắt từ `main` đã sync 2026-07-29). Hoàn tác từng phần: `git revert <sha-P2>` đưa executor về
sentinel cũ mà vẫn giữ session threading; `git revert <sha-P2> <sha-P1>` đưa về nguyên trạng
Day 7. Sau mỗi revert chạy lại `pytest packages/engine/tests -q` để xác nhận.

## Risks
- **H — 6 call site `run()` bên workbench sẽ đỏ.** Không tránh được vì user đã chốt tham số bắt
  buộc (đó là cái giá của fence kín). Mitigation: CI workbench reconstruct workspace từ
  `main` của repo cha (`.github/workflows/reusable-domain-ci.yml`), nên đỏ chỉ xuất hiện **sau
  khi kit bump submodule pointer** — có cửa sổ thời gian. Bắt buộc: ghi rõ breaking-change +
  liệt kê 6 file trong PR description, và comment vào issue #37/#38 để SWE biết trước.
- **M — `mypy --strict` có thể từ chối frozen dataclass khớp Protocol có thuộc tính mutable.**
  Protocol data-member mặc định là read-write; một `@dataclass(frozen=True)` không cho gán lại
  nên mypy có thể coi là KHÔNG khớp — điều đó sẽ phá luôn lý do chọn Protocol (khớp
  `ResolvedContext` của SWE mà không cần adapter). Đây là `[ASSUMED]` từ hiểu biết về quy tắc
  variance của mypy, **tôi chưa chạy thật**. Mitigation: khai 3 thuộc tính bằng `@property`
  (read-only Protocol) — frozen dataclass thoả. Phase 1 có bước probe bắt buộc: viết 1 test
  double frozen dataclass rồi chạy `mypy --strict` để xác nhận TRƯỚC khi build tiếp.
- **M — `runtime_checkable` chỉ kiểm tra sự tồn tại của thuộc tính, không kiểm kiểu.**
  `isinstance(x, SessionContext)` sẽ pass cho object có `tenant_id` kiểu `str`. Mitigation:
  không dùng `isinstance` làm cổng validate; dựa vào `mypy --strict` ở tầng tĩnh. Nếu cần chặn
  runtime thì kiểm `isinstance(ctx.tenant_id, UUID)` tường minh, không kiểm cả Protocol.
- **L — `__main__.py:80` (CLI demo) và 7 file test trong engine cùng phải cập nhật call site.**
  Cơ học, nhưng sót 1 chỗ là suite đỏ. Mitigation: `run()` bắt buộc tham số nên **mọi** chỗ sót
  đều nổ `TypeError` lúc collect/chạy — không có kiểu sót âm thầm.
