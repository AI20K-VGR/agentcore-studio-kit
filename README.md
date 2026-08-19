# agentcore-studio-kit

Production-grade `uv` workspace template for **AgentCore Studio** — a Mini-Studio where 4 OJT
engineers (DE · SWE · AIE-1 · AIE-2) build an AI-agent authoring tool end to end: form → tool+KB
(with tenant fence) → 6-node canvas → Test/trace (token+cost) → eval-gate → Publish.

Infra (Docker/Postgres/CI/contracts/RLS/queue/OTel) is WIRE — it runs Day-1. Business logic in the
4 quadrant packages is intentionally TRÔNG (`Protocol` + `NotImplementedError` + a RED acceptance
test = the spec each engineer fills in). See `plans/260717-1516-studio-kit-template/plan.md` for
the full decision record.

## Setup

```bash
make setup    # uv sync — one venv, one lockfile, all 6 Python members resolved
cp .env.example .env   # fill in real DSNs/keys
```

Requires `uv >=0.11` and network access on first `uv sync` (real PyPI deps, no vendoring).

## Dev loop

```bash
make dev        # docker compose up -d (default profile — Postgres, wired in P3/P9)
make test       # uv run pytest — full workspace suite
make lint       # ruff check . && mypy strict (packages + apps) && lint-imports (layers-contract)
```

## Workspace layout

```
packages/
  contracts/   studio_contracts   — frozen pydantic contracts (owner: mentor/shared, mentor-approval)
  kb/          studio_kb          — KB pipeline + kb.search fence-DATA (owner: DE — Nguyễn Đông Anh)
  engine/      studio_engine      — interpreter + 6 node executors (owner: AIE-1 — Trần Bá Đạt, stateless)
  workbench/   studio_workbench   — form+canvas UI wiring, Tenant-Wall (owner: SWE — Thiệu Quang Minh)
  evalhub/     studio_evalhub     — eval harness, judge, scorecard (owner: AIE-2 — Lưu Tiến Duy)
apps/
  studio/      studio_app         — composition root (owner: mentor)
  web/         (Vite/TS, P10)     — NOT a Python workspace member
```

One `uv.lock` at repo root resolves the whole workspace. `uv run --package <name>` isolates a
single member's dep-closure (e.g. `uv sync --package agentcore-studio-kb`).

## Kiến trúc & luồng

### Đồ thị phụ thuộc (import chỉ đi 1 chiều xuống — `.importlinter` cưỡng chế)

`studio_contracts` là **tầng đáy** (chỉ pydantic, không import ai). 4 quadrant package **chỉ** import
`studio_contracts` — KHÔNG import chéo nhau, KHÔNG import `studio_app`. `apps/studio` (composition)
là nơi DUY NHẤT được import mọi thứ, gom 4 xưởng lại thành app chạy được. Xưởng dùng nhau qua
**Protocol (DIP)** ở contracts, do composition tiêm bản thật vào — nên 4 owner làm song song không giẫm chân.

```mermaid
graph TD
    WEB["apps/web — Vite + React Flow (mentor)"]
    APP["apps/studio · studio_app (mentor)<br/>app.py · middleware · core/_db · core/schema · queue · providers · obs"]
    KB["packages/kb · studio_kb (DE — Nguyễn Đông Anh)<br/>search.py · pipeline.py · schema.py (kb.chunks + RLS)"]
    ENG["packages/engine · studio_engine (AIE-1 — Trần Bá Đạt)<br/>interpreter.py · executors.py · registry.py"]
    WB["packages/workbench · studio_workbench (SWE — Thiệu Quang Minh)<br/>validator.py · publish.py · tenant_wall.py · schema.py (wb.*)"]
    EVAL["packages/evalhub · studio_evalhub (AIE-2 — Lưu Tiến Duy)<br/>harness.py · judge.py · compute.py · schema.py (eval.*)"]
    CON["packages/contracts · studio_contracts (mentor/shared)<br/>Recipe · TraceEvent · KbSearchResultItem · Scorecard · NodeType(6) · Protocol(KbSearch/LLM/EmbeddingService/TraceWriter)"]

    WEB -. HTTP .-> APP
    APP --> KB
    APP --> ENG
    APP --> WB
    APP --> EVAL
    APP --> CON
    KB --> CON
    ENG --> CON
    WB --> CON
    EVAL --> CON

    classDef bottom fill:#eef,stroke:#66c;
    classDef comp fill:#efe,stroke:#6a6;
    class CON bottom
    class APP,WEB comp
```

