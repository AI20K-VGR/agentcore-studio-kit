#!/usr/bin/env bash
# 1 lệnh dựng full stack agentcore-studio-kit cho dev cục bộ trên Linux — CHỈ cần Docker (không
# cần python/uv/pnpm/Node trên máy host). Idempotent: chạy lại bao nhiêu lần cũng an toàn.
# Bản port của scripts/dev-up.ps1 (Windows/PowerShell) — cùng logic, cùng thứ tự bước, đã verify
# thật trên cả 2 hệ điều hành (không phải đoán theo cú pháp).
#
# Giai đoạn 1 — Database (postgres):
#   1. Container `postgres` (docker-compose.yml, project "studio") đang chạy rồi -> bỏ qua bước
#      khởi tạo. Chưa chạy (kể cả tồn tại nhưng đang dừng) -> `docker compose up -d postgres` rồi
#      đợi healthcheck.
#   2. Áp lại docker/postgres-init/*.sql (3 role + extension pgvector) — idempotent, phòng volume
#      cũ từ trước khi 2 file này tồn tại.
#   3. Tạo/kiểm schema `core.*` — DDL embed ở đây, copy khớp
#      apps/studio/src/studio_app/core/schema.py::_CORE_DDL. Redundant một phần với bước 6 (app tự
#      chạy ensure_all_schemas() lúc boot) nhưng vô hại (idempotent) — giữ để DB vẫn seed được ngay
#      cả khi chỉ muốn phần DB, không cần bật backend.
#   4. Seed 3 tài khoản mẫu bằng pgcrypto (bcrypt ngay trong SQL, không cần python):
#        - superadmin@gmail.com / 123456789 — roles=[superadmin], tenant "__system__"
#        - admin@gmail.com      / 123456789 — roles=[admin],      tenant "default"
#        - user@gmail.com       / 123456789 — roles=[hr],         tenant "default"
#      Idempotent: ON CONFLICT (email) DO NOTHING — chạy lại không đổi mật khẩu đã có.
#
# Giai đoạn 2 — Backend + Frontend:
#   5. `.env` chưa có -> copy từ `.env.example` (placeholder dev-safe, fake providers bật sẵn,
#      không cần API key thật). Đã có -> giữ nguyên, không ghi đè.
#   6. Build + start `docker compose --profile app up -d --build` — service `app` (backend,
#      Dockerfile gốc repo) + `web` (frontend, apps/web/Dockerfile — Vite dev server). `app`
#      lifespan tự chạy ensure_all_schemas() + grant_app_privileges() lần nữa (đủ cả
#      kb/wb/obs/eval — ngoài phạm vi core.* ở bước 3).
#   7. STUDIO_DATABASE_URL(_ADMIN|_SCORER) bị ép về hostname service `postgres` (KHÔNG đọc theo
#      .env) khi build/chạy 3 container này — .env mặc định trỏ localhost:5432 (đúng cho luồng
#      host README §"Chạy thử demo": backend chạy NGOÀI Docker) — trong network riêng của compose,
#      localhost là CHÍNH container app, không phải container postgres, nối theo localhost sẽ
#      timeout (PoolTimeout, đã thực nghiệm xác nhận). Set qua process env ở ĐÂY, không sửa .env.
#   8. Đợi backend healthy (/openapi.json, route công khai mặc định của FastAPI) rồi báo URL + tài
#      khoản đăng nhập.
#
# Dùng: ./scripts/dev-up.sh   (hoặc  bash scripts/dev-up.sh — không cần chạy từ gốc repo)

set -euo pipefail

# --- output helpers (màu chỉ bật khi stdout là TTY thật) --------------------
if [ -t 1 ]; then
    C_CYAN=$'\033[36m'; C_YELLOW=$'\033[33m'; C_GRAY=$'\033[90m'; C_RESET=$'\033[0m'
else
    C_CYAN=''; C_YELLOW=''; C_GRAY=''; C_RESET=''
fi

log_step() { printf '\n%s==> %s%s\n' "$C_CYAN" "$1" "$C_RESET"; }
log_info() { printf '    %s\n' "$1"; }
log_warn() { printf '    %s[WARN] %s%s\n' "$C_YELLOW" "$1" "$C_RESET"; }

