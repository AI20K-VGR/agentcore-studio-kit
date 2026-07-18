# Code Standards — `agentcore-studio-kit`

> Chuẩn code de-facto (house-style VSF) mà template này áp dụng — copy pattern từ
> `document-intake` production (`plans/260717-1516-studio-kit-template/research/document-intake-patterns.md`,
> viết tắt R-DI, ở repo root) + điều chỉnh cho uv workspace 4-quadrant. Mọi mục dưới đây đã đối
> chiếu trực tiếp với `pyproject.toml`, `.importlinter`, và code thật trong
> `agentcore-studio-kit/**` — không suy diễn.

## 1. Python & workspace

- `requires-python = ">=3.14"` — khai **giống hệt** ở root `pyproject.toml` VÀ mọi 6 member
  (`packages/{contracts,kb,engine,workbench,evalhub}/pyproject.toml` + `apps/studio/pyproject.toml`).
- **1 `uv.lock` duy nhất ở root** — resolve toàn bộ workspace. `[tool.uv.workspace] members =
  ["packages/*", "apps/*"]` + `exclude = ["apps/web"]` (Vite/TS, không phải Python member).
  `[tool.uv.sources]` khai `{ workspace = true }` cho cả 6 dist Python — cross-member dependency
  resolve nội bộ, không kéo qua PyPI.
- Root là **umbrella, không mang code riêng** — `[tool.hatch.build.targets.wheel] bypass-selection =
  true` (nếu không, hatchling từ chối build wheel cho project không có package khám phá được).
- Mỗi workspace member là **1 distribution độc lập** — `[project].name` riêng
  (`agentcore-studio-{contracts,kb,engine,workbench,evalhub,app}`), không gộp chung 1 wheel kiểu
  `[tool.hatch.build.targets.wheel].packages=[...]` (đó là anti-pattern AgentSpace — không phải
  workspace thật).

## 2. Ruff

Cấu hình duy nhất ở root `pyproject.toml`, áp cho toàn workspace (không có `[tool.ruff]` riêng ở
từng member):

```toml
[tool.ruff]
line-length = 120
src = ["packages", "apps"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
```

Chạy: `uv run ruff check .` (job `lint` trong `.github/workflows/ci.yml` + `.gitlab-ci.yml`, cũng là
target `lint` trong `Makefile`). `.pre-commit-config.yaml` chạy `ruff --fix` + `ruff-format` trên
mỗi commit.

## 3. Mypy — strict, plugin pydantic, `py.typed`

```toml
[tool.mypy]
strict = true
python_version = "3.14"
plugins = ["pydantic.mypy"]
```

- `strict = true` áp cho **toàn** `packages` + `apps` (`uv run mypy packages apps`) — không có
  override per-member.
- Plugin `pydantic.mypy` bắt buộc vì mọi contract (`packages/contracts/src/studio_contracts/*.py`)
  là pydantic `BaseModel` — không có plugin, mypy strict sẽ không hiểu đúng `ConfigDict`/`Field`.
- **`py.typed` marker** có mặt ở đúng 4 package: `packages/{contracts,kb,workbench,evalhub}/src/
  studio_*/py.typed` — đây là điều kiện để cross-package import (vd `studio_app` import
  `studio_kb.schema`) được mypy strict type-check mà **không cần `# type: ignore[import-untyped]`**.
  `studio_engine` và `studio_app` hiện **không** có `py.typed` trong cây — một package mới thêm vào
  workspace và muốn được type-check nghiêm khi package khác import nó phải tự thêm marker này.
- Chạy: `uv run mypy packages apps` (job `lint`, target `lint` Makefile).

