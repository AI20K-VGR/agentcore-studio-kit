---
id: 260812-1133-d18-d20-aie1-engine-daily-prs
title: "D18-D20 AIE-1 engine: 3 phase rieng, 3 PR rieng"
status: in_progress
mode: hard
tdd: true
branch: main
created: 2026-08-12
author: user:tranbadat26072004@gmail.com
decisions: []
phases:
  - phases/phase-1-d18-llm-step-fixtures.md
  - phases/phase-2-d19-tokens-idempotent-retrieval-failure-modes.md
  - phases/phase-3-d20-dag-real-spine-trade-off.md
harness_version: 5.3.0
harness_kit_digest: 251ed307796039124b44d71759b3f62d8bb9135c4bf3053156e38798587a50a8
harness_schema_version: 1.0
---

# Plan: D18-D20 AIE-1 engine: 3 phase rieng, 3 PR rieng

## Tổng quan

AIE-1 (Trần Bá Đạt) làm 3 issue liên tiếp trong `packages/engine` (submodule
`agentcore-studio-engine`, repo WRITE duy nhất của lane này): kit#116 (D18), kit#121 (D19),
kit#126 (D20). **Ràng buộc cứng của user: mỗi ngày một PR riêng vào `agentcore-studio-engine`
— không gộp code/PR của ngày khác.** 3 phase dưới đây ánh xạ 1-1 vào 3 PR, mỗi phase tự chứa
(self-contained): tự tạo branch riêng từ `origin/main` sau khi fetch (không phải `main` local —
xem lý do ở §Quyết định đã khoá), tự mở PR riêng, không phase nào rebase lên nhánh của phase
khác. **Mỗi phase chạy bằng 1 lượt `/hs:cook <plan> --phase N` RIÊNG, và PR của ngày trước PHẢI
merge xong trước khi chạy lượt cook cho ngày sau** (branch ngày sau cắt từ `origin/main`, nếu
chưa merge thì `origin/main` chưa có commit ngày trước — phase sau sẽ thiếu nền). 1 lệnh cook
không kèm `--phase` sẽ chạy gộp cả 3 ngày thành 1 PR, đúng thứ user cấm — xem chi tiết + lệnh
chính xác ở §Quyết định đã khoá.

Bối cảnh nền đã probe thật trong phiên trước khi lập plan này (không phải suy diễn):

- Engine hiện ở D17 (`engine#22` merged) — 6/6 node-executor có thân thật từ D14 (`engine#18`),
  `EmbeddingService` seam + chunking×embedding grid harness có số thật từ D14
  (`packages/engine/docs/design-notes/aie1-day14-grid-harness.md`), KB thật (`PgKbSearch`) đã flip live D17
  (`kb#19`). `apps/studio` (composition root) có fix A1-8 (tenant_id bind trong
  `PgTraceWriter`) đã merge qua `agentcore-studio-app#4` — không còn chặn trace-write.
- `docs/system-architecture.md §6` + `measure_chunk_embed.py:332` (class `_BowWideService`,
  câu R-6 ở `:334-335`): impl gateway/model thật
  **chính thức KHÔNG ship trong kit này** (quyết định R-6) — "ES" trong cả 2 issue #116/#126 là
  `EmbeddingService` seam nội bộ (gateway-stub), không phải một phụ thuộc bên ngoài đang treo.
- `scripts/run_golden_batch.py` (D16) đã có harness xanh chạy 30 golden case thật qua
  `interpreter.run()` — nhưng dùng DAG **3 node** (`kb-retrieve → llm-step → end`,
  `run_golden_batch.py:185-189`) và một double tự viết `_GoldenAwareLLM`
  (`run_golden_batch.py:106`), KHÔNG dùng `FixtureLLM`/`tests/fixtures/llm_step/*.json`. Tương
  tự `apps/studio/scripts/e2e_smoke_eval.py` dùng double riêng `ExtractiveFakeLLM`. `tests/
  fixtures/llm_step/` hiện chỉ có **1** file (`smoke-01.json`) — dùng cho contract test của
  `FixtureLLM` (`test_fixture_missing_fails_loud.py`, `test_llm_step_prompt_build.py`), không
  phải nguồn dữ liệu cho golden-batch.
- `LlmStepExecutor.execute()` (class `executors.py:185`, method `:196`) hard-code
  `Tokens(prompt=0, completion=0)` ở dòng `:290` — **chưa có token accounting thật**, không có
  test nào tên "idempotent"/"replay" gắn với tokens (grep rỗng) — D19 là việc mới thật, không
  phải hardening việc đã có. Test hiện có `test_executors_behavior.py:114` đang **khoá cứng**
  `result["tokens"] == Tokens(prompt=0, completion=0)` — phase 2 sẽ cố ý làm test này đỏ rồi
  sửa nó cùng lúc với implement (nằm trong Files phase 2, không phải side-effect bỏ sót).