die() { printf '\nERROR: %s\n' "$1" >&2; exit 1; }

# --- Cấu hình ----------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.yml"
POSTGRES_INIT_DIR="$REPO_ROOT/docker/postgres-init"
ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE_FILE="$REPO_ROOT/.env.example"
DB_NAME="studio"
SUPER_USER="postgres"
OWNER_USER="studio_owner"

[ -f "$COMPOSE_FILE" ] || die "Không tìm thấy docker-compose.yml tại $COMPOSE_FILE — chạy script từ đúng repo agentcore-studio-kit."

# apps/studio + apps/web (build image ở bước 8) đều là git submodule riêng — clone THIẾU cờ
# --recurse-submodules (hoặc quên `git submodule update --init --recursive`) để lại 2 thư mục
# RỖNG. `docker build` trên thư mục rỗng vẫn chạy được đến 1 lúc rồi lỗi mù mờ (thiếu
# pyproject.toml/package.json) — không có chữ "submodule" nào trong thông điệp, dễ đi sai hướng
# tìm nguyên nhân (đúng cái bẫy README đã cảnh báo ở bước clone). Chặn sớm, nói thẳng nguyên nhân.
empty_submodules=()
[ -f "$REPO_ROOT/apps/studio/pyproject.toml" ] || empty_submodules+=("apps/studio")
[ -f "$REPO_ROOT/apps/web/package.json" ] || empty_submodules+=("apps/web")
if [ "${#empty_submodules[@]}" -gt 0 ]; then
    die "Submodule rỗng: ${empty_submodules[*]} — chạy 'git submodule update --init --recursive' từ gốc repo rồi thử lại."
fi

# --- Bước 0: kiểm Docker + Docker Compose v2 --------------------------------
log_step "Kiểm tra Docker"
command -v docker >/dev/null 2>&1 || die "Không tìm thấy lệnh 'docker' — cài Docker Engine/Docker Desktop trước."
docker info >/dev/null 2>&1 || die "Docker daemon chưa chạy (hoặc user hiện tại chưa trong nhóm 'docker' — thử 'sudo usermod -aG docker \$USER' rồi đăng nhập lại). Khởi động Docker rồi chạy lại script."
docker compose version >/dev/null 2>&1 || die "Thiếu Docker Compose v2 plugin ('docker compose ...'). Bản 'docker-compose' (v1, có dấu gạch ngang) KHÔNG đủ — cài plugin compose (đi kèm Docker Desktop, hoặc gói 'docker-compose-plugin' trên Linux)."
log_info "Docker + Compose v2 OK."

# --- Bước 1: container postgres đã chạy chưa? -------------------------------
log_step "Kiểm tra container postgres (docker-compose.yml, project 'studio')"
pg_cid="$(docker compose -f "$COMPOSE_FILE" ps -q postgres || true)"
pg_running=false
if [ -n "$pg_cid" ]; then
    state="$(docker inspect -f '{{.State.Running}}' "$pg_cid" 2>/dev/null || echo false)"
    [ "$state" = "true" ] && pg_running=true
fi

if [ "$pg_running" = true ]; then
    log_info "Container postgres đang chạy rồi ($pg_cid) — bỏ qua bước khởi tạo image mới."
else
    log_info "Chưa chạy — khởi tạo qua 'docker compose up -d postgres' (image pgvector/pgvector:pg17)..."
    docker compose -f "$COMPOSE_FILE" up -d postgres
    pg_cid="$(docker compose -f "$COMPOSE_FILE" ps -q postgres || true)"
    [ -n "$pg_cid" ] || die "Không tìm thấy container postgres sau khi 'up -d' — kiểm log bằng: docker compose -f \"$COMPOSE_FILE\" logs postgres"
fi

# --- Bước 2: đợi container "healthy" (helper dùng lại cho cả postgres lẫn app) ---
wait_container_healthy() {
    local cid="$1" label="$2" timeout_s="${3:-90}"
    local waited=0
    while [ "$waited" -lt "$timeout_s" ]; do
        local health
        health="$(docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo '')"
        [ "$health" = "healthy" ] && return 0
        sleep 2
        waited=$((waited + 2))
    done
    log_warn "$label không healthy sau ${timeout_s}s."
    return 1
}

