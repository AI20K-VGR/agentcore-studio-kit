# Multi-stage uv-workspace image (F4). Two stages:
#   builder — has the uv toolchain, resolves + installs the whole workspace into a .venv.
#   runtime — slim, carries ONLY the built .venv (no uv/toolchain, no editable-path back to
#             source that no longer exists in this stage).
#
# Layer order is deliberate for Docker layer-caching (R-DI §8 pattern, adapted to a uv
# *workspace* instead of a single package): every member's `pyproject.toml` is copied FIRST,
# before any application source — `uv sync` needs every workspace member's pyproject present to
# resolve the dependency graph, even though only deps (not the members themselves) get
# installed in that first sync. Source changes then only invalidate the second (fast) layer.
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 1) Root workspace files + every member's pyproject.toml — nothing else yet. This is the
#    layer `uv sync --no-install-project` needs to resolve the full workspace graph; it changes
#    only when a dependency is added/bumped, not on every source edit.
COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/kb/pyproject.toml packages/kb/pyproject.toml
COPY packages/engine/pyproject.toml packages/engine/pyproject.toml
COPY packages/workbench/pyproject.toml packages/workbench/pyproject.toml
COPY packages/evalhub/pyproject.toml packages/evalhub/pyproject.toml
COPY apps/studio/pyproject.toml apps/studio/pyproject.toml

# Cache-only sync: resolves + installs every dependency but NOT the workspace members
# themselves (their source isn't copied in yet) — this layer stays warm across source edits.
RUN uv sync --frozen --no-install-project

# 2) Now the real source for every member that ships in the runtime image (apps/web is a
#    separate Vite/TS frontend, P10 — never part of this Python image).
COPY packages/ packages/
COPY apps/studio/ apps/studio/

# --no-editable is MANDATORY (F4): without it uv installs the workspace members as editable
# path-links back to /app/packages/*/src and /app/apps/studio/src. The runtime stage below
# copies ONLY .venv, not that source tree — an editable .venv left pointing at source that no
# longer exists is a runtime import failure, not a build failure (fails at container start,
# not at `docker build`). `--frozen` on both syncs means this build never silently relocks.
RUN uv sync --frozen --no-editable

# --- runtime stage ---------------------------------------------------------------------------
# Slim, no uv/toolchain, no source tree — just the fully-installed, non-editable .venv from the
# builder stage. Smaller image, smaller attack surface, and structurally cannot import from a
# path that got left behind (there is no builder-stage source tree here to leave behind).
FROM python:3.14-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "studio_app.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