- Golden-batch DAG hiện chỉ chạm **3/6 NodeType** (`kb-retrieve`/`llm-step`/`end`) —
  `condition`/`tool-call`/`hitl-pause` chỉ có test đơn lẻ (`test_executors_behavior.py`,
  `test_condition_dag_e2e.py`), chưa từng chạy chung 1 DAG thật với 3 node kia. D20 "6
  node-type executor chạy DAG thật" là gap thật, không phải diễn giải lại việc cũ.

## Quyết định đã khoá

- **1 PR/ngày, không gộp** (user, turn này). **Cook KHÔNG tự chặn việc này** — đã xác nhận thật
  (`autonomy_policy.py --show` → `pauses.phase=false`; cook SKILL.md: bước
  branch/push/PR-per-phase không nằm trong per-phase loop, `@git-manager` chỉ chạy 1 lần SAU
  phase cuối) rằng một lệnh `/hs:cook <plan.md>` chạy thẳng 3 phase rồi tạo **1 PR gộp cả 3
  ngày** — đúng thứ user cấm. **Bắt buộc chạy cook 3 LƯỢT RIÊNG, mỗi lượt đúng 1 ngày, PR merge
  xong mới chạy lượt kế:**
  ```
  /hs:cook plans/260812-1133-d18-d20-aie1-engine-daily-prs/plan.md --phase 1 --tdd
  # ... review, merge PR ngày 18, rồi mới ...
  /hs:cook plans/260812-1133-d18-d20-aie1-engine-daily-prs/plan.md --phase 2 --tdd
  # ... review, merge PR ngày 19, rồi mới ...
  /hs:cook plans/260812-1133-d18-d20-aie1-engine-daily-prs/plan.md --phase 3 --tdd
  ```
  KHÔNG chạy `/hs:cook <plan.md>` không kèm `--phase` cho plan này.
- Branch mỗi phase tạo từ **`origin/main` sau khi fetch**, không phải `main` local — đã đo
  thật: `packages/engine` local đang **detached HEAD** ở `main` cũ (`9484968`), lệch 2 commit
  so với `origin/main` (`62773ba`, gồm fix mypy `types-PyYAML` D17). Cắt nhánh từ `main` cũ sẽ
  làm CI "Types" đỏ ngay PR đầu (mypy `warn_unused_ignores` bắt `unused-ignore` thừa). Lệnh
  đúng mỗi phase:
  ```
  git -C packages/engine fetch origin
  git -C packages/engine switch -c aie-1/dayNN-<slug> origin/main
  ```
  `.claude/` hiện untracked trong `packages/engine` (dấu vết detached HEAD trước đó) — thêm vào
  `packages/engine/.gitignore` ở phase 1 trước khi commit đầu tiên, để `git add -A` không lỡ
  đẩy nó vào PR.
- TDD test-first mỗi phase (user, turn này) — RED trước khi sửa `src/`, GREEN sau, regression
  full suite trước khi mở PR:
  ```
  uv run --package agentcore-studio-engine pytest packages/engine/tests -q
  uv run ruff check packages/engine
  uv run ruff format --check packages/engine
  uv run mypy packages/engine
  uv run lint-imports
  ```
  5 lệnh, không phải 3 — đối chiếu CI thật (`reusable-domain-ci.yml`, job `lint`) có đủ
  `ruff check` + `ruff format --check` + `lint-imports` + `mypy`, thiếu bất kỳ lệnh nào là gate
  yếu hơn CI thật. **`ruff check`/`ruff format --check` LÀ BẮT BUỘC trước push** — bài học từ PR
  `agentcore-studio-app#4` cùng phiên này: CI fail vì 4 dòng E501 chỉ vì chỉ chạy `pytest` mà
  quên `ruff`.
- Không tự build/ship gateway LLM hay gateway embedding thật trong 3 phase này — ngoài scope
  chính thức của kit (R-6). "ES gateway-flag" (D18) và "chạy DAG thật qua ES" (D20) đều nói về
  seam `EmbeddingService` nội bộ, không phải một tích hợp gateway mới.
- Không đụng `apps/studio`, `packages/kb`, `packages/workbench`, `packages/evalhub` trong 3 PR
  này — lane AIE-1 chỉ ghi `packages/engine`; A1-8 (apps/studio) đã đóng ở PR riêng từ trước.