log_step "Đợi Postgres sẵn sàng (healthcheck)"
wait_container_healthy "$pg_cid" "Postgres" 60 || die "Xem log: docker compose -f \"$COMPOSE_FILE\" logs postgres"
log_info "Postgres healthy."

# --- Helper: chạy SQL bên trong container qua unix socket (không cần mật khẩu —
# pg_hba mặc định của image postgres là 'trust' cho kết nối local/unix socket, đã verify thật:
# docker exec ... psql -U studio_owner không cần PGPASSWORD). ---------------------------------
invoke_sql() {
    local as_user="$1" sql="$2"
    printf '%s' "$sql" | docker exec -i "$pg_cid" psql -U "$as_user" -d "$DB_NAME" -v ON_ERROR_STOP=1 -q >/dev/null
}

# In ra danh sách dòng (mỗi dòng 1 cột) — dùng cho các câu SELECT cần đọc kết quả.
# `-q` BẮT BUỘC: thiếu nó, psql vẫn in tag hoàn tất lệnh (VD "INSERT 0 0") ra stdout dù đã có `-t`
# (tuples-only chỉ tắt header/footer của KẾT QUẢ truy vấn, không tắt tag này) — thực nghiệm xác
# nhận, thiếu `-q` thì "INSERT 0 0" lẫn vào kết quả khiến 1 INSERT 0 dòng (ON CONFLICT DO NOTHING,
# email đã tồn tại) bị đọc nhầm thành "có kết quả" -> báo "đã tạo" sai cho email cũ.
invoke_sql_scalar() {
    local as_user="$1" sql="$2"
    printf '%s' "$sql" | docker exec -i "$pg_cid" psql -U "$as_user" -d "$DB_NAME" -v ON_ERROR_STOP=1 -t -A -F'|' -q
}

# Có phần tử $1 nằm trong mảng còn lại không — dùng thay cho PowerShell -notcontains.
array_contains() {
    local needle="$1"; shift
    local x
    for x in "$@"; do [ "$x" = "$needle" ] && return 0; done
    return 1
}

# --- Bước 3: role + extension (idempotent, áp lại từ chính docker/postgres-init/*.sql —
# 1 nguồn sự thật duy nhất, không copy trùng SQL sang đây) -------------------
log_step "Áp lại role (studio_owner/studio_app/studio_scorer) + extension pgvector"
for file in 00-roles.sql 01-extensions.sql; do
    path="$POSTGRES_INIT_DIR/$file"
    if [ ! -f "$path" ]; then
        log_warn "Thiếu $path — bỏ qua (nếu volume Postgres còn mới, initdb đã tự chạy các file này rồi)."
        continue
    fi
    docker exec -i "$pg_cid" psql -U "$SUPER_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -q < "$path" >/dev/null
    log_info "$file OK."
done

# --- Bước 4: schema core.* (chạy như studio_owner — khớp F1/F2: studio_owner OWN mọi bảng nó
# tạo, để FORCE ROW LEVEL SECURITY sau này bắt cả owner). Nguồn: core/schema.py::_CORE_DDL. ---
log_step "Tạo/kiểm schema core.* (tenants, users, sections, user_sections, jobs, outbox, embedding_cache)"
core_ddl=$(cat <<'SQL'
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS obs;

CREATE TABLE IF NOT EXISTS core.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES core.tenants(id),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    roles TEXT[] NOT NULL DEFAULT '{}',
    created_by UUID NULL REFERENCES core.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT true
);

ALTER TABLE core.users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE core.users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ NULL;

CREATE TABLE IF NOT EXISTS core.embedding_cache (
    cache_key TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    embedding vector(2048) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES core.tenants(id),
    name TEXT NOT NULL,
    created_by UUID NOT NULL REFERENCES core.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

CREATE TABLE IF NOT EXISTS core.user_sections (
    user_id UUID NOT NULL REFERENCES core.users (id) ON DELETE CASCADE,
    section_id UUID NOT NULL REFERENCES core.sections (id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, section_id)
);

CREATE TABLE IF NOT EXISTS core.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    idempotency_key TEXT NOT NULL,
    job_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 5,
    leased_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS core.outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    dispatched_at TIMESTAMPTZ
);

