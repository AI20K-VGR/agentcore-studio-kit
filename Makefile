.PHONY: setup dev test test-int leak-test demo lint

setup: ## uv sync the whole workspace (all 6 Python members, 1 venv)
	uv sync

dev: ## bring up the default compose profile (pgvector/pgvector:pg17) — wired in P3/P9
	docker compose up -d

test: ## run the full pytest suite across the workspace
	uv run pytest

test-int: ## bring up the isolated test-stack compose file, then run tests against it — wired in P9
	docker compose -f docker-compose.test.yml up -d --wait
	uv run pytest

leak-test: ## RLS/tenant leak-test — has teeth by design (a leaky kb.search stays RED) — wired in P5
	uv run pytest packages/kb/tests/test_leak.py

demo: ## 8-step lifecycle demo harness — wired in P10
	@echo "demo target — wired in P10 (Frontend + E2E + Docs)"

lint: ## ruff + mypy strict + import-linter layers-contract
	uv run ruff check .
	uv run mypy packages apps
	uv run lint-imports