## Ràng buộc (constraint-scan)

- `docs/code-standards.md §2`: ruff `line-length = 120`, `select = ["E", "F", "W", "I", "UP",
  "B", "SIM"]` — chạy `uv run ruff check packages/engine`.
- `docs/code-standards.md §3`: mypy `strict = true` toàn `packages` — `uv run mypy packages/
  engine`. **Sửa lại so với `code-standards.md`** (tài liệu đó ghi `studio_engine` không có
  `py.typed` — kiểm sống lại thấy đã SAI, marker đã thêm từ commit `f7e29eb`
  ("add py.typed marker (PEP 561, sync with sibling packages)"); dùng trạng thái thật này, không
  copy nguyên văn tài liệu.
- `docs/code-standards.md §4.1`: 2 loại `xfail` không được lẫn — spec-contract test (`pytest.
  raises(NotImplementedError)`, hợp lệ cho seam CHƯA cài) vs behavioral-fence test (KHÔNG BAO
  GIỜ thoả mãn chỉ bằng raise NotImplementedError). Không seam nào trong 3 phase này còn ở dạng
  spec-stub (6/6 executor đã có thân thật từ D14) nên không tạo `xfail` mới loại 1; nếu phase
  nào viết test tính chất bảo mật/nghiệp vụ thật (không có trong 3 issue này, nhưng nếu chạm
  paths liên quan tenant/fence) phải theo mẫu "có răng" như `test_leak.py`.
- `docs/code-standards.md §8`: 6 `NodeType` đóng — cấm thêm loại thứ 7, khoá bởi
  `test_node_type_closed.py`/`test_registry_has_exactly_six`. D20 "6 node-type" nghĩa là dùng
  **đủ** 6 loại đã có, không phải thêm loại mới.
- `docs/code-standards.md §9`: conventional commits, mỗi phase 1 commit-range riêng.
- `harness/data/stage-policy.yaml`: stage `pr`/`ship`/`deploy` đòi `requires: [verification,
  review-decision, plan-approval]` — mỗi phase phải để lại verification/review-decision thật
  (không phải tự-khai) trước khi mở PR qua `hs:ship`.
- Không có entry `ownership.yaml`/policy riêng chặn `packages/engine` ngoài ranh giới repo-per-
  submodule đã biết (`.gitmodules`, GITFLOWS.md) — AIE-1 có write trên
  `agentcore-studio-engine`, read-only trên các submodule khác.

## Phases

| # | Ngày | Issue | Theme | Phụ thuộc | Cỡ |
|---|---|---|---|---|---|
| 1 | D18 | kit#116 | `llm-step` output ổn định cho judge + ES gateway-flag | Không phụ thuộc phase khác | S–M |
| 2 | D19 | kit#121 | Token accounting thật + idempotent-qua-replay + failure-mode retrieval | Độc lập kỹ thuật với phase 1 (không sửa cùng file); chạy sau D18 theo lịch, không theo code | S–M |
| 3 | D20 | kit#126 | DAG thật đủ 6 node-type (phía engine) + tái lập trade-off table | Dùng lại field token phase 2 thêm vào `Tokens`/executor nếu phase 2 mở rộng — xác nhận tại đầu phase 3 trước khi viết code | M |

**Status: Phase 1 (D18) implementation + review + test done, CI xanh** — 2026-08-12. PR#23
(`aie-1/day18-llm-step-stability`, commits `52d8111`+`8528883`) mở, `gh pr checks 23` exit 0
(mọi check pass/skip, không pending). Chờ review + merge từ AIE-2 trước khi chạy `/hs:cook <plan>
--phase 2`.

Không có phase nào ghi đè file `src/` của phase khác trong cùng lượt chạy — nếu phase 2 đổi
shape `Tokens`/`TraceEvent` theo hướng cần sang `packages/contracts` (ngoài quyền ghi AIE-1),
phase đó phải dừng và note lại thay vì tự ý mở PR chéo-repo (xem Risk).

## Out of scope

- Build/ship gateway LLM hoặc gateway `EmbeddingService` thật (R-6, ngoài scope kit).
- Sửa `obs.trace_events`/RLS production, `apps/studio` nói chung (đã đóng ở PR riêng —
  `agentcore-studio-app#4`).
- Sửa `graph_lint`/canvas/publish (`packages/workbench`, SWE lane) hay `kb.search` thật/ingest
  (`packages/kb`, DE lane) hay eval harness/judge (`packages/evalhub`, AIE-2 lane) — AIE-1 chỉ
  tiêu thụ các seam đó qua `studio_contracts`, không tự sửa.
- Đổi field/shape trong `packages/contracts` (cần mentor-approval, ngoài quyền write của AIE-1)
  — nếu phase 2/3 phát hiện cần đổi contract thật (không chỉ thêm optional field nội bộ engine),
  dừng lại ghi note, không tự mở PR vào `packages/contracts`.
- Comment/coordination với DE/SWE/AIE-2 (#115/#117/#118/#120/#122/#123/#125/#127/#128) — nằm
  ngoài phạm vi 3 PR kỹ thuật này, xử lý riêng nếu cần (đã làm ở turn trước cho kit#84).

## Acceptance (toàn plan)

- [ ] Mỗi phase red→green TDD; `uv run --package agentcore-studio-engine pytest packages/
      engine/tests` xanh sau mỗi phase.
- [ ] `uv run ruff check packages/engine` + `uv run mypy packages/engine` sạch trước mỗi PR.
- [ ] 3 PR riêng biệt mở vào `agentcore-studio-engine`, mỗi PR chỉ chứa code+test của đúng 1
      ngày (diff review được: `git diff <base>...<head> --stat` chỉ liệt kê file thuộc đúng
      phase đó).
- [ ] Không PR nào bump gitlink `packages/engine` trong `agentcore-studio-kit` thay — bump
      gitlink là hành động riêng, sau khi mỗi PR merge (không nằm trong 3 phase, xem note cuối).

## Rollback

Mỗi phase = branch riêng + PR riêng + commit-range riêng trong `agentcore-studio-engine`. Revert
1 phase = `git revert <merge-commit-của-PR-đó>` trên `main` của `agentcore-studio-engine`, không
đụng 2 PR còn lại (file-ownership giữa 3 phase không trùng — xem bảng Files từng phase file).
Nếu phase 3 phụ thuộc field phase 2 thêm vào `Tokens` nội bộ, revert phase 2 sau khi phase 3 đã
merge sẽ cần revert luôn phần phase 3 dùng field đó — ghi rõ trong phase 3 nếu xảy ra.

## Risks

- **[M] `_GoldenAwareLLM`/`ExtractiveFakeLLM` là 2 double tự viết cho 2 harness khác nhau,
  không phải `FixtureLLM`** — chưa xác nhận được đích xác AIE-2's LLM-judge (kit#118, D18, đang
  làm song song) sẽ gọi qua đường nào để chấm. Phase 1 PHẢI probe (đọc PR/commit mới của
  `agentcore-studio-evalhub` nếu đã có tại thời điểm cook) trước khi quyết "ổn định (fixtures)"
  nghĩa là mở rộng `FixtureLLM`/`tests/fixtures/llm_step/` hay hardening 1 trong 2 double có
  sẵn. Không đoán trước — xem Phase 1 §Probe.
- **[L] Phase 3 dùng lại field token phase 2 thêm** — nếu phase 2 mở field mới trong
  `Tokens`/`TraceEvent.outputs` cho mục "nguồn cost", phase 3 cần field đó để bảng trade-off
  đọc cost thật. Rủi ro thấp vì cả 2 đều trong quyền ghi AIE-1 (`packages/engine`), không chạm
  `packages/contracts`.
- **[L] `run_golden_batch.py` cần chạy từ kit-root** (`uv run` resolve `studio_kb` qua
  workspace) — không chạy standalone trong repo con `agentcore-studio-engine`. Mọi lệnh
  test/verify trong 3 phase phải chạy từ `agentcore-studio-kit/`, không từ
  `packages/engine/` riêng.
- **[L] `ruff check` bị bỏ sót trước push** — đã xảy ra thật ở PR liên quan trong phiên này
  (`agentcore-studio-app#4`). Regression Gate của mỗi phase liệt kê `ruff check` tường minh,
  không ẩn trong "chạy test".

## Note — gitlink bump (ngoài 3 phase)

Sau khi mỗi PR merge vào `agentcore-studio-engine`, con trỏ submodule `packages/engine` trong
`agentcore-studio-kit` sẽ lệch (`git submodule status` báo `+<sha>`) cho tới khi có 1 PR riêng
bump gitlink trong `agentcore-studio-kit` — đúng pattern `chore(gitlink): bump ...` đã thấy
trong lịch sử team. Không nằm trong 3 phase (mỗi phase chỉ chạm `agentcore-studio-engine`), ghi
lại ở đây để không quên — làm sau khi 3 PR đều merge, hoặc theo từng PR nếu team muốn bump ngay.
