---
phase: 3
title: "D20 Dag Real Spine Trade Off"
status: pending
plan: 260812-1133-d18-d20-aie1-engine-daily-prs
created: 2026-08-12
harness_version: 5.3.0
harness_kit_digest: 251ed307796039124b44d71759b3f62d8bb9135c4bf3053156e38798587a50a8
harness_schema_version: 1.0
---

# Phase 3 — D20 (GATE-2 phần AIE-1): DAG 6-node phía engine + tái xác nhận trade-off table

Issue: kit#126, con của kit#129 (GATE-2 cả team: *"spine 4 mảng chạy THẬT end-to-end lần đầu"*).
Việc AIE-1: *"6 node-type executor chạy DAG thật qua ES + bảng chunking×embedding trade-off có
số; đã ghép vào spine."*

**Tên phase + deliverable đã hạ đúng mức sau red-team** — bản đầu tự nhận "đã ghép vào spine",
red-team chỉ ra Success cũ không chứng minh nổi claim đó (2/6 node-type là no-op ngữ nghĩa trong
walk hôm nay, và không có cách verify chéo với canvas SWE trong quyền ghi AIE-1). Phase này CHỈ
làm và chứng minh phần thuộc quyền ghi AIE-1: engine chạy được đủ 6 node-type trong 1 DAG thật,
sẵn sàng để ghép — không tự nhận đã ghép xong với UI/canvas thật của SWE.

## Setup bắt buộc trước khi làm bất kỳ việc gì

```
git -C packages/engine fetch origin
git -C packages/engine switch -c aie-1/day20-dag-6node-spine origin/main
```
Chạy SAU KHI PR phase 2 đã merge — xác nhận `git -C packages/engine log --oneline -3
origin/main` có commit phase 2 trước khi bắt đầu.

## Overview

Xác nhận thật (đã probe khi lập plan này): `scripts/run_golden_batch.py` (D16) là harness
DAG-thật gần nhất hiện có, nhưng DAG của nó chỉ 3 node (`kb-retrieve→llm-step→end`,
`run_golden_batch.py:182-194`) — `condition`/`tool-call`/`hitl-pause` CHƯA từng chạy chung 1 walk
thật với 3 node kia (chỉ có test đơn lẻ: `test_executors_behavior.py`,
`test_condition_dag_e2e.py`).

**Giới hạn thật của `interpreter.run()` hôm nay, phải biết trước khi viết DAG mới** (red-team
xác nhận bằng code, không phải suy đoán):
- `condition`'s verdict **KHÔNG route walk thật** — `interpreter.py:103-115`
  (`_build_next_map`) là single-successor last-write-wins; `condition` chỉ evaluate và trả
  `{"when", "result", "reason"}`, không rẽ nhánh walk (đúng như docstring `ConditionExecutor`
  tự ghi: *"interpreter.py (phase 2 của [plan D12]) không branch theo kết quả này"* — vẫn đúng
  hôm nay).
- `hitl-pause` **KHÔNG thật sự dừng gì** — `executors.py:496-517`: trả output pause-SHAPED
  (`{"paused": True, "status": "pending_approval"}`) nhưng interpreter không biết gì về nó, walk
  đi tiếp bình thường.

⇒ Một DAG thẳng 6 node chạy hết KHÔNG chứng minh 2 node-type đó "hoạt động" theo nghĩa hành vi
đầy đủ — chỉ chứng minh **executor của cả 6 loại chạy được, output đúng shape, không crash walk**.
Đây là điều issue #126 đòi ("6 node-type executor chạy DAG thật") — không đòi routing/pause thật
(đó là INV-2/interpreter phase khác, ngoài scope D20 theo chính docstring hiện có). Ghi rõ ranh
giới này trong design-note + PR, không để đọc nhầm thành "cả 6 node-type hoạt động đầy đủ".