## 4. Pytest

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = [
    "tests",
    "packages/contracts/tests",
    "packages/kb/tests",
    "packages/engine/tests",
    "packages/workbench/tests",
    "packages/evalhub/tests",
    "apps/studio/tests",
]
```

`asyncio_mode = "auto"` — mọi `async def test_...` chạy được không cần `@pytest.mark.asyncio` thủ
công (toàn bộ codebase là async-first, xem §5).

### 4.1. Red-by-design — 2 loại test, không lẫn nhau

Template dùng `pytest.mark.xfail(strict=False)` (builtin marker, không cần sửa `pyproject.toml`) cho
mọi seam **ĐỂ TRỐNG** — test đỏ là đặc tả hành vi owner phải cài, và `strict=False` khiến việc PASS
sớm (impl một phần) báo cáo XPASS vô hại thay vì fail cả suite (không phạt tiến độ dở dang). Ví dụ đã
verify: `packages/engine/tests/test_interpreter_contract.py`,
`packages/workbench/tests/test_graph_lint.py`, `packages/evalhub/tests/test_eval_gate.py`,
`packages/kb/tests/test_leak.py`.

**Có 2 hình thức xfail khác hẳn nhau về ý nghĩa — đừng nhầm:**

1. **Spec-contract test** (hợp lệ dùng `pytest.raises(NotImplementedError)`) — khoá đúng trạng thái
   STUB hiện tại của một seam chưa cài (vd `test_run_not_implemented`,
   `test_graph_lint_not_implemented`, `packages/kb/tests/test_search_contract.py`). Đây **không**
   phải hành vi nghiệp vụ/bảo mật — chỉ là "seam này hiện raise, đúng như spec nói".
2. **Behavioral fence test** (**KHÔNG BAO GIỜ** được thoả mãn chỉ bằng `pytest.raises
   (NotImplementedError)`) — test một thuộc tính nghiệp vụ/bảo mật thật (vd cách ly cross-tenant).
   Bằng chứng: `packages/kb/tests/test_leak.py` — seed 2 tenant thật (`_seed_chunk` qua
   `admin_pool`), gọi `KbSearchService.search` qua **đường app**, rồi assert **loại trừ** cross-tenant
   (`"chunk-b-1" not in result_chunk_ids`) VÀ assert **bao gồm** đúng chunk của tenant đang truy vấn
   (`"chunk-a-1" in result_chunk_ids` — "positive teeth" để một impl trả `[]` rỗng không false-pass
   phần loại trừ). Một impl leaky (trả hết mọi chunk) vẫn **FAIL** test này — đây là "có răng" (F5).
   Cặp với `packages/kb/tests/test_leak_meta.py` — **anti-tamper**, grep source `test_leak.py` còn
   đủ assertion T1(IDOR)+T6(label-spoof), tự nó luôn XANH (không xfail), chặn ai đó âm thầm làm rỗng
   leak-test để giả xanh.

**Quy tắc anti-slop rút ra:** một test khẳng định một thuộc tính bảo mật/nghiệp vụ thật KHÔNG BAO GIỜ
được viết dưới dạng "assert raises NotImplementedError" — làm vậy là giả-xanh khi seam được lấp đầy
(một impl sai vẫn không raise `NotImplementedError` nữa, và test sẽ PASS dù logic sai). Chỉ test khoá
"seam này hiện chưa cài" mới được dùng hình thức đó.

## 5. Data layer — async psycopg, no ORM

- `psycopg[binary,pool]>=3.2` là driver duy nhất — không SQLAlchemy, không Alembic (verify: không
  import nào của 2 lib này trong toàn bộ `packages/`/`apps/`).
- Raw SQL, tham số hoá bằng `%s` placeholder qua `conn.execute(sql, params)` (vd
  `obs/trace_writer.py::PgTraceWriter.write`, `core/queue.py`).
- **`sql.Identifier`/`sql.Literal` cho identifier/utility-statement** — không nội suy chuỗi Python
  trực tiếp vào SQL:
  - `sql.Literal` — `middleware.py` dùng cho `SET LOCAL app.tenant_id = {}` (utility statement
    không nhận bind parameter qua wire protocol).
  - `sql.Identifier` — `core/schema.py::grant_app_privileges` dùng cho tên schema trong câu
    `GRANT`/`ALTER DEFAULT PRIVILEGES`; `conftest.py::_truncate_all` dùng cho
    `TRUNCATE TABLE {schema}.{table}`.
- **DDL-SSOT idempotent** — mọi `ddl()` (5 file: `core/schema.py`, `obs/schema.py`,
  `packages/{kb,workbench,evalhub}/src/studio_*/schema.py`) chỉ dùng `CREATE SCHEMA/TABLE/INDEX IF
  NOT EXISTS`; policy RLS dùng `DROP POLICY IF EXISTS ... ; CREATE POLICY ...` để idempotent (drop-
  rồi-tạo-lại, không phải `IF NOT EXISTS` vì Postgres không hỗ trợ cú pháp đó cho `CREATE POLICY`).
  Không dùng migration tool (Alembic/dbmate) — README của kit ghi rõ: có prod data thật thì chuyển
  sang migration tool, greenfield thì DDL-SSOT đủ.
- **Schema-per-quadrant `ddl()` + aggregator** — mỗi package export `ddl() -> str` riêng (không
  copy-paste DDL tập trung); `apps/studio/src/studio_app/core/schema.py::ensure_all_schemas()`
  direct-import 4 module quadrant (`_QUADRANT_SCHEMA_MODULES`, sorted theo tên module) + `core.ddl()`
  của chính nó, chạy tuần tự qua **admin pool**.
- **Pool split cho RLS** — `core/_db.py::get_admin_pool()` (role `studio_owner`, chỉ dùng DDL+GRANT
  lúc boot) tách biệt hoàn toàn với `get_pool()` (role `studio_app`, request path/DML — pool duy
  nhất RLS thật sự áp). Không bao giờ chạy DDL/GRANT qua `get_pool()`, không bao giờ chạy query
  request-path qua `get_admin_pool()` — trộn 2 pool là chính xác lỗ hổng "1 pool cho mọi thứ" mà
  pattern này tồn tại để chặn.

## 6. Contracts (`packages/contracts`)

- Mọi model pydantic dùng `model_config = ConfigDict(frozen=True)` — mutate instance sau khi tạo
  phải raise `ValidationError` (verify: `test_freeze_guard.py::test_frozen_rejects_mutation`).
- Field dùng alias reserved-keyword (vd `Edge.from_` với `Field(alias="from")`, vì `from` là
  Python keyword) **bắt buộc** `model_config` có thêm `populate_by_name=True` — cho phép build bằng
  cả tên field (`from_=...`) lẫn alias (`from=...`). Round-trip test phải verify **cả 2 chiều**
  (`by_alias=True` và mặc định) — chỉ test 1 chiều là "XANH giả" (F12,
  `packages/contracts/tests/test_roundtrip.py`).
- `SCHEMA_VERSION = "0.1.0-draft"` khai module-level ở `studio_contracts/__init__.py` — v0-draft
  (chưa freeze thật), nhưng discipline additive-only áp dụng từ ngày đầu: thêm field OPTIONAL không
  cần bump version; **rename/xoá/thêm field REQUIRED là breaking** — cần DEC + bump
  `SCHEMA_VERSION`. Test khoá điều này: `test_freeze_guard.py::test_required_add_breaks_old_payload`
  (simulate model có thêm field required, validate payload cũ → phải raise `ValidationError`).
- `packages/contracts` là **bottom import-layer** — chỉ phụ thuộc `pydantic` (+ stdlib `typing`),
  không bao giờ import package `studio_*` khác (verify bằng `.importlinter` + `uv run lint-imports`).

## 7. Kiến trúc — import-linter, DIP, direct composition

- `.importlinter` layers-contract (root): `studio_app` (top) > `studio_kb | studio_engine |
  studio_workbench | studio_evalhub` (siblings, không import chéo) > `studio_contracts` (bottom).
  Enforce bằng `uv run lint-imports` — chạy trong mọi phase gate + CI job `lint`.
- DIP qua `typing.Protocol` (`@runtime_checkable`, khai ở `packages/contracts/src/studio_contracts/
  protocols.py` + `kb.py`): `EmbeddingService`, `LLM`, `TraceWriter`, `KbSearch`. Không có thân hàm ở
  layer contracts — impl (WIRED hoặc `NotImplementedError` spec) nằm ở quadrant/`apps/studio`.
- **Direct composition, KHÔNG DI-framework** — `apps/studio/src/studio_app/app.py::create_app()`
  wire trực tiếp (FastAPI factory + lifespan gọi `get_admin_pool()` → `ensure_all_schemas` →
  `grant_app_privileges`), không container DI 3-tầng kiểu AgentSpace anti-pattern
  (`InfrastructureContainer`/`ApplicationContainer`/`ClientsContainer`).

## 8. Ownership — per-repo permission (multi-repo), closed node-set

- **Ranh giới quyền = per-repo (submodule)**, KHÔNG dùng CODEOWNERS nữa (đã gỡ — trên GitHub-private-
  Free, CODEOWNERS + branch-protection không thành hard-gate được). Mỗi domain là submodule-repo riêng:
  `packages/kb`→DE (Nguyễn Đông Anh), `packages/engine`→AIE-1 (Trần Bá Đạt), `packages/workbench`→SWE (Thiệu Quang Minh), `packages/evalhub`→AIE-2 (Lưu Tiến Duy),
  `packages/contracts`→mentor (đổi cần duyệt), `apps/studio`→mentor. Owner có **write**, người khác **read**
  → chặn CỨNG ở tầng git. Phân quyền + thao tác chi tiết: **`GITFLOWS.md`**.
- **6 `NodeType` đóng** (`packages/contracts/src/studio_contracts/nodes.py`, `StrEnum`):
  `kb-retrieve`, `llm-step`, `condition`, `tool-call`, `hitl-pause`, `end`. Đây là **nguồn duy nhất**
  — `packages/engine/src/studio_engine/registry.py` import từ đây (không tự định nghĩa lại); thêm
  giá trị thứ 7 hoặc bất kỳ DSL turing-complete nào là **cấm cứng** — khoá bằng
  `test_registry_has_exactly_six` + validation pydantic enum tại tầng `Node.type` (từ chối construct
  giá trị ngoài 6).

## 9. Git

- Conventional commits (`feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`) — mỗi phase =
  1 commit riêng (hoặc 1 commit-range) theo `plan.md` §Rollback (repo root
  `plans/260717-1516-studio-kit-template/plan.md`).
- Trailer `Co-Authored-By` khi commit được tạo qua agent — không chèn ngôn ngữ quảng cáo AI vào nội
  dung commit message/code comment (no AI-reference slop).
- Rollback theo phase: revert theo range, chạy lại regression gate của phase trước; batch P5–P8 độc
  lập nhau (revert 1 quadrant không ảnh hưởng 3 quadrant còn lại, vì file-ownership disjoint và
  class/`ddl()` stub từ P1 vẫn còn).

## 10. Security

- **2-role least-privilege** (`docker/postgres-init/00-roles.sql`) — `studio_owner` (owner, DDL) và
  `studio_app` (non-owner, DML) đều `NOSUPERUSER`; xem chi tiết cơ chế RLS đầy đủ ở
  `docs/system-architecture.md` §4.
- **`FORCE ROW LEVEL SECURITY` + `WITH CHECK`** trên `kb.chunks` (`packages/kb/src/studio_kb/
  schema.py`) — bắt buộc cả 2 mệnh đề (`ENABLE` không đủ: thiếu `FORCE` thì owner vẫn bypass; thiếu
  `WITH CHECK` thì chỉ chặn đọc, không chặn ghi cross-tenant).
- **Dev credentials `changeme`** (`docker/postgres-init/00-roles.sql`, `.env.example`,
  `docker-compose.yml`) — **PHẢI đổi** trước khi triển khai bất kỳ môi trường chia sẻ/không phải máy
  dev cá nhân nào. Không có cơ chế rotate tự động trong kit — trách nhiệm người triển khai.
- **NDA denylist pre-commit** (`.pre-commit-config.yaml` hook `nda-denylist` → `scripts/
  nda-denylist.sh`) — chặn file mentor/rubric/answer-key commit vào bất kỳ repo nào (repo cha hoặc 6
  submodule mà học viên có quyền write). Cài hook này ở mỗi repo. (Phân phối = multi-repo submodule,
  xem `GITFLOWS.md` + `docs/system-architecture.md` §7 — cơ chế subtree-squash-1-repo cũ đã bỏ.)
- **Secrets qua env, không hardcode** — `Settings` (`apps/studio/src/studio_app/settings.py`,
  `pydantic-settings`, prefix `STUDIO_`) đọc mọi khoá (Gemini API key, Langfuse keys, 2 DSN) từ
  `.env`/environment; `.env.example` liệt kê đủ biến, `.env` thật nằm trong `.gitignore`.
