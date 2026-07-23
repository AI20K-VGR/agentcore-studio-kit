# GITFLOWS — phân quyền & cách thao tác (multi-repo submodule)

Tài liệu này mô tả **cách 4 kỹ sư OJT + mentor làm việc** khi `agentcore-studio-kit` được tách
thành **1 repo cha (workspace) + 7 repo con (submodule)**. Đọc kỹ phần "Pitfalls" ở cuối — 90%
lỗi submodule đến từ đó.

> Vì sao multi-repo thay vì monorepo? Để **ranh giới quyền CỨNG ở tầng git** (bạn A không push
> được vào repo của bạn B) — hoạt động trên **GitHub private + Free**, nơi branch-protection /
> CODEOWNERS-hard-gate bị khoá (cần Pro/Team hoặc public). CODEOWNERS đã được **gỡ bỏ** vì trên
> private-free nó chỉ chạy mức mềm (auto-request reviewer), không chặn được gì.

---

## 1. Bản đồ repo (8 repo: 1 cha + 7 con)

| Path trong workspace | Repo GitHub (private) | Owner (write) | Nội dung |
|---|---|---|---|
| **(gốc)** `agentcore-studio-kit` | `hieubui2409/agentcore-studio-kit` | **mentor** | Repo CHA = workspace root: `pyproject.toml` + `uv.lock` + `docker/` + `docker-compose*.yml` + `.github/` (CI + **reusable-workflow** + **composite action**) + `Makefile` + `conftest.py` + `tests/` + `scripts/` + `docs/` + `GITFLOWS.md` + `README.md`. Ghim con trỏ 7 submodule. |
| `packages/contracts` | `agentcore-studio-contracts` | **mentor** (đổi cần mentor duyệt) | `studio_contracts` — hợp đồng chung (Recipe/TraceEvent/Scorecard/NodeType/Protocol). Ai cũng phụ thuộc → đổi = mentor duyệt. |
| `apps/studio` | `agentcore-studio-app` | **mentor** | `studio_app` — composition root: DB pool-split, RLS fence wiring, middleware, providers, obs, queue. |
| `packages/kb` | `agentcore-studio-kb` | **DE — Nguyễn Đông Anh** | `studio_kb` — KB pipeline + `kb.search` fence-DATA + `kb.chunks` RLS. |
| `packages/engine` | `agentcore-studio-engine` | **AIE-1 — Trần Bá Đạt** | `studio_engine` — interpreter + 6 node executors. |
| `packages/workbench` | `agentcore-studio-workbench` | **SWE — Thiệu Quang Minh** | `studio_workbench` — validator/graph-lint + publish + Tenant-Wall. |
| `packages/evalhub` | `agentcore-studio-evalhub` | **AIE-2 — Lưu Tiến Duy** | `studio_evalhub` — eval harness + judge + scorecard-compute. |
| `apps/web` | `agentcore-studio-web` | **mentor** (SWE — Thiệu Quang Minh sau) | Frontend Vite + React Flow. **App JS độc lập — KHÔNG thuộc uv workspace** (root pyproject `[tool.uv.workspace].exclude`). CI standalone, không cần PAT/reconstruct. |

```
agentcore-studio-kit  (repo CHA — mentor)
├── pyproject.toml · uv.lock · docker/ · .github/ · Makefile · conftest.py · tests/   ← ở repo cha
├── packages/contracts  ─▶ submodule agentcore-studio-contracts   (mentor, đổi cần duyệt)
├── apps/studio         ─▶ submodule agentcore-studio-app         (mentor)
├── packages/kb         ─▶ submodule agentcore-studio-kb          (DE — Nguyễn Đông Anh)
├── packages/engine     ─▶ submodule agentcore-studio-engine      (AIE-1 — Trần Bá Đạt)
├── packages/workbench  ─▶ submodule agentcore-studio-workbench   (SWE — Thiệu Quang Minh)
├── packages/evalhub    ─▶ submodule agentcore-studio-evalhub     (AIE-2 — Lưu Tiến Duy)
└── apps/web            ─▶ submodule agentcore-studio-web          (mentor→SWE Thiệu Quang Minh, JS độc lập)
```