### Hàng rào tenant (RLS) — 1 request đi xuyên fence

Bảng `kb.chunks` bật `FORCE ROW LEVEL SECURITY` + policy `USING(...) WITH CHECK(...)`. App chạy bằng
role **`studio_app`** (non-owner → bị RLS cắn), DDL chạy bằng **`studio_owner`** (pool tách đôi ở
`core/_db.py`). Không set tenant ⇒ `current_setting('app.tenant_id', true)` = NULL ⇒ **0 dòng**
(fail-closed), cho cả đọc lẫn ghi.

```mermaid
sequenceDiagram
    participant C as Client (tenant X)
    participant MW as middleware.py (studio_app)
    participant P as get_pool() → role studio_app
    participant DB as Postgres · kb.chunks (FORCE RLS)
    C->>MW: request + header x-tenant-id: X
    MW->>P: mở 1 conn/txn, giữ qua ContextVar
    alt resolve được tenant
        MW->>DB: SET LOCAL app.tenant_id = 'X'
    else không có tenant
        Note over MW,DB: KHÔNG set → NULL → 0 rows (fail-closed)
    end
    MW->>DB: kb.search chạy CÙNG conn đó
    DB-->>MW: chỉ rows tenant = X (USING) — ghi sai tenant bị chặn (WITH CHECK)
    MW-->>C: response — commit ở cuối txn (SET LOCAL tự reset)
```

### Luồng vòng đời 8 bước (mỗi bước map về package/file sở hữu)

```mermaid
graph LR
    S1["1· form tạo agent<br/>(workbench)"] --> S2["2· gắn tool + KB scope<br/>(workbench)"]
    S2 --> S3["3· canvas DAG 6-node<br/>(web + workbench)"]
    S3 --> S4["4· Test → trace token/cost<br/>(engine → obs.trace_events)"]
    S4 --> S5["5· fence-proof: hỏi data tenant-Y khi scope tenant-X → leak = 0<br/>(kb RLS)"]
    S5 --> S6["6· eval 30-case → gate PASS → Publish<br/>(evalhub → workbench)"]
    S6 --> S7["7· degrade instructions → re-eval → gate BLOCK → rollback<br/>(evalhub verdict → workbench)"]
    S7 --> S8["8· hitl-pause suspend/resume<br/>(engine)"]
```

**Mô tả luồng chạy 1 agent:** SWE dựng `Recipe` (bản thiết kế DAG) qua **workbench** → `validator.graph_lint`
kiểm 6-node-đóng/không-chu-trình/tool-whitelist. **engine** `interpreter.run(recipe)` duyệt DAG, mỗi node
gọi executor tương ứng (`kb-retrieve` → gọi `KbSearch` Protocol do **kb** hiện thực, chạy qua hàng rào RLS;
`llm-step` → `LLM` Protocol do **provider** GeminiProvider/FakeLLM cấp), và emit `TraceEvent` mỗi bước →
**PgTraceWriter** ghi 1 INSERT vào `obs.trace_events`. Cuối vòng, **evalhub** `harness.run` chấm 30 golden-case
→ `compute` ra `Scorecard.gate.verdict`; verdict **FAIL** ⇒ **workbench** `publish` chặn + `rollback` version.
Job nền chạy qua queue `core.jobs` (SKIP LOCKED + lease) do **worker/consumer** kéo. Tất cả "nói chuyện" qua
các kiểu ở **contracts** — không package nào import trực tiếp package khác.

> Đồ thị đầy đủ + thiết kế chi tiết (component map, 4-tier ownership, ops/CI): `docs/system-architecture.md`.
> Chuẩn code (ruff/mypy/psycopg/contracts/RLS…): `docs/code-standards.md`.

## Rule of thumb (luật 2-4-8, extended in P10)

The kit is designed around one onboarding rule: **2-4-8** — **2 weeks** to stand the kit up
(mentor, Tuần 0, before Day 1) · **4 owners** each fully self-sufficient in their own package ·
**8-step** demo proves the whole lifecycle end to end. Each OJT engineer lives in **one package**
— DE never edits `packages/workbench`, SWE never edits `packages/kb`, and so on (see the ownership
table below). Editing a package you don't own is a contract change, not a quadrant change, and
needs the mentor-approval rule (see `packages/contracts/`).

