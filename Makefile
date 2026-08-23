ifneq (,$(wildcard ./.env))
	include .env
	export
endif

.PHONY: setup dev frontend test test-int leak-test demo lint format

setup: ## uv sync the whole workspace (all 6 Python members, 1 venv)
	uv sync
	cp .env.example .env

dev: ## bring up the default compose profile (pgvector/pgvector:pg17) — wired in P3/P9
	docker compose up -d
	uv run uvicorn studio_app.app:create_app --factory --app-dir apps/studio/src --host 127.0.0.1 --port 8000 --reload --no-proxy-headers

ingestDB: ## ingest the database
	uv run python apps/studio/scripts/seed_demo_tenants.py
	uv run python packages/kb/scripts/ingest_callisto_v2.py
	uv run python apps/studio/scripts/seed_superadmin.py

# mặc định http://127.0.0.1:5173 
frontend: ## bring up the frontend
	cd apps/web && corepack enable pnpm && pnpm install && pnpm dev

test: ## run the full pytest suite across the workspace
	uv run pytest

test-int: ## bring up the isolated test-stack compose file, then run tests against it — wired in P9
	docker compose -f docker-compose.test.yml up -d --wait
	uv run pytest

leak-test: ## RLS/tenant leak-test — has teeth by design (a leaky kb.search stays RED) — wired in P5
	uv run pytest packages/kb/tests/test_leak.py

# `ruff format --check` phải nằm ở đây: CI của repo con chạy nó như một bước RIÊNG
# (.github/workflows/reusable-domain-ci.yml:106-108), nên thiếu nó ở local là gate local
# strictly yếu hơn gate CI — PR đi qua `make lint` sạch vẫn đỏ trên CI vì format.
lint: ## ruff + format-check + mypy strict + import-linter layers-contract
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy packages apps
	uv run lint-imports

format: ## áp ruff format cho toàn workspace (sửa thứ `make lint` báo)
	uv run ruff format .