-- pgcrypto: dùng crypt()/gen_salt('bf') để băm mật khẩu seed bằng bcrypt NGAY TRONG SQL — verify
-- thật: bcrypt.checkpw() (thư viện python app đang dùng, jwt_auth.py) đọc đúng hash pgcrypto sinh
-- ra ($2a$ prefix), không cần cài python/uv trên máy host.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SQL
)
invoke_sql "$OWNER_USER" "$core_ddl"
log_info "DDL core.* áp xong (idempotent — bảng đã có thì CREATE TABLE IF NOT EXISTS chỉ no-op)."

# Grant DML cho studio_app trên schema core — khớp grant_app_privileges() (core/schema.py).
grant_sql=$(cat <<'SQL'
GRANT USAGE ON SCHEMA core TO studio_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core TO studio_app;
ALTER DEFAULT PRIVILEGES FOR ROLE studio_owner IN SCHEMA core
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO studio_app;
SQL
)
invoke_sql "$OWNER_USER" "$grant_sql"
log_info "Grant DML cho studio_app trên schema core OK."

# --- Bước 5: kiểm cấu trúc schema thật (query information_schema, không chỉ tin IF NOT EXISTS) --
log_step "Kiểm cấu trúc schema core.* (đối chiếu bằng query, không chỉ tin theo IF NOT EXISTS)"
expected_tables=(embedding_cache jobs outbox sections tenants user_sections users)
mapfile -t actual_tables < <(invoke_sql_scalar "$OWNER_USER" "SELECT table_name FROM information_schema.tables WHERE table_schema = 'core' ORDER BY table_name;")
missing_tables=()
for t in "${expected_tables[@]}"; do
    array_contains "$t" "${actual_tables[@]}" || missing_tables+=("$t")
done
if [ "${#missing_tables[@]}" -gt 0 ]; then
    log_warn "Thiếu bảng trong schema core: ${missing_tables[*]}"
else
    log_info "Đủ 7 bảng core.*: ${actual_tables[*]}"
fi

expected_user_cols=(id tenant_id email password_hash roles created_by created_at is_active password_changed_at)
mapfile -t actual_user_cols < <(invoke_sql_scalar "$OWNER_USER" "SELECT column_name FROM information_schema.columns WHERE table_schema='core' AND table_name='users';")
missing_cols=()
for c in "${expected_user_cols[@]}"; do
    array_contains "$c" "${actual_user_cols[@]}" || missing_cols+=("$c")
done
if [ "${#missing_cols[@]}" -gt 0 ]; then
    log_warn "core.users thiếu cột: ${missing_cols[*]} — có thể do bảng cũ tạo trước khi script này tồn tại. Kiểm tay bằng: docker exec $pg_cid psql -U studio_owner -d studio -c '\\d core.users'"
else
    log_info "core.users đủ cột đúng thiết kế."
fi

# --- Bước 6: seed 3 tài khoản (idempotent) ----------------------------------
log_step "Seed tenant + tài khoản mẫu"

set_seed_account() {
    local tenant_name="$1" email="$2" password="$3" role="$4"
    # Tenant: tạo nếu chưa có, idempotent qua ON CONFLICT.
    invoke_sql "$OWNER_USER" "INSERT INTO core.tenants (name) VALUES ('$tenant_name') ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name;"

    # User: ON CONFLICT (email) DO NOTHING + RETURNING email để biết mới tạo hay đã tồn tại sẵn
    # (đúng khuôn seed_superadmin.py/seed_demo_tenants.py — KHÔNG đổi mật khẩu nếu email đã có).
    local sql result
    sql="INSERT INTO core.users (tenant_id, email, password_hash, roles)
SELECT t.id, '$email', crypt('$password', gen_salt('bf', 12)), ARRAY['$role']
FROM core.tenants t WHERE t.name = '$tenant_name'
ON CONFLICT (email) DO NOTHING
RETURNING email;"
    result="$(invoke_sql_scalar "$OWNER_USER" "$sql")"
    if [ -n "$result" ]; then
        log_info "Đã tạo $email (role=$role, tenant=$tenant_name)."
    else
        log_info "$email đã tồn tại từ trước — giữ nguyên (không đổi mật khẩu)."
    fi
}