- **2** — **weeks to stand up**: this whole kit is designed to be mentor-built in ~2 weeks
  (Tuần 0, before Day 1 batch starts) so trainees `git clone` into a running skeleton on day one.
  Also doubles as: **2** roles per DB connection — `studio_owner` (DDL/admin, bypasses RLS) vs
  `studio_app` (runtime DML, RLS-enforced) — never point runtime traffic at the owner role.
- **4** — **owners**, one per quadrant package, each importing only `studio_contracts` (DIP) — no
  sibling imports, enforced by `.importlinter`'s layers-contract. Ownership table:

  | Owner | Package (import name) | Owns | Contract seam (bút) | Must NOT touch |
  |---|---|---|---|---|
  | **DE — Nguyễn Đông Anh** | `packages/kb` (`studio_kb`) | KB pipeline (doc-factory, chunk/embed/index, fence-DATA `kb.search`, consent-purge), trace sink, cost table, golden-set | trace-event schema · `kb.search` API | Workbench/validator/Tenant-Wall (SWE); interpreter/executor/fence-executor/EmbeddingService (AIE-1); eval harness/judge/scorecard-render (AIE-2) |
  | **SWE — Thiệu Quang Minh** | `packages/workbench` (`studio_workbench`) | Workbench UI (form+canvas wiring), recipe validator/graph-lint, publish/eval-gate wiring, version/rollback, Tenant-Wall (INV-1) | recipe schema | KB pipeline/`kb.search`-filter/trace-sink/golden-set (DE); interpreter/executor/fence-executor (AIE-1); eval-harness/judge/scorecard-render (AIE-2 — SWE only wires the gate that *reads* the verdict) |
  | **AIE-1 — Trần Bá Đạt** | `packages/engine` (`studio_engine`) | Interpreter, 6 node executors, `EmbeddingService` 2-impl, fence-EXECUTOR | consumes `kb.search` + `EmbeddingService` (no contract bút) | Workbench/Tenant-Wall/eval-gate-wiring (SWE); doc-factory/`kb.search`-filter/trace-sink/golden-set (DE — consumes only); eval-harness/judge/scorecard (AIE-2 — supplies citations only) |
  | **AIE-2 — Lưu Tiến Duy** | `packages/evalhub` (`studio_evalhub`) | Eval harness, LLM-judge + agreement-check, scorecard render, trace UX | scorecard format | eval-gate-wiring/publish/rollback (SWE — AIE-2 only supplies the verdict); golden-set (DE — consumes only); interpreter/executor/fence-executor/EmbeddingService (AIE-1 — consumes citations only); Tenant-Wall/INV-1 |

  Full cross-owner boundary detail: `plans/260717-1516-studio-kit-template/research/studio-spec-and-workspace.md`
  §A4. `apps/studio` (composition root, `core.*`+`obs.*` schema) and `apps/web` (Vite/React Flow
  scaffold) are **mentor**-owned — every quadrant package imports `studio_contracts` only, never
  each other or `apps/studio` (DIP, enforced by `.importlinter`).
- **8** — **step Studio lifecycle demo** (money-shot steps in bold): (1) form creates agent ·
  (2) attach 2 tools + 1 KB scope · (3) draw a 6-node-palette canvas DAG · (4) Test → trace
  timeline with live tokens/cost · **(5) fence-proof — ask a Tenant-Y-only question while scoped
  to Tenant-X → refusal + audit, leakage=0** · (6) Eval → scorecard 30-case golden set → gate
  PASS → Publish · **(7) degrade instructions → re-eval → gate BLOCKS publish → rollback** ·
  (8) `hitl-pause` node suspends the run in the playground, resumes after approval. Wired
  progressively through the phases; tied together as one system-level spec in
  `tests/e2e/test_lifecycle.py` (P10, RED-by-design until the 4 quadrants fill their business
  logic).

## How to run

