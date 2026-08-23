<#
.SYNOPSIS
    1 lệnh dựng full stack agentcore-studio-kit cho dev cục bộ — CHỈ cần Docker (không cần
    python/uv/pnpm/Node trên máy host). Idempotent: chạy lại bao nhiêu lần cũng an toàn.

.DESCRIPTION
    Giai đoạn 1 — Database (postgres):
      1. Container `postgres` (docker-compose.yml, project "studio") đang chạy rồi -> bỏ qua bước
         khởi tạo. Chưa chạy (kể cả tồn tại nhưng đang dừng) -> `docker compose up -d postgres`
         rồi đợi healthcheck.
      2. Áp lại docker/postgres-init/*.sql (3 role + extension pgvector) — idempotent, phòng volume
         cũ từ trước khi 2 file này tồn tại.
      3. Tạo/kiểm schema `core.*` — DDL embed ở đây, copy khớp
         `apps/studio/src/studio_app/core/schema.py::_CORE_DDL`. Redundant một phần với bước 5
         (app tự chạy `ensure_all_schemas()` lúc boot) nhưng vô hại (idempotent) — giữ để DB vẫn
         seed được ngay cả khi chỉ muốn phần DB, không cần bật backend.
      4. Seed 3 tài khoản mẫu bằng pgcrypto (bcrypt ngay trong SQL, không cần python):
           - superadmin@gmail.com / 123456789 — roles=[superadmin], tenant "__system__"
           - admin@gmail.com      / 123456789 — roles=[admin],      tenant "default"
           - user@gmail.com       / 123456789 — roles=[hr],         tenant "default"
         Idempotent: ON CONFLICT (email) DO NOTHING — chạy lại không đổi mật khẩu đã có.

    Giai đoạn 2 — Backend + Frontend:
      5. `.env` chưa có -> copy từ `.env.example` (placeholder dev-safe, fake providers bật sẵn,
         không cần API key thật). Đã có -> giữ nguyên, không ghi đè.
      6. Build + start `docker compose --profile app up -d --build` — service `app` (backend,
         Dockerfile gốc repo) + `web` (frontend, `apps/web/Dockerfile` — Vite dev server, mới thêm
         cho máy không có Node/pnpm). `app` lifespan tự chạy `ensure_all_schemas()` +
         `grant_app_privileges()` lần nữa (đủ cả kb/wb/obs/eval — ngoài phạm vi core.* ở bước 3).
      7. `STUDIO_DATABASE_URL(_ADMIN|_SCORER)` bị ép về hostname service `postgres` (KHÔNG đọc
         theo `.env`) khi build/chạy 3 container này — `.env` mặc định trỏ `localhost:5432` (đúng
         cho luồng host README §"Chạy thử demo": backend chạy NGOÀI Docker, container Postgres lộ
         cổng ra host) — trong network riêng của compose, `localhost` là CHÍNH container `app`,
         không phải container `postgres`, nên nối theo `localhost` sẽ timeout (`PoolTimeout`, đã
         thực nghiệm xác nhận). Set qua process env ở ĐÂY, không sửa `.env` của bạn.
      8. Đợi backend healthy (`/openapi.json`, route công khai mặc định của FastAPI) rồi báo URL +
         tài khoản đăng nhập.

.EXAMPLE
    powershell -File scripts\dev-up.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message"
}

function Write-Warn {
    param([string]$Message)
    Write-Host "    [WARN] $Message" -ForegroundColor Yellow
}

# --- Cấu hình --------------------------------------------------------------
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $RepoRoot 'docker-compose.yml'
$PostgresInitDir = Join-Path $RepoRoot 'docker\postgres-init'
$EnvFile = Join-Path $RepoRoot '.env'
$EnvExampleFile = Join-Path $RepoRoot '.env.example'
$DbName = 'studio'
$SuperUser = 'postgres'
$OwnerUser = 'studio_owner'

if (-not (Test-Path $ComposeFile)) {
    throw "Không tìm thấy docker-compose.yml tại $ComposeFile — chạy script từ đúng repo agentcore-studio-kit."
}

# `apps/studio` + `apps/web` (build image ở bước 8) đều là git submodule riêng — clone THIẾU cờ
# `--recurse-submodules` (hoặc quên `git submodule update --init --recursive`) để lại 2 thư mục
# RỖNG. `docker build` trên thư mục rỗng vẫn chạy được đến 1 lúc rồi lỗi mù mờ (thiếu
# pyproject.toml/package.json) — không có chữ "submodule" nào trong thông điệp, dễ đi sai hướng
# tìm nguyên nhân (đúng cái bẫy README đã cảnh báo ở bước clone). Chặn sớm, nói thẳng nguyên nhân.
$submoduleMarkers = @{
    'apps/studio' = Join-Path $RepoRoot 'apps\studio\pyproject.toml'
    'apps/web'    = Join-Path $RepoRoot 'apps\web\package.json'
}
$emptySubmodules = @($submoduleMarkers.Keys | Where-Object { -not (Test-Path $submoduleMarkers[$_]) })
if ($emptySubmodules.Count -gt 0) {
    throw "Submodule rỗng: $($emptySubmodules -join ', ') — chạy 'git submodule update --init --recursive' từ gốc repo rồi thử lại."
}

# --- Bước 0: kiểm Docker daemon ---------------------------------------------
Write-Step "Kiểm tra Docker"
try {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw "docker info thoát mã $LASTEXITCODE" }
} catch {
    throw "Docker daemon chưa chạy (hoặc Docker chưa cài). Mở Docker Desktop rồi chạy lại script."
}
Write-Info "Docker daemon OK."

# --- Bước 1: container postgres đã chạy chưa? -------------------------------
Write-Step "Kiểm tra container postgres (docker-compose.yml, project 'studio')"
$pgContainerId = (& docker compose -f $ComposeFile ps -q postgres) | Select-Object -First 1
$pgRunning = $false
if ($pgContainerId) {
    $state = & docker inspect -f '{{.State.Running}}' $pgContainerId 2>$null
    if ($state -eq 'true') { $pgRunning = $true }
}

if ($pgRunning) {
    Write-Info "Container postgres đang chạy rồi ($pgContainerId) — bỏ qua bước khởi tạo image mới."
} else {
    Write-Info "Chưa chạy — khởi tạo qua 'docker compose up -d postgres' (image pgvector/pgvector:pg17)..."
    & docker compose -f $ComposeFile up -d postgres
    if ($LASTEXITCODE -ne 0) { throw "docker compose up -d postgres thất bại (exit $LASTEXITCODE)." }
    $pgContainerId = (& docker compose -f $ComposeFile ps -q postgres) | Select-Object -First 1
    if (-not $pgContainerId) { throw "Không tìm thấy container postgres sau khi 'up -d' — kiểm log bằng: docker compose -f `"$ComposeFile`" logs postgres" }
}

# --- Bước 2: đợi container "healthy" (helper dùng lại cho cả postgres lẫn app) ---
function Wait-ContainerHealthy {
    param(
        [Parameter(Mandatory)][string]$ContainerId,
        [Parameter(Mandatory)][string]$Label,
        [int]$TimeoutSeconds = 90
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $health = & docker inspect -f '{{.State.Health.Status}}' $ContainerId 2>$null
        if ($health -eq 'healthy') { return $true }
        Start-Sleep -Seconds 2
    }
    Write-Warn "$Label không healthy sau ${TimeoutSeconds}s."
    return $false
}

Write-Step "Đợi Postgres sẵn sàng (healthcheck)"
if (-not (Wait-ContainerHealthy -ContainerId $pgContainerId -Label 'Postgres' -TimeoutSeconds 60)) {
    throw "Xem log: docker compose -f `"$ComposeFile`" logs postgres"
}
Write-Info "Postgres healthy."

# --- Helper: chạy SQL bên trong container qua unix socket (không cần mật
# khẩu — pg_hba mặc định của image postgres là 'trust' cho kết nối local/unix
# socket, đã verify thật: docker exec ... psql -U studio_owner không cần PGPASSWORD). -------------
function Invoke-Sql {
    param(
        [Parameter(Mandatory)][string]$AsUser,
        [Parameter(Mandatory)][string]$Sql
    )
    # KHÔNG dùng `2>&1` ở đây (PowerShell 5.1 bọc từng dòng stderr của native exe thành
    # NativeCommandError kể cả khi exit code = 0 — psql in NOTICE ra stderr, sẽ tự nổ dù chạy đúng.
    # stderr của native exe đã được terminal hiện sẵn; chỉ cần đọc $LASTEXITCODE để biết pass/fail).
    $Sql | & docker exec -i $pgContainerId psql -U $AsUser -d $DbName -v ON_ERROR_STOP=1 -q | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "psql (user=$AsUser) thất bại (exit $LASTEXITCODE): $($Sql.Substring(0, [Math]::Min(120, $Sql.Length)))..."
    }
}

# Trả về danh sách dòng (mỗi dòng 1 cột, đã trim) — dùng cho các câu SELECT cần đọc kết quả.
function Invoke-SqlScalar {
    param(
        [Parameter(Mandatory)][string]$AsUser,
        [Parameter(Mandatory)][string]$Sql
    )
    # `-q` BẮT BUỘC: thiếu nó, psql vẫn in tag hoàn tất lệnh (VD "INSERT 0 0") ra stdout dù đã có
    # `-t` (tuples-only chỉ tắt header/footer của KẾT QUẢ truy vấn, không tắt tag này) — thực nghiệm
    # xác nhận, thiếu `-q` thì dòng "INSERT 0 0" lẫn vào $raw khiến 1 INSERT 0 dòng (ON CONFLICT DO
    # NOTHING, email đã tồn tại) bị đọc nhầm thành "có kết quả" -> báo "đã tạo" sai cho email cũ.
    $raw = $Sql | & docker exec -i $pgContainerId psql -U $AsUser -d $DbName -v ON_ERROR_STOP=1 -t -A -F '|' -q
    if ($LASTEXITCODE -ne 0) {
        throw "psql (user=$AsUser) thất bại khi đọc kết quả (exit $LASTEXITCODE)."
    }
    return ($raw | Where-Object { $_.Trim() -ne '' })
}

# --- Bước 3: role + extension (idempotent, áp lại từ chính docker/postgres-init/*.sql —
# 1 nguồn sự thật duy nhất, không copy trùng SQL sang đây) -------------------
Write-Step "Áp lại role (studio_owner/studio_app/studio_scorer) + extension pgvector"
foreach ($file in @('00-roles.sql', '01-extensions.sql')) {
    $path = Join-Path $PostgresInitDir $file
    if (-not (Test-Path $path)) {
        Write-Warn "Thiếu $path — bỏ qua (nếu volume Postgres còn mới, initdb đã tự chạy các file này rồi)."
        continue
    }
    Get-Content -Raw $path | & docker exec -i $pgContainerId psql -U $SuperUser -d $DbName -v ON_ERROR_STOP=1 -q | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Áp $file thất bại (exit $LASTEXITCODE)." }
    Write-Info "$file OK."
}

# --- Bước 4: schema core.* (chạy như studio_owner — khớp F1/F2: studio_owner OWN mọi bảng
# nó tạo, để FORCE ROW LEVEL SECURITY sau này bắt cả owner). Nguồn: core/schema.py::_CORE_DDL. ---
Write-Step "Tạo/kiểm schema core.* (tenants, users, sections, user_sections, jobs, outbox, embedding_cache)"
$coreDdl = @'
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
'@
Invoke-Sql -AsUser $OwnerUser -Sql $coreDdl | Out-Null
Write-Info "DDL core.* áp xong (idempotent — bảng đã có thì CREATE TABLE IF NOT EXISTS chỉ no-op)."

# Grant DML cho studio_app trên schema core — khớp grant_app_privileges() (core/schema.py).
$grantSql = @'
GRANT USAGE ON SCHEMA core TO studio_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core TO studio_app;
ALTER DEFAULT PRIVILEGES FOR ROLE studio_owner IN SCHEMA core
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO studio_app;
'@
Invoke-Sql -AsUser $OwnerUser -Sql $grantSql | Out-Null
Write-Info "Grant DML cho studio_app trên schema core OK."

# --- Bước 5: kiểm cấu trúc schema thật (query information_schema, không chỉ tin IF NOT EXISTS) --
Write-Step "Kiểm cấu trúc schema core.* (đối chiếu bằng query, không chỉ tin theo IF NOT EXISTS)"
$expectedTables = @('embedding_cache', 'jobs', 'outbox', 'sections', 'tenants', 'user_sections', 'users')
$actualTablesRaw = Invoke-SqlScalar -AsUser $OwnerUser -Sql "SELECT table_name FROM information_schema.tables WHERE table_schema = 'core' ORDER BY table_name;"
$actualTables = @($actualTablesRaw | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
$missingTables = @($expectedTables | Where-Object { $actualTables -notcontains $_ })
if ($missingTables.Count -gt 0) {
    Write-Warn "Thiếu bảng trong schema core: $($missingTables -join ', ')"
} else {
    Write-Info "Đủ 7 bảng core.*: $($actualTables -join ', ')"
}

$expectedUserCols = @('id', 'tenant_id', 'email', 'password_hash', 'roles', 'created_by', 'created_at', 'is_active', 'password_changed_at')
$actualUserColsRaw = Invoke-SqlScalar -AsUser $OwnerUser -Sql "SELECT column_name FROM information_schema.columns WHERE table_schema='core' AND table_name='users';"
$actualUserCols = @($actualUserColsRaw | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
$missingCols = @($expectedUserCols | Where-Object { $actualUserCols -notcontains $_ })
if ($missingCols.Count -gt 0) {
    Write-Warn "core.users thiếu cột: $($missingCols -join ', ') — có thể do bảng cũ tạo trước khi script này tồn tại. Kiểm tay bằng: docker exec $pgContainerId psql -U studio_owner -d studio -c '\d core.users'"
} else {
    Write-Info "core.users đủ cột đúng thiết kế."
}

# --- Bước 6: seed 3 tài khoản (idempotent) ----------------------------------
Write-Step "Seed tenant + tài khoản mẫu"

function Set-SeedAccount {
    param(
        [Parameter(Mandatory)][string]$TenantName,
        [Parameter(Mandatory)][string]$Email,
        [Parameter(Mandatory)][string]$Password,
        [Parameter(Mandatory)][string]$Role
    )
    # Tenant: tạo nếu chưa có, idempotent qua ON CONFLICT.
    Invoke-Sql -AsUser $OwnerUser -Sql "INSERT INTO core.tenants (name) VALUES ('$TenantName') ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name;" | Out-Null

    # User: ON CONFLICT (email) DO NOTHING + RETURNING email để biết mới tạo hay đã tồn tại sẵn
    # (đúng khuôn seed_superadmin.py/seed_demo_tenants.py — KHÔNG đổi mật khẩu nếu email đã có).
    $sql = @"
INSERT INTO core.users (tenant_id, email, password_hash, roles)
SELECT t.id, '$Email', crypt('$Password', gen_salt('bf', 12)), ARRAY['$Role']
FROM core.tenants t WHERE t.name = '$TenantName'
ON CONFLICT (email) DO NOTHING
RETURNING email;
"@
    $result = Invoke-SqlScalar -AsUser $OwnerUser -Sql $sql
    if ($result -and $result.Count -gt 0) {
        Write-Info "Đã tạo $Email (role=$Role, tenant=$TenantName)."
    } else {
        Write-Info "$Email đã tồn tại từ trước — giữ nguyên (không đổi mật khẩu)."
    }
}

Set-SeedAccount -TenantName '__system__' -Email 'superadmin@gmail.com' -Password '123456789' -Role 'superadmin'
Set-SeedAccount -TenantName 'default'    -Email 'admin@gmail.com'      -Password '123456789' -Role 'admin'
Set-SeedAccount -TenantName 'default'    -Email 'user@gmail.com'       -Password '123456789' -Role 'hr'

# --- Bước 7: .env cho backend/frontend --------------------------------------
Write-Step "Kiểm .env"
if (-not (Test-Path $EnvFile)) {
    if (-not (Test-Path $EnvExampleFile)) {
        throw "Không có .env lẫn .env.example tại $RepoRoot — không dựng được backend."
    }
    Copy-Item $EnvExampleFile $EnvFile
    Write-Info "Chưa có .env — tạo mới từ .env.example (fake providers bật sẵn, không cần API key thật)."
} else {
    Write-Info ".env đã có sẵn — giữ nguyên, không ghi đè."
}

# --- Bước 8: build + start backend (apps/studio) + frontend (apps/web) -----
Write-Step "Build + khởi động backend + frontend (docker compose --profile app)"

# `.env` mặc định trỏ DATABASE_URL vào `localhost` (đúng cho luồng backend chạy NGOÀI Docker,
# README §"Chạy thử demo") — bên trong network riêng của compose, `localhost` là CHÍNH container
# `app`, không phải container `postgres`, nên nối theo `.env` sẽ treo tới `PoolTimeout` rồi crash
# (đã thực nghiệm xác nhận nguyên văn lỗi này). Ép 3 DSN này về hostname service `postgres` qua
# process env NGAY TRƯỚC KHI gọi compose — không sửa file `.env` của bạn.
$env:STUDIO_DATABASE_URL = 'postgresql://studio_app:changeme@postgres:5432/studio'
$env:STUDIO_DATABASE_URL_ADMIN = 'postgresql://studio_owner:changeme@postgres:5432/studio'
$env:STUDIO_DATABASE_URL_SCORER = 'postgresql://studio_scorer:changeme@postgres:5432/studio'

& docker compose -f $ComposeFile --profile app up -d --build
if ($LASTEXITCODE -ne 0) { throw "docker compose --profile app up -d --build thất bại (exit $LASTEXITCODE) — xem log phía trên." }

$appContainerId = (& docker compose -f $ComposeFile ps -q app) | Select-Object -First 1
if (-not $appContainerId) { throw "Không tìm thấy container app sau khi 'up -d' — kiểm log: docker compose -f `"$ComposeFile`" logs app" }

Write-Step "Đợi backend sẵn sàng (healthcheck /openapi.json)"
if (-not (Wait-ContainerHealthy -ContainerId $appContainerId -Label 'Backend (app)' -TimeoutSeconds 90)) {
    throw "Backend không lên được. Xem log: docker compose -f `"$ComposeFile`" logs app"
}
Write-Info "Backend healthy."

$webContainerId = (& docker compose -f $ComposeFile ps -q web) | Select-Object -First 1
$webState = if ($webContainerId) { & docker inspect -f '{{.State.Running}}' $webContainerId 2>$null } else { 'false' }
if ($webState -eq 'true') {
    Write-Info "Frontend (web) đang chạy."
} else {
    Write-Warn "Frontend (web) chưa thấy chạy — kiểm log: docker compose -f `"$ComposeFile`" logs web"
}

# --- Tổng kết ----------------------------------------------------------------
Write-Step "Xong"
Write-Info "Backend:  http://127.0.0.1:8000  (docs: http://127.0.0.1:8000/docs)"
Write-Info "Frontend: http://127.0.0.1:5173"
Write-Info "DB:       postgresql://studio_owner:changeme@localhost:5432/$DbName  (admin, DDL)"
Write-Info "          postgresql://studio_app:changeme@localhost:5432/$DbName    (runtime, DML)"
Write-Host ""
Write-Host "    Tài khoản seed (mật khẩu chỉ dùng local dev):" -ForegroundColor Cyan
Write-Host "    - superadmin@gmail.com / 123456789  -> roles=[superadmin], tenant=__system__"
Write-Host "    - admin@gmail.com      / 123456789  -> roles=[admin],      tenant=default"
Write-Host "    - user@gmail.com       / 123456789  -> roles=[hr],         tenant=default"
Write-Host ""
Write-Host "    Dừng toàn bộ:  docker compose --profile app down" -ForegroundColor DarkGray
Write-Host ""
