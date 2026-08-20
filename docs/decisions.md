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