```bash
make setup      # uv sync — one venv, one lockfile, all 6 Python members resolved
make dev        # docker compose up -d (default profile — pgvector, wired in P3/P9)
make test       # uv run pytest — full workspace suite
make leak-test  # RLS/tenant leak-test — has teeth by design (a leaky kb.search stays RED)
make demo       # 8-step lifecycle demo harness (wired in P10 — see tests/e2e/test_lifecycle.py)
make lint       # ruff check . && mypy strict (packages + apps) && lint-imports (layers-contract)
```

`apps/web` (Vite + React Flow, empty scaffold — Decision #11) is a separate Node project, NOT a
Python workspace member:

```bash
cd apps/web
corepack enable pnpm && pnpm install && pnpm build   # or: npm install && npm run build
pnpm dev   # local dev server
```

## Chạy thử demo Kế hoạch 2 (login → canvas → Test → Publish → Chat)

`make demo` (target ở trên) hiện chỉ là placeholder — chưa nối harness E2E thật (P10). Muốn tự
tay chạy thử luồng demo `apps/studio` + `apps/web` (login → dựng canvas → Test → chấm điểm →
Publish → Chat), làm theo đúng các bước dưới, đã tự chạy thật trên Ubuntu 24.04 để xác nhận.

### Cần cài gì trên máy — KHÔNG cần `pip install` gì cả

| Công cụ | Cần cho | Ghi chú |
|---|---|---|
| `uv >=0.11` | Toàn bộ 6 Python member | `uv` tự quản Python riêng (`uv python install`), tự tạo venv qua `uv sync` — **không cần** cài Python hệ thống hay `pip install` tay bất cứ gói nào. |
| Docker (+ compose plugin) | Postgres/pgvector | `docker compose up -d` (dev stack, port 5432) hoặc `docker compose -f docker-compose.test.yml up -d` (test stack, port 5433, dùng cho bước dưới). |
| Node.js + npm | `apps/web` | `apps/web` KHÔNG nằm trong `uv` workspace (Vite/TS riêng) — cần Node để `npm install`/`npm run dev`. |

`pip install` duy nhất xuất hiện trong repo là dòng ghi chú optional `pip install .[obs]` (Langfuse,
`.env.example`) — không cần cho demo, không cần cho bất kỳ `make` target nào ở trên.

### Các bước

```bash
# 1. Cài dependency Python + copy env mẫu
make setup
cp .env.example .env
# Sửa .env: STUDIO_JWT_SECRET phải >= 32 ký tự (Settings() raise ValidationError lúc khởi động
# nếu ngắn hơn — vá kit#129 §3.3 mục #3, VinSOC pentest). .env.example đã để sẵn 1 placeholder
# đủ dài để chạy dev ngay, nhưng KHÔNG dùng nguyên placeholder đó cho môi trường thật — xem
# `openssl rand -hex 32` để sinh khoá thật.

# 2. Bật Postgres — dùng ĐÚNG dev stack (docker-compose.yml, port 5432, db "studio"), khớp
# NGUYÊN VẸN giá trị mặc định trong .env.example — không cần sửa STUDIO_DATABASE_URL nào cả.
# (docker-compose.test.yml là stack RIÊNG cho `make test-int`/CI, port 5433 khác — đừng lẫn 2
# stack, .env chỉ trỏ đúng 1 trong 2.)
docker compose up -d

# 3. Seed 2 tenant demo (ankor/borea) — BẮT BUỘC trước lần chạy đầu, và sau MỖI LẦN chạy
# `make test`/`pytest` (fixture `admin_pool` truncate toàn bộ bảng, kể cả `core.tenants`).
# CHẠY TỪ GỐC KIT, ĐỪNG `cd apps/studio` trước — `.env` chỉ nằm ở gốc kit, Settings() tìm
# `.env` theo thư mục đang đứng (CWD) khi lệnh chạy, không theo vị trí file script.
uv run python apps/studio/scripts/seed_demo_tenants.py

# 4. Chạy backend (apps/studio) — cửa sổ terminal riêng. Lần khởi động này chạy lifespan = dựng
# schema (`ensure_all_schemas`) + CẤP QUYỀN DML cho role `studio_app` (`grant_app_privileges`,
# `app.py:39-40`). PHẢI lên TRƯỚC bước 5: `studio_app` chỉ có quyền INSERT vào `kb.chunks` SAU khi
# backend boot — chạy ingest trước sẽ gãy `permission denied for schema kb`.
# `--no-proxy-headers` (app#18): uvicorn mặc định tự tin `X-Forwarded-For` từ MỌI kết nối tới từ
# 127.0.0.1 (kể cả `curl localhost` ngay trên máy này) và ghi đè `request.client` TRƯỚC KHI app
# thấy request — độc lập với `STUDIO_TRUST_X_FORWARDED_FOR`, nên bỏ cờ này thì rate-limit
# `/api/auth/login` né được bằng cách tự set header giả, không cần chạm gì tới cờ app. CHỈ bỏ cờ
# này (và bật `STUDIO_TRUST_X_FORWARDED_FOR=true`) khi triển khai THẬT có reverse proxy đáng tin
# GHI ĐÈ (không nối thêm) `X-Forwarded-For` trước khi tới app.
uv run uvicorn studio_app.app:create_app --factory --app-dir apps/studio/src --host 127.0.0.1 --port 8000 --reload --no-proxy-headers

# 5. Nạp corpus Callisto vào kb.chunks (42 doc / 140 chunk: ankor 71 · borea 69) — CHẠY TỪ GỐC KIT,
# cửa sổ terminal riêng, SAU khi backend (bước 4) đã in "Application startup complete". BẮT BUỘC
# trước khi demo chat/retrieval. Sau mỗi lần `make test`/`pytest` (fixture truncate `kb.chunks` +
# `core.tenants`) chỉ cần chạy lại BƯỚC 3 + 5 — KHÔNG phải restart backend (truncate xoá dòng, không
# xoá grants). THIẾU BƯỚC NÀY → `kb.search` trả RỖNG, chat không ra kết quả.
# Script đọc `STUDIO_DATABASE_URL` từ BIẾN MÔI TRƯỜNG (không tự nạp .env như backend) → export đúng
# dev-stack DSN dưới đây; KHỚP NGUYÊN VẸN .env.example, role non-owner `studio_app` để RLS WITH CHECK
# còn cắn. Idempotent — chạy lại không nhân đôi.
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5432/studio
uv run python packages/kb/scripts/ingest_callisto.py

# 6. Chạy frontend (apps/web) — cửa sổ terminal riêng
cd apps/web
npm install
npm run dev   # mặc định http://127.0.0.1:5173
```

### Đăng nhập — chỉ còn 1 đường, bằng mật khẩu thật

`POST /api/auth/demo-login` (đăng nhập chỉ bằng email, không mật khẩu) đã bị **xoá hoàn toàn**
khỏi `apps/studio/src/studio_app/routes/auth.py`. Không còn bảng tài khoản demo nào để đăng nhập
ngay — mọi tài khoản (kể cả để tự thử/demo) phải được **tạo trước** qua `core.users` (mật khẩu
băm bcrypt thật), theo đúng 1 trong 2 cách dưới.

**Cách A — bootstrap superadmin rồi tự tạo công ty MỚI qua UI** (công ty trống, không có sẵn corpus
Callisto — dùng để thử luồng quản trị, không dùng để thử canvas/chat có nội dung thật):

```bash
export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5432/studio
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5432/studio
export STUDIO_SUPERADMIN_EMAIL=superadmin@agentcore.internal
export STUDIO_SUPERADMIN_PASSWORD=<mật khẩu tự chọn, tối thiểu 8 ký tự>
uv run python apps/studio/scripts/seed_superadmin.py
```

Đăng nhập bằng `STUDIO_SUPERADMIN_EMAIL`/`STUDIO_SUPERADMIN_PASSWORD` ở `http://127.0.0.1:5173` —
màn hình DUY NHẤT của superadmin là "Tạo công ty mới" (`POST /api/admin/companies`). Tạo xong,
đăng xuất rồi đăng nhập bằng email/mật khẩu admin vừa tạo — tài khoản đó có tab "Quản trị" để tự
tạo thêm nhân viên (`POST /api/admin/users`, chọn roles qua checkbox).

**Cách B — gán tài khoản thật vào tenant `ankor`/`borea` đã seed sẵn** (có ngay corpus Callisto
71/69 chunk từ bước 5 — dùng cách này nếu muốn thử canvas/chat ra nội dung thật). `create_company`
LUÔN tạo tenant MỚI (UUID ngẫu nhiên), không có route nào gắn thẳng vào 1 trong 2 tenant có sẵn
này — chèn thẳng 1 dòng `core.users` bằng script nhỏ:

```bash
# Chạy từ apps/studio (`uv run python` cần thấy được package `studio_app`).
cd apps/studio
uv run python - <<'PY'
import asyncio, sys
# Windows: psycopg async từ chối ProactorEventLoop mặc định — cùng workaround
# apps/studio/tests/conftest.py và scripts/seed_superadmin.py đã dùng. Không cần trên Linux/macOS.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from studio_app.jwt_auth import hash_password
from studio_app.core._db import get_admin_pool, close_pools

ANKOR_ID = "a0000000-0000-0000-0000-000000000001"  # packages/workbench/src/studio_workbench/builder.py

async def main() -> None:
    pool = await get_admin_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO core.users (tenant_id, email, password_hash, roles) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (email) DO NOTHING",
            (ANKOR_ID, "admin@ankor.vn", hash_password("doi-mat-khau-nay-truoc-khi-dung-that"), ["admin", "public", "hr", "finance", "engineering"]),
        )
    await close_pools()

asyncio.run(main())
PY
```

Đăng nhập bằng `admin@ankor.vn` / mật khẩu vừa đặt — canvas thấy đủ, Test ra chunk KB thật (không
rỗng, vì role có đủ cả 4 role nội dung). Cùng cách này, đổi `ANKOR_ID`/email/roles để tạo tài khoản
chỉ có 1 role nội dung (thử ca "chỉ thấy Chat, không thấy canvas" — role thiếu `"admin"`).

Rồi Publish (tự chạy `EvalHarness` trên nguyên golden-set + gate trong 1 lần bấm).

**`recipe_hash` (DEC-03) đã có producer thật VÀ đã được nối vào đường publish** — producer
`studio_workbench.publish.recipe_hash()` merge ở
[`agentcore-studio-workbench#27`](https://github.com/AI20K-VGR/agentcore-studio-workbench/pull/27),
call-site merge ở [`agentcore-studio-app#26`](https://github.com/AI20K-VGR/agentcore-studio-app/pull/26):
`_evaluate` truyền `recipe=` vào `EngineAgentRunner` (nên recipe được CHẤM đúng là recipe được
PUBLISH — đóng kit#127) rồi truyền `recipe_hash=recipe_hash(recipe)` vào `EvalHarness.run()`.
⇒ `Publish` **không còn LUÔN trả 409**. 409 giờ chỉ còn nghĩa `gate.verdict == "FAIL"` thật (agent
chưa đạt ngưỡng) hoặc `scorecard.recipe_hash` lệch với recipe đang publish.

## CI + branch protection (F16)

GitHub Actions (`.github/workflows/ci.yml`) is the CI **SSOT**; `.gitlab-ci.yml` is a minimal
lint+test mirror only. CI has 4 jobs: `lint`, `test` (per-package matrix), `leak-test`, `build`.

**`leak-test` is red-by-design and must NEVER block a merge.** It exercises the tenant-fence
anti-tamper/closed-set guards before the owning quadrant (DE) ships the real `kb.search` fence —
until that lands, this job is expected to fail. It runs with `continue-on-error: true` so its own
job status never turns the workflow run red, but that is a CI-level guard, not a branch-protection
one: if this repo's GitHub **required status checks** are ever configured as "require branches to
be up to date" + an explicit checks list, add the checks by name (`lint`, `test / *`, `build`) and
deliberately leave `leak-test` OUT of that list. This is a manual repo-settings step (Settings →
Branches → branch protection rule → required status checks) — nothing in this kit automates it,
and no code here substitutes for checking it once the repo exists on GitHub.

## Fallback (Hướng A)

If per-package `uv`/mypy/IDE tooling costs the mentor too much time in week 0, the directory tree
can stay exactly as-is while collapsing to a single root `pyproject.toml` (Hướng A) — the ownership
boundary (packaging + CI-per-package + **per-repo permission** + schema-per-quadrant) still holds
without a true workspace. Not the default; documented here as an explicit escape hatch.

> **Phân phối repo & phân quyền:** kit được tách thành **1 repo cha + 6 submodule** (mỗi domain 1
> repo private, ranh giới quyền cứng ở tầng git). CODEOWNERS đã gỡ. Quy trình đầy đủ: **`GITFLOWS.md`**.