Bảng chunking×embedding trade-off: **`measure_chunk_embed.py` không chạm Postgres/`PgKbSearch`**
(tự ghi rõ ở `:40`: *"Không mạng, không model, không Postgres"*; import duy nhất từ kb là
`doc_factory.chunk_document`/`embeddings.derive_vector`, không phải `static_search`/DSN nào).
Chạy lại `--grid` là **kiểm tái lập** (cùng corpus + cùng code ⇒ cùng số), KHÔNG phải một phép đo
mới trên KB thật đã flip D17 — 2 thứ khác nhau, bản đầu của phase này nhầm lẫn 2 thứ đó.

## Probe (chạy TRƯỚC khi viết code)

1. Xác nhận corpus/chunker/embedder có đổi từ lúc đo D14 chưa — lệnh cụ thể (siết hơn bản đầu,
   phủ cả code không chỉ data):
   ```
   git -C packages/kb log --oneline 51df3a4..HEAD -- docs/callisto src/studio_kb/doc_factory.py src/studio_kb/embeddings.py golden/smoke-10.yaml
   ```
   Nếu rỗng → bảng D14 vẫn hợp lệ đúng nghĩa "chưa đổi input", phase này chỉ cần re-run `--grid`
   1 lần xác nhận tái lập, ghi rõ đây KHÔNG phải xác nhận qua `PgKbSearch` thật.
2. Xác nhận state thật của `Tokens`/`LlmStepExecutor` sau phase 1+2 (đọc lại file, không giả
   định plan cũ còn khớp) trước khi viết DAG 6-node mới.
3. Đọc `packages/workbench/src/studio_workbench/validator.py` (`graph_lint`) NẾU có thời gian —
   chỉ để hiểu shape recipe hợp lệ SWE mong đợi, KHÔNG import nó (`.importlinter` cấm
   `studio_engine → studio_workbench`) — DAG script của phase này tự dựng `Recipe` object trực
   tiếp qua `studio_contracts`, không gọi `graph_lint`.

## Files

- **Create**: `packages/engine/scripts/run_spine_dag_6node.py` — 1 DAG thật đủ 6 `NodeType`:
  `kb-retrieve → llm-step → condition → tool-call → hitl-pause → end` (chuỗi thẳng, không rẽ
  nhánh thật — theo đúng giới hạn đã nêu ở Overview). `tool-call` node cần
  `ToolCallExecutor(dispatcher=...)` với `tool` nằm trong whitelist của dispatcher truyền vào
  (`executors.py:472-493` raise nếu không) — dựng 1 dispatcher stub tối thiểu trong script, ghi
  rõ đây là stub demo, không phải `ToolDispatch` thật.
- **Modify**: `packages/engine/docs/design-notes/aie1-day14-grid-harness.md` — thêm 1 mục nối
  tiếp: ngày chạy lại `--grid`, số có đổi hay không, VÀ ghi rõ ràng buộc "đây là kiểm tái lập
  trên harness không-Postgres, không phải phép đo qua `PgKbSearch` đã flip D17".
- **Create**: `packages/engine/tests/test_dag_6node_spine.py` — khoá hành vi walk đủ 6 node.

## TDD

- **Tests-before (RED)**:
  1. Test DAG 6-node chạy thật: dựng 1 `Recipe` hợp lệ đủ 6 node trực tiếp qua
     `studio_contracts` (không qua `graph_lint`), gọi `interpreter.run()` thật (không mock
     executor) → assert `RunResult.events` có đủ 6 `node_type` khác nhau xuất hiện, đúng thứ tự
     walk theo `edges`. RED trước khi script/DAG này tồn tại.
  2. Test trade-off tái lập: chạy lại `measure_chunk_embed.py --grid` → so số với bảng D14 đã
     ghi, assert khớp (hoặc ghi rõ lệch + lý do nếu Probe bước 1 phát hiện corpus/code đổi).
- **Implement** → xanh. KHÔNG thêm `NodeType` thứ 7 — `test_node_type_closed.py`/
  `test_registry_has_exactly_six` (`test_node_type_closed.py:16`) PHẢI vẫn xanh sau thay đổi;
  nếu đỏ, dừng lại xem lại thiết kế, không sửa 2 test đó để chúng xanh trở lại.
