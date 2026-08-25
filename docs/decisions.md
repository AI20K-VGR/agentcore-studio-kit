# Decision Register

---
id: DEC-1
status: active
date: 2026-08-18
actor: "user:tranbadat26072004@gmail.com"
ts: "2026-08-18T07:09:34.125332+00:00"
affects: "apps/studio/src/studio_app/settings.py,apps/studio/src/studio_app/providers/factory.py,.env.example,docker-compose.yml,.github/workflows/reusable-domain-ci.yml"
---

## DEC-1 — llm_provider (StrEnum) required, không default trong Settings (app#19)

Discriminator OpenAI/Gemini phải fail-closed đúng precedent jwt_secret (settings.py:43) — thiếu STUDIO_LLM_PROVIDER raise ValidationError lúc boot, không rơi về nhánh mặc định im lặng. Đánh đổi: mọi .env/CI/docker-compose hiện có phải thêm biến (xử lý ở plan 260818-1356-app19-llm-provider-discriminator Phase 4).

---
id: DEC-2
status: active
date: 2026-08-25
actor: "user:thieuminh2004@gmail.com"
ts: "2026-08-25T02:06:19+00:00"
affects: "packages/contracts/src/studio_contracts/recipe.py,packages/engine,packages/workbench,apps/studio,apps/web,packages/kb"
---

## DEC-2 — AgentConfig.instructions renamed to system_prompt (contracts#14, kit#217)

Breaking rename per additive-only discipline; `SCHEMA_VERSION` bump 0.2.0-draft -> 0.3.0-draft (contracts commit c08ee94). Tên cũ mập mờ với "instructions" ở các nghĩa khác trong hệ thống (DAG node params, test docstring); `system_prompt` khớp thuật ngữ ngành cho field này.

Review contracts#14 chặn merge vì recipe **đã publish** trong DB (`wb.recipes`/`wb.recipe_versions`, jsonb, ghi hình dạng cũ) không đọc lại được sau rename thuần — `/chat`, `GET` recipe, và `recipe_hash` (rollback) đều vỡ `ValidationError`. Chọn hướng (1) trong 3 hướng review nêu: `AgentConfig.system_prompt` mang `Field(alias="instructions")` + `populate_by_name=True` (cùng khuôn F12 với `Edge.from_`) — đọc được cả hai tên, ghi ra tên mới. Đánh đổi: tên `instructions` sống mãi trên wire dưới dạng alias/kwarg hợp lệ; không migration DB nào cần chạy.

Phạm vi rename mở rộng ra `packages/kb` (kb#60) và 3 file test gốc kit (`tests/test_cost_one_number_three_surfaces.py`, `tests/test_agent_loop_chunks_seam.py`, `tests/e2e/test_lifecycle.py`) — thiếu ở lượt PR ban đầu, phát hiện khi ghép đủ 5 nhánh + chạy full suite ở gốc kit (review contracts#14, mục 2).