---

## 2. Phân quyền (mentor set 1 lần trên GitHub)

**Nguyên tắc:** mỗi kỹ sư có **write** ở đúng repo domain mình, **read** ở phần còn lại. Đây là
ranh giới CỨNG — không có token = không push được, không phải chỉ chặn ở review.

| Người | Repo có **WRITE** | Repo chỉ **READ** |
|---|---|---|
| **DE — Nguyễn Đông Anh** | `agentcore-studio-kb` | cha, contracts, app, engine, workbench, evalhub |
| **AIE-1 — Trần Bá Đạt** | `agentcore-studio-engine` | cha, contracts, app, kb, workbench, evalhub |
| **SWE — Thiệu Quang Minh** | `agentcore-studio-workbench` **+ `agentcore-studio-web`** | cha, contracts, app, kb, engine, evalhub |
| **AIE-2 — Lưu Tiến Duy** | `agentcore-studio-evalhub` | cha, contracts, app, kb, engine, workbench |
| **mentor** | **tất cả** (admin) | — |
| _web (SWE — Thiệu Quang Minh)_ | `agentcore-studio-web` | mentor giữ **ownership**; SWE có `push` (mở rộng canvas ở sprint sau) |

**Contracts (mentor-approval):** không cấp write cho kỹ sư OJT. Đổi contract → mở PR ở
`agentcore-studio-contracts`, cần **mentor** approve (đây là seam chung, đổi bừa là vỡ cả 4 người).

### Secret cho CI (mentor set 1 lần, xem §9)

CI của **6 repo Python con** + repo **cha** cần đọc các repo private khác để dựng lại workspace →
cần **1 fine-grained PAT read-only**. `web` KHÔNG cần (standalone).

```bash
# 1. Tạo fine-grained PAT: GitHub → Settings → Developer settings → Fine-grained tokens
#    - Resource owner: hieubui2409
#    - Repository access: 7 repo studio (cha + contracts/kb/engine/workbench/evalhub/app) — KHÔNG cần web
#    - Permissions: Contents = Read-only ; Expiration: 90 ngày (nhớ rotate)
# 2. Set secret cho 7 repo (tài khoản user không có org-secret dùng chung → set từng repo):
for r in kit contracts kb engine workbench evalhub app; do
  echo "$PAT" | gh secret set PAT --repo hieubui2409/agentcore-studio-$r
done
```

### Cách mentor cấp quyền (gh CLI)

```bash
# ví dụ cấp cho DE (Nguyễn Đông Anh, username GitHub "DongAnh2704") quyền push vào repo kb
gh api -X PUT repos/hieubui2409/agentcore-studio-kb/collaborators/DongAnh2704 \
  -f permission=push        # push = read+write; các mức: pull|triage|push|maintain|admin

# read-only ở các repo khác:
gh api -X PUT repos/hieubui2409/agentcore-studio-contracts/collaborators/DongAnh2704 -f permission=pull
gh api -X PUT repos/hieubui2409/agentcore-studio-app/collaborators/DongAnh2704       -f permission=pull
gh api -X PUT repos/hieubui2409/agentcore-studio-kit/collaborators/DongAnh2704       -f permission=pull
```
Làm tương tự cho AIE-1 (Trần Bá Đạt · `TranBaDat2607`)→engine, SWE (Thiệu Quang Minh · `Dozyboy`)→workbench **+ web**,
AIE-2 (Lưu Tiến Duy · `dholmes0207`)→evalhub. (Hoặc dùng UI: repo → Settings → Collaborators → Add people.)
Bảng username đầy đủ: `agentcore-studio/03-role-tracks/team-roster.md`.

> Mẹo: dùng **GitHub Team** thay vì add từng người nếu sau này nhiều học viên — gán team-permission
> 1 lần cho mỗi repo.

---

## 3. Clone lần đầu (mọi người)

Submodule **KHÔNG tự tải** khi `git clone` thường. Phải `--recursive`:

```bash
git clone --recursive git@github.com:hieubui2409/agentcore-studio-kit.git
cd agentcore-studio-kit

# nếu lỡ clone quên --recursive:
git submodule update --init --recursive

# dựng môi trường (1 venv cho cả workspace):
make setup                      # = uv sync (cần đủ 6 submodule Python đã init; web không tính)
cp .env.example .env            # điền DSN/key thật
cd apps/web && corepack enable pnpm && pnpm install && cd ..   # frontend (nếu cần)
```

Một kỹ sư chỉ có **read** ở repo người khác vẫn **clone/pull được** (để build/test cả workspace) —
chỉ **không push** được. Đó là ý đồ.

---

## 4. Luồng làm việc hằng ngày — sửa domain của mình

Ví dụ **DE** hiện thực `kb.search`:

```bash
cd packages/kb                  # đi vào submodule (đây là repo agentcore-studio-kb)

# ⚠️ BẮT BUỘC: submodule mặc định ở DETACHED HEAD. Về main + đồng bộ trước:
git checkout main
git pull                        # lấy bản mới nhất

# ⚠️ KHÔNG commit thẳng main — main là nhánh ĐƯỢC BẢO VỆ (callout dưới). Mở nhánh việc:
git checkout -b feat/kb-search  # nhánh <type>/<scope>-<mô-tả> tách từ main

# ... sửa src/studio_kb/search.py ...

git add -A
git commit -m "feat(kb): implement kb.search fail-closed retrieval"
git push -u origin feat/kb-search   # push NHÁNH (KHÔNG push main)
gh pr create --fill --base main     # BẮT BUỘC: main chỉ vào qua PR
# → mentor/CI review → merge PR → main tiến. TUYỆT ĐỐI không tự push vào main.
```

→ **Sau khi PR merge, xong phần việc của bạn.** Bạn KHÔNG cần đụng repo cha. Đồng đội `git submodule
update --remote packages/kb` là thấy code bạn.

> **Vì sao PR chứ không `git push` thẳng main?** Harness cài ở repo bạn liệt `main` là **protected
> branch** (`harness/data/protected-branches.yaml`); pre-push `protected_ref_guard` **chặn** push
> thẳng vào `main` — nó đòi artifact merge-grade y như một PR đã review. Trên GitHub private-free,
> branch-protection/CODEOWNERS-hard-gate bị khoá (xem đầu tài liệu §intro), nên **harness-guard chính
> là lớp thay thế**: kỷ luật "vào main chỉ qua PR" do guard enforce ở tầng local, không phải GitHub.
> Đó là lý do luồng trên đi nhánh + `gh pr create` thay vì `git push` vào main.

### Chạy test (cần CẢ workspace)

Test của `kb` cần `studio_contracts` + `apps/studio` + DB. Chạy **từ repo cha**:

```bash
cd <repo-cha>                   # về gốc agentcore-studio-kit
uv run pytest packages/kb/tests -q          # test riêng kb
make test-int                                # full suite + DB (docker compose.test)
make lint                                    # ruff + mypy + import-linter (ranh giới import vẫn enforce)
```

---

## 5. Mentor: bump con trỏ ở repo cha (đồng bộ workspace)

Repo cha ghim **đúng 1 commit** của mỗi submodule. Sau khi kỹ sư push code mới, mentor (hoặc bất kỳ
ai có write repo cha) cập nhật con trỏ để workspace "nhìn thấy" bản mới:

```bash
cd <repo-cha>
git submodule update --remote packages/kb    # kéo commit mới nhất của kb về pointer
# hoặc: cd packages/kb && git checkout main && git pull && cd ..

git add packages/kb
git commit -m "chore: bump kb → <sha ngắn>"
git push                                      # push repo cha
```

> ⚠️ **Repo cha cũng có `main` protected.** Nếu harness-guard bật ở máy mentor, bump pointer cũng đi
> **nhánh + PR** như §4 (`git checkout -b chore/bump-kb` → push nhánh → `gh pr create`), không `git
> push` thẳng main. Chỉ bỏ qua khi `protected-branches.yaml` **không** liệt `main` (guard tắt).