set_seed_account "__system__" "superadmin@gmail.com" "123456789" "superadmin"
set_seed_account "default"    "admin@gmail.com"      "123456789" "admin"
set_seed_account "default"    "user@gmail.com"       "123456789" "hr"

# --- Bước 7: .env cho backend/frontend --------------------------------------
log_step "Kiểm .env"
if [ ! -f "$ENV_FILE" ]; then
    [ -f "$ENV_EXAMPLE_FILE" ] || die "Không có .env lẫn .env.example tại $REPO_ROOT — không dựng được backend."
    cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
    log_info "Chưa có .env — tạo mới từ .env.example (fake providers bật sẵn, không cần API key thật)."
else
    log_info ".env đã có sẵn — giữ nguyên, không ghi đè."
fi

# --- Bước 8: build + start backend (apps/studio) + frontend (apps/web) -----
log_step "Build + khởi động backend + frontend (docker compose --profile app)"

# .env mặc định trỏ DATABASE_URL vào localhost (đúng cho luồng backend chạy NGOÀI Docker, README
# §"Chạy thử demo") — bên trong network riêng của compose, localhost là CHÍNH container app,
# không phải container postgres, nên nối theo .env sẽ treo tới PoolTimeout rồi crash (đã thực
# nghiệm xác nhận nguyên văn lỗi này). Ép 3 DSN này về hostname service `postgres` qua process env
# NGAY TRƯỚC KHI gọi compose — không sửa file .env của bạn.
export STUDIO_DATABASE_URL='postgresql://studio_app:changeme@postgres:5432/studio'
export STUDIO_DATABASE_URL_ADMIN='postgresql://studio_owner:changeme@postgres:5432/studio'
export STUDIO_DATABASE_URL_SCORER='postgresql://studio_scorer:changeme@postgres:5432/studio'

docker compose -f "$COMPOSE_FILE" --profile app up -d --build

app_cid="$(docker compose -f "$COMPOSE_FILE" ps -q app || true)"
[ -n "$app_cid" ] || die "Không tìm thấy container app sau khi 'up -d' — kiểm log: docker compose -f \"$COMPOSE_FILE\" logs app"

log_step "Đợi backend sẵn sàng (healthcheck /openapi.json)"
wait_container_healthy "$app_cid" "Backend (app)" 90 || die "Backend không lên được. Xem log: docker compose -f \"$COMPOSE_FILE\" logs app"
log_info "Backend healthy."

web_cid="$(docker compose -f "$COMPOSE_FILE" ps -q web || true)"
web_state="false"
[ -n "$web_cid" ] && web_state="$(docker inspect -f '{{.State.Running}}' "$web_cid" 2>/dev/null || echo false)"
if [ "$web_state" = "true" ]; then
    log_info "Frontend (web) đang chạy."
else
    log_warn "Frontend (web) chưa thấy chạy — kiểm log: docker compose -f \"$COMPOSE_FILE\" logs web"
fi

# --- Tổng kết ----------------------------------------------------------------
log_step "Xong"
log_info "Backend:  http://127.0.0.1:8000  (docs: http://127.0.0.1:8000/docs)"
log_info "Frontend: http://127.0.0.1:5173"
log_info "DB:       postgresql://studio_owner:changeme@localhost:5432/$DB_NAME  (admin, DDL)"
log_info "          postgresql://studio_app:changeme@localhost:5432/$DB_NAME    (runtime, DML)"
printf '\n'
printf '%sTài khoản seed (mật khẩu chỉ dùng local dev):%s\n' "$C_CYAN" "$C_RESET"
printf '    - superadmin@gmail.com / 123456789  -> roles=[superadmin], tenant=__system__\n'
printf '    - admin@gmail.com      / 123456789  -> roles=[admin],      tenant=default\n'
printf '    - user@gmail.com       / 123456789  -> roles=[hr],         tenant=default\n'
printf '\n'
printf '%sDừng toàn bộ:  docker compose --profile app down%s\n' "$C_GRAY" "$C_RESET"
printf '\n'
