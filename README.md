# agentcore-studio-kit

Production-grade `uv` workspace template for **AgentCore Studio** — a Mini-Studio where 4 OJT
engineers (DE · SWE · AIE-1 · AIE-2) build an AI-agent authoring tool end to end: form → tool+KB
(with tenant fence) → 6-node canvas → Test/trace (token+cost) → eval-gate → Publish.

Infra (Docker/Postgres/CI/contracts/RLS/queue/OTel) is WIRE — it runs Day-1. Business logic in the
4 quadrant packages is intentionally TRÔNG (`Protocol` + `NotImplementedError` + a RED acceptance
test = the spec each engineer fills in). See `docs/decisions/README.md` for the full decision record.

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

  `apps/studio` (composition root, `core.*`+`obs.*` schema) and `apps/web` (Vite/React Flow
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

`apps/web` (Vite + React Flow — Decision #11; canvas/Playground/Chat all built out, 22 `.tsx` files,
NOT an empty scaffold anymore) is a separate Node project, NOT a Python workspace member:

```bash
cd apps/web
corepack enable pnpm && pnpm install && pnpm build   # CI-canonical (--frozen-lockfile, ci.yml)
pnpm dev   # local dev server
```

`apps/web` ships both `pnpm-lock.yaml` (canonical, CI runs `pnpm install --frozen-lockfile`) and
`package-lock.json` — use `pnpm`, not `npm`: nothing tests the `npm` path, and 2 lockfiles can
resolve 2 different dependency trees on 2 clean clones.

## Chạy thử demo Kế hoạch 2 (login → canvas → Test → Publish → Chat)

`make demo` (target ở trên) hiện chỉ là placeholder — chưa nối harness E2E thật (P10). Muốn tự
tay chạy thử luồng demo `apps/studio` + `apps/web` (login → dựng canvas → Test → chấm điểm →
Publish → Chat), làm theo đúng các bước dưới, đã tự chạy thật trên Ubuntu 24.04 để xác nhận.

### Cần cài gì trên máy — KHÔNG cần `pip install` gì cả

| Công cụ | Cần cho | Ghi chú |
|---|---|---|
| `uv >=0.11` | Toàn bộ 6 Python member | `uv` tự quản Python riêng (`uv python install`), tự tạo venv qua `uv sync` — **không cần** cài Python hệ thống hay `pip install` tay bất cứ gói nào. |
| Docker (+ compose plugin) | Postgres/pgvector | `docker compose up -d` (dev stack, port 5432) hoặc `docker compose -f docker-compose.test.yml up -d` (test stack, port 5433, dùng cho bước dưới). |
| Node.js + `pnpm` | `apps/web` | `apps/web` KHÔNG nằm trong `uv` workspace (Vite/TS riêng) — cần Node + `corepack enable pnpm`. `pnpm-lock.yaml` là canonical (CI dùng `--frozen-lockfile`); đừng dùng `npm install` dù repo có sẵn `package-lock.json`. |

`pip install` duy nhất xuất hiện trong repo là dòng ghi chú optional `pip install .[obs]` (Langfuse,
`.env.example`) — không cần cho demo, không cần cho bất kỳ `make` target nào ở trên.

### Các bước

```bash
# 0. Clone — BẮT BUỘC kèm cờ submodule. `apps/studio` + 6 `packages/*` đều là git submodule riêng
# (repo private); clone thiếu cờ này để lại 9 thư mục RỖNG, và `make setup` ở bước 1 gãy bằng lỗi
# nội bộ của `uv` — thông điệp KHÔNG có chữ "submodule" nào, dễ đi sai hướng tìm nguyên nhân. Đo
# thật trên 1 clone trần: `agentcore-studio-contracts references a workspace in tool.uv.sources,
# but is not a workspace member`.
git clone --recurse-submodules <repo-url>
cd agentcore-studio-kit
# Đã lỡ clone KHÔNG kèm submodule? Sửa tại chỗ, không cần clone lại:
git submodule update --init --recursive

# 1. Cài dependency Python + copy env mẫu
make setup
cp .env.example .env
# STUDIO_JWT_SECRET >= 32 ký tự (raise ValidationError nếu ngắn hơn) — sinh khoá thật bằng
# `openssl rand -hex 32`, đừng dùng nguyên placeholder cho môi trường thật.
# Bỏ comment STUDIO_JUDGE_CACHE_PATH/CAP_PATH, điền đường TUYỆT ĐỐI ghi được trên máy bạn. Cần
# ngay từ bước này (LLMJudge dựng vô điều kiện kể cả fake providers) — thiếu ⇒ `PermissionError`
# (Linux) / `OSError: Read-only file system` (macOS) thành 500 CHƯA BẮT khi bấm "Chấm điểm"; đường
# tương đối (khác CWD) làm counter quota tách đôi âm thầm.

# 2. Bật Postgres — dev stack (docker-compose.yml, port 5432), khớp mặc định .env.example, không
# cần sửa STUDIO_DATABASE_URL. (docker-compose.test.yml là stack RIÊNG cho test/CI, port 5433.)
docker compose up -d

# 3. Seed 2 tenant demo (ankor/borea) — bắt buộc trước lần chạy đầu và sau mỗi `make test`/`pytest`
# (fixture truncate cả `core.tenants`). CHẠY TỪ GỐC KIT — Settings() tìm `.env` theo CWD.
uv run python apps/studio/scripts/seed_demo_tenants.py

# 3b. CHỈ KHI demo bằng provider THẬT (bắt buộc để "Chấm điểm" ra số có nghĩa). Mặc định
# STUDIO_USE_FAKE_PROVIDERS=true (stub) ⇒ luồng chạy nhưng điểm không phản ánh chất lượng thật.
# Bốn biến sau, thiếu 1 là hỏng giữa demo:
#
#   STUDIO_USE_FAKE_PROVIDERS=false
#   STUDIO_LLM_PROVIDER=openai            # file mẫu ship `gemini` — hay bị quên, hỏng CÂM (không 500)
#   STUDIO_OPENAI_API_KEY=sk-...          # LLM trả lời + LLM-judge
#   STUDIO_OPENROUTER_API_KEY=sk-or-...   # embedding gemini-embedding-001@2048; thiếu ⇒ 503 cả /evaluate lẫn /chat
#
# (STUDIO_JUDGE_CACHE_PATH/CAP_PATH đã set ở bước 1 — cần cho mọi đường /evaluate, không riêng 3b.)
# STUDIO_OPENAI_MODEL để trống = gpt-4o-mini (model duy nhất đo PASS: evalhub#31 0.9889/1.0000;
# o4-mini FAIL). ĐỪNG khai STUDIO_OPENAI_BASE_URL= rỗng — "" khác None, làm mọi call LLM chết
# APIConnectionError.
# Judge quota 100 call/ngày — 1 lượt "Chấm điểm" tốn 8-16 call (~6-9 lượt/ngày); xoá file cap
# trước demo để về 0.

# 4. Chạy backend (apps/studio) — cửa sổ terminal riêng. Lifespan dựng schema + cấp quyền DML cho
# studio_app — PHẢI lên TRƯỚC bước 5 (ingest trước sẽ gãy "permission denied for schema kb").
# `--no-proxy-headers`: uvicorn mặc định tin X-Forwarded-For từ mọi kết nối 127.0.0.1, cho phép né
# rate-limit login bằng header giả — chỉ bỏ cờ này khi có reverse proxy thật GHI ĐÈ header đó.
uv run uvicorn studio_app.app:create_app --factory --app-dir apps/studio/src --host 127.0.0.1 --port 8000 --reload --no-proxy-headers

# 5. Nạp corpus Callisto 2.0 vào kb.chunks (80 doc/800 chunk: ankor 400 · borea 400) — CHẠY TỪ GỐC
# KIT, cửa sổ terminal riêng, SAU khi backend (bước 4) in "Application startup complete". Sau mỗi
# `make test`/`pytest` (truncate kb.chunks) chỉ cần chạy lại BƯỚC 3 + 5, không restart backend.
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5432/studio
uv run python packages/kb/scripts/ingest_callisto_v2.py

# ⚠️ ĐÚNG script là `..._v2.py`. Bản 1.0 (`ingest_callisto.py`) dùng bộ nhúng bag-of-words — corpus
# và query nằm ở HAI không gian vector khác nhau, recall@3 rơi từ 22/22 xuống 1/22, KHÔNG lỗi nào
# nổ. `..._v2.py` đọc vector từ cache đã commit, không cần API key.
# Kiểm (qua superuser postgres — studio_app/studio_owner đều NOSUPERUSER, RLS chặn thấy full 800):
#   docker compose exec postgres psql -U postgres -d studio \
#     -c "select vector_dims(embedding), count(*) from kb.chunks group by 1;"
#   →  2048 | 800

# 6. Chạy frontend (apps/web) — cửa sổ terminal riêng
cd apps/web
corepack enable pnpm && pnpm install   # KHÔNG dùng npm install — xem cảnh báo pnpm/npm ở trên
pnpm dev   # mặc định http://127.0.0.1:5173
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

> 3 mục UI dưới đây (canvas/trace/chat) khớp đúng con trỏ `apps/web` đang ghim ở PR này
> (`0e4bd1e`, web#10). `apps/web` main đã đi trước ít nhất 1 commit (`9688e6f`, web#11 — gộp tab
> "Agent đã publish" vào Canvas qua `OpenAgentModal.tsx`, đổi panel role thành "Thử vai trò"). Nếu
> con trỏ kit đã bump qua khỏi `0e4bd1e` lúc bạn đọc, tự kiểm lại 3 chỗ trước khi tin: tab
> "Agent đã publish"/Rollback, khối "Test agent với role", và cách nạp 1 recipe cũ vào canvas.

### Dựng recipe trên canvas

Admin đăng nhập vào thẳng tab **Canvas**. Tab này mở ra đã có sẵn 1 khung agent
`agent-callisto-d12` với DAG mẫu 4 node (`kb-retrieve → llm-step → tool-call → end`) và
`golden_set_ref: callisto-2.0-golden-30-v1` — khớp đúng corpus vừa nạp ở bước 5, dùng luôn để đi
hết luồng mà không cần vẽ tay. Sidebar phải báo "graph-lint: 7/7 luật sạch" khi recipe hợp lệ.

Muốn tự dựng agent mới: bấm **"Tạo agent"** (cột trái) → đặt tên → kéo node từ Palette vào canvas
(6 loại đóng: KB Retrieve, LLM Step, Condition, Tool Call, HITL Pause, End) → nối cạnh bằng kéo
chuột giữa 2 handle → bấm đúp 1 node để sửa param (`query`/`top_k`/`section_roles` cho KB Retrieve,
`temperature` cho LLM Step, `tool` cho Tool Call…), bấm đúp 1 cạnh để sửa `when`. Bấm đúp thanh
tiêu đề khung mở **"Cấu hình Agent"**: Định danh (`agent_id`/`instructions`/`model`), Tool
whitelist, KB Binding (`kb_id` + section scope), Eval Gate (`golden_set_ref` + ngưỡng
`success`/`citation_accuracy`). graph-lint fail-closed — Test/Publish khoá cứng tới khi đủ 7 luật:
6 loại node · cạnh có đích · 1 start node · ≤1 cạnh ra mỗi node · không chu trình · kết ở `end` ·
tool nằm trong whitelist.

### Chạy — Test → xem trace

Sidebar phải, mục **Playground**, bấm **Test** (khoá nếu graph-lint đỏ) → `POST /api/runs`,
interpreter chạy DAG thật, rồi UI tự `GET /api/runs/{run_id}` lại bằng 1 request TÁCH RIÊNG (không
tin thẳng response POST) để chứng minh trace ghi đúng — hiện `TraceViewer`: từng event theo đúng
thứ tự dispatch, có `node_type`/`node_id`/timestamp/`tokens {prompt, completion}`/citations/
outputs, cộng dòng tổng `Σtokens=…`.

**Trung thực:** `cost` mỗi event hiện LUÔN in "chưa đo" — `interpreter.py` chưa có nguồn cost thật
(cost-lineage còn mở, kit#120). `tokens` là số thật, `cost` thì chưa wire — đừng báo cáo cost như
đã đo.

### Chấm điểm → Publish

Mục **Chấm điểm**, bấm nút cùng tên → `POST /api/agents/{agent_id}/evaluate`, chạy nguyên
`golden_set_ref` qua `EvalHarness` thật, hiện `verdict`/`success_rate`/`citation_accuracy` — CHƯA
publish, chỉ xem điểm trước. Nút **Publish** chỉ **sáng** khi lần Chấm điểm gần nhất `verdict=PASS`
cho ĐÚNG recipe đang có trên canvas (đổi bất cứ gì sau khi chấm điểm làm nút tắt lại — phải chấm
lại). Bấm Publish gọi `POST /api/agents/{agent_id}/publish` — server tự chấm lại từ đầu (không tin
điểm client) rồi gate thật; kết quả `published` (kèm nút "Sang tab Chat để thử") hoặc `blocked`
(HTTP 409, kèm lý do + scorecard, nút "Sang tab Rollback"). `409` chỉ khi `gate.verdict == "FAIL"`
thật hoặc `scorecard.recipe_hash` lệch với recipe đang publish — không phải luôn-409.

**Đo được, đừng tưởng treo:** với provider thật, 1 lượt Chấm điểm chạy nguyên 30 case mất **~55s**,
Publish (chấm lại + gate) mất thêm **~43s** — không thấy phản hồi trong vài giây đầu là bình
thường, đừng bấm lại (đo sống, review PR#196 @dholmes0207, 2026-08-20).

**Biên mỏng ở golden set:** ngưỡng `success` mặc định 0.9 trên 30 case cần **≥27/30**. Đo 2 lượt
liên tiếp cùng cấu hình ra `29/30` (0.9667) rồi `28/30` (0.9333) — chỉ cách FAIL đúng 1-2 case. Nếu
demo sống cho Gate-3, đừng coi 1 lần PASS là ổn định; chạy lại vài lượt trước buổi chấm thật.

Nhánh **chặn phía server đã xác nhận sống** (không còn là lý thuyết đọc code):
`POST /publish → HTTP 409`, message `"gate.verdict='FAIL' … blocked (INV-6); previously published
version re-asserted live"` kèm scorecard — nghĩa là bản published cũ vẫn đứng, không bị artifact
tệ đè lên (đo sống, review PR#196 @dholmes0207, 2026-08-20). Cách chắc ăn nhất để tự tái tạo: sửa 2
ngưỡng `success`/`citation_accuracy` trong "Cấu hình Agent" lên gần 1.0 trước khi Chấm điểm —
verdict FAIL gần như chắc chắn với model thật, nút Publish khoá lại ngay trên UI.

**Rollback thì CHƯA ai xác nhận sống** (kể cả người đo nhánh chặn ở trên) — nằm ở tab "Agent đã
publish": chọn agent → chọn version cũ ở dropdown → bấm **Rollback**
(`POST /api/agents/{agent_id}/rollback`) — cần đã publish ≥2 version mới có gì để rollback về. *Tự
tay thử qua 1 lượt trước khi đưa nhánh rollback vào evidence-pack Gate-3.*

### Dùng — chat với agent đã publish

Tab **"Dùng thử"** (icon chat) — dropdown chọn agent đã publish (tên hiển thị dạng đọc được, vd
"Agent callisto d12"; giá trị gửi lên server vẫn là `agent_id` slug gốc). Admin thấy thêm khối
"Test agent với role" (checkbox theo phòng ban, mặc định tick hết) để tự thu hẹp role trước khi
hỏi — dùng đúng ô này làm phép fence-proof: bỏ tick phòng ban/tenant kia, hỏi 1 câu chỉ dữ liệu
phòng ban đó mới có — kỳ vọng agent từ chối hoặc không trả lời đúng. Gõ câu hỏi → **Gửi** →
`POST /api/agents/{agent_id}/chat`; trả lời kèm badge version, citation (nếu có), và nút "Xem
trace" mở lại đúng `TraceViewer` của lượt chat đó qua `run_id` riêng của lượt đó.

Tài khoản chỉ có role nội dung (thiếu `"admin"`, xem cách tạo ở trên) đăng nhập vào thẳng màn hình
chat toàn màn hình này, không thấy tab nào khác — đúng hành vi "employee chỉ dùng, không xây".

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

## Phân phối repo & phân quyền

Kit được tách thành **1 repo cha + 6 submodule** (mỗi domain 1 repo private, ranh giới quyền cứng ở
tầng git). CODEOWNERS đã gỡ. Quy trình đầy đủ: **`GITFLOWS.md`**.

(Fallback tooling cho mentor ở Tuần 0, "Hướng A" — collapse về 1 root `pyproject.toml` nếu
per-package `uv`/mypy/IDE tốn quá nhiều thời gian — chi tiết ở `docs/ONBOARDING.md`.)