> **Không bắt buộc bump mỗi lần.** Gom lại, bump khi muốn chốt một "phiên bản workspace" (ví dụ cuối
> ngày, trước demo). Repo con vẫn tiến hoá độc lập.

---

## 6. Đổi contract (chạm nhiều người) — quy trình cẩn thận

`contracts` là seam chung. Đổi nó = có thể vỡ cả 4 domain. Quy trình:

1. Mở PR ở `agentcore-studio-contracts` mô tả rõ thay đổi (thêm field OPTIONAL = không bump; rename/
   remove/required-add = breaking → bump `SCHEMA_VERSION`). Cần **mentor approval**.
2. Merge contracts. Note lại `sha` mới.
3. Mentor bump con trỏ contracts ở repo cha (`git submodule update --remote packages/contracts` →
   commit → push).
4. Báo 4 domain: mỗi người `cd packages/<mình> && ... ` cập nhật code cho khớp contract mới, rồi push
   repo mình.
5. ⚠️ **Version drift:** trong lúc chuyển tiếp, kb có thể đang dùng contract@vN còn engine ở @vN-1.
   Chạy `make lint` + `make test-int` ở repo cha sau khi mọi người bump để chắc đồng bộ.

---

## 7. Lấy việc mới nhất của đồng đội

```bash
cd <repo-cha>
git pull                                     # cập nhật con trỏ submodule (nếu mentor đã bump)
git submodule update --init --recursive      # ⚠️ ĐỪNG QUÊN — nếu không, bạn thấy code CŨ

# muốn kéo bản HEAD mới nhất của mọi submodule (kể cả chưa bump ở cha):
git submodule update --remote --merge
```

---

## 8. Pitfalls (đọc kỹ — đây là nơi hay vỡ)

| Triệu chứng | Nguyên nhân | Cách tránh/sửa |
|---|---|---|
| Commit trong submodule "biến mất" | Sửa khi submodule ở **detached HEAD** | `git checkout main` **rồi** `git checkout -b <nhánh>` **trước khi** sửa |
| `ModuleNotFoundError: studio_contracts` khi test | Quên init submodule | `git submodule update --init --recursive` rồi `uv sync` |
| Thấy code cũ, tưởng đồng đội chưa làm | Quên `submodule update` sau `git pull` | `git pull && git submodule update --init --recursive` |
| Mentor bump pointer nhưng đồng đội build lỗi | Bump con trỏ tới commit submodule **chưa push** | Luôn `git push` trong submodule **TRƯỚC** khi bump pointer ở cha |
| `uv sync` báo thiếu member | 1 submodule chưa được init (empty dir) | `git submodule update --init <path>` |
| Đổi contract xong 1 domain lỗi type | Version drift giữa các submodule | Sau khi đổi contract, `make lint` + `make test-int` ở cha |
| Không push được vào repo domain của mình | Chưa được cấp quyền collaborator | Mentor chạy `gh api ... collaborators ... -f permission=push` |
| `git push` main bị guard chặn (đòi artifact merge) | `main` là protected branch (harness `protected_ref_guard`) | Đi **nhánh + `gh pr create`**; KHÔNG push thẳng main (§4) |

### Quy tắc vàng
1. **Sửa submodule:** `cd <path>` → `git checkout main && git pull` → `git checkout -b <nhánh>` → sửa → commit → **push nhánh** → **`gh pr create` (BẮT BUỘC)** → mentor/CI merge. **KHÔNG** commit/push thẳng `main` — guard chặn.
2. **Bump ở cha:** chỉ sau khi submodule đã **merge + push**. `git add <path>` → commit → (nhánh + PR nếu cha cũng guard main).
3. **Pull:** `git pull` **luôn đi kèm** `git submodule update --init --recursive`.

---

## 9. CI