- **Regression** (chạy từ kit-root):
  ```
  uv run --package agentcore-studio-engine pytest packages/engine/tests -q
  uv run python packages/engine/scripts/run_golden_batch.py     # D16 harness vẫn xanh
  uv run python packages/engine/scripts/measure_chunk_embed.py --grid
  uv run ruff check packages/engine
  uv run ruff format --check packages/engine
  uv run mypy packages/engine
  uv run lint-imports
  ```

## PR (bắt buộc — không gộp với phase 1/2)

1. Đã tạo branch ở bước Setup (`aie-1/day20-dag-6node-spine`, từ `origin/main` SAU KHI phase 2
   merge).
2. Commit conventional, dẫn `kit#126` + `kit#129` (GATE-2 cha).
3. `gh pr create --repo AI20K-VGR/agentcore-studio-engine --base main --head
   aie-1/day20-dag-6node-spine` — mô tả PR nêu rõ, KHÔNG phóng đại: DAG 6-node chạy thật phía
   engine (evidence: `RunResult.events` thật), 2/6 node-type (condition/hitl-pause) là
   evaluate-only/shape-only chưa route/pause thật (giới hạn đã biết, không phải bug phase này
   gây ra), bảng trade-off là **tái lập**, không phải đo mới qua `PgKbSearch`. Đây là bằng chứng
   phía engine sẵn sàng ghép — verify chéo với canvas/UI thật của SWE KHÔNG nằm trong PR này.
4. Xác nhận `gh pr checks <N> --repo AI20K-VGR/agentcore-studio-engine` xanh THẬT.
5. Reviewer: SWE (Quang Minh) — họ own canvas/`graph_lint` mà DAG 6-node cuối cùng cần khớp
   shape để ghép vào spine thật; PR description nên xin họ xác nhận shape `Recipe` script này
   dựng có tương thích validator của họ không (không phải merge-blocker của PR này, nhưng đáng
   hỏi ngay khi có review).

## Success

- [ ] 1 DAG thật, chạy qua `interpreter.run()` không mock, đi qua đủ 6/6 `NodeType`, có
      `RunResult`/`TraceEvent` thật làm bằng chứng.
- [ ] PR description nói rõ giới hạn 2/6 node-type (condition không route, hitl-pause không
      dừng thật) — không claim ngầm "cả 6 hoạt động đầy đủ".
- [ ] Bảng chunking×embedding **tái lập được** trên trạng thái corpus/code hôm nay (khớp D14
      hoặc lệch có ghi lý do) — KHÔNG claim đây là phép đo qua KB thật/`PgKbSearch`.
- [ ] `test_node_type_closed`/`test_registry_has_exactly_six` vẫn xanh.
- [ ] `run_golden_batch.py` (D16) không bị phá bởi DAG mới.
- [ ] 7 lệnh regression sạch. PR riêng mở, CI xanh xác nhận qua `gh pr checks`.

## Risks

- **[M] "Ghép vào spine" (claim của issue cha kit#129) cần SWE's canvas/graph_lint xác nhận
  chéo** — phase này KHÔNG tự nhận đã ghép; chỉ chứng minh phần AIE-1 sẵn sàng. Nếu SWE/team cần
  bằng chứng "ghép thật" mạnh hơn (vd chạy DAG này từ 1 recipe JSON canvas SWE thật sự xuất ra),
  đó là việc phối hợp riêng ngoài PR này — ghi thành theo-dõi (follow-up), không phải mở rộng
  scope giữa chừng.
- **[L]** Nếu Probe (bước 1) phát hiện corpus/code đã đổi từ D14, bảng trade-off cũ không còn
  hợp lệ để so — phải đo lại thật (không copy số D14), tốn thêm thời gian trong ngày.
- **[L]** Thứ tự 6 node trong DAG demo là 1 lựa chọn hợp lý (`umbrella-contract.md:69` chỉ cố
  định 4 node lõi, `hitl-pause`+`end` là node điều khiển không ràng buộc vị trí) nhưng chưa xác
  nhận đây là thứ tự "chuẩn" đội đang kỳ vọng cho demo — nếu SWE/canvas có thứ tự khác đã thống
  nhất trước, dùng thứ tự đó thay vì tự chọn.