Vấn đề cốt lõi: một repo domain (vd kb) **không test độc lập được** — đơn vị test thật là **cả
uv-workspace** (import `contracts`, cần `uv.lock` + `docker/postgres-init` + Postgres). Nên CI được
thiết kế theo **"Phương án B — dựng lại workspace"**, và **DRY hoá** để không phải copy 6 lần.

### 9.1. Kiến trúc (DRY — logic ở 1 chỗ)

```
agentcore-studio-kit (cha)
├─ .github/workflows/reusable-domain-ci.yml   ← LOGIC reconstruct DUY NHẤT (workflow_call)
├─ .github/actions/init-submodules/           ← composite action: init submodule bằng PAT (dùng chung)
└─ .github/workflows/ci.yml                    ← CI workspace của cha (lint/test-matrix/leak/build)

6 repo Python con  →  .github/workflows/ci.yml = STUB ~13 dòng:
    uses: hieubui2409/agentcore-studio-kit/.github/workflows/reusable-domain-ci.yml@main
    with: { domain_path, domain_package }
    secrets: inherit

agentcore-studio-web  →  CI STANDALONE (pnpm install + build). KHÔNG dùng reusable, KHÔNG PAT.
```

- **Sửa quy trình CI của domain** (bước test, DB, token…) → chỉ sửa `reusable-domain-ci.yml` ở repo
  cha; cả 6 repo con ăn theo (`@main`). Không đụng từng repo con.
- Để repo con (private) gọi được reusable workflow của repo cha (private) cùng chủ: mentor đã bật
  `Actions access = user` cho repo cha (`gh api -X PUT repos/hieubui2409/agentcore-studio-kit/actions/permissions/access -f access_level=user`).

### 9.2. Phương án B chạy thế nào (repo con)

Khi push/PR vào 1 repo domain, reusable workflow: ① checkout code PR của repo đó → ② **clone repo
cha private + submodule bằng PAT read-only** → ③ đắp code PR đè lên `domain_path` → ④ `uv sync
--frozen` + bật pgvector + `pytest <domain>/tests`.

**Không lộ token:** PAT chỉ nằm trong Secret `PAT` (GitHub mask khỏi log), chỉ nhét
vào `git config url.insteadOf` (không `echo`), unset ngay sau clone; fine-grained Contents=Read-only;
PR từ **fork** không được cấp secret → suy biến thành `lint-shallow`. Cách set secret: xem §2.

- `apps/web` được **bỏ qua** khi init/clone submodule (`update=none`) vì web không thuộc uv workspace
  → parent CI + reconstruct không cần nó, và PAT cũng **không cần** quyền đọc repo web.

### 9.3. CI repo cha

`.github/workflows/ci.yml`: init 6 submodule Python (trừ `apps/web`) qua composite action → `lint` (ruff/mypy/
import-linter) · `test` (matrix per-package + pgvector) · `leak-test` · `build` (docker). Chạy khi
push repo cha (thường là lúc bump pointer).

- `leak-test` vẫn **continue-on-error** (đỏ-by-design) tới khi fence-DATA land thật. Lưu ý: ở **repo
  con kb**, leak-test nằm trong job **chặn** (trách nhiệm của DE) — khác semantics repo cha.
- `NDA-denylist` pre-commit cài ở **mỗi** repo (chống file mentor/rubric/answer-key lọt vào bất kỳ
  repo nào học viên có quyền).

### 9.4. Đổi PAT (rotate)

Khi PAT hết hạn / cần xoay: tạo PAT mới (§2), rồi chạy lại vòng `gh secret set` cho 7 repo. Web không
đụng tới.

---

## 10. Nếu thấy multi-repo quá nặng

Cái giá của mô hình này: mỗi thay đổi chạm nhiều repo = nhiều lần commit + bump pointer + nhớ
`--recursive`. Nếu ưu tiên là **tốc độ dạy nội dung** hơn **ranh giới quyền cứng**, cân nhắc quay lại
monorepo + tin-nhau/review (rẻ hơn nhiều thao tác). Đổi lại monorepo không chặn cứng được ai trên
GitHub-private-free. Đây là trade-off có chủ đích — chọn theo mục tiêu khoá học.
