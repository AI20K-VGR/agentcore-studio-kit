---
id: studio.decision-log.shared
type: decision-log
owner: cả nhóm (SWE/DE/AIE-1/AIE-2)
scope: agentcore-studio (toàn bộ 4 quadrant)
started: 2026-08-03
canonical_location: agentcore-studio-kit/docs/decisions/decision-log.md
---

# Decision-log chung — AgentCore Studio

> **Đây là bản chung, canonical, đặt tại `agentcore-studio-kit` theo ADR-D11-01** (xem
> [issue kit#84](https://github.com/AI20K-VGR/agentcore-studio-kit/issues/84)). Các bản "local"
> từng repo (vd `agentcore-studio-kb/docs/decisions/decision-log.md` của DE) giữ nguyên làm chi
> tiết kỹ thuật riêng của quadrant đó — chỉ cần để lại 1 dòng trỏ sang file này làm bản tổng.
>
> Nguồn luật freeze: umbrella-contract §3 (`:92-93`) · D-12 · INV-5 · GITFLOWS §5. Đổi contract sau
> freeze = mini-RFC + 4/4 chữ ký + decision-log.

## D11 · 2026-08-03 · Contract-freeze workshop (issue #84)

| # | Quyết định | Lý do | PR / bằng chứng | Trạng thái |
|---|---|---|---|---|
| **ADR-D11-01** | Q-1 (nơi đóng dấu freeze) + Q-2 (decision-log chung + hình thức chữ ký) — xem chi tiết trong ADR đăng ở [kit#84](https://github.com/AI20K-VGR/agentcore-studio-kit/issues/84#issuecomment-5163714300) | Mentor giao quyền tự quyết từ S2 (không phê duyệt kiến trúc/quy trình nữa) | issue kit#84 | 🟡 PROPOSED — chờ phản hồi trong ngày 03/08 |
| **DL-11.1** | `CaseResult.judge: Judge` → `Judge \| None = None` | Case exact-match/refusal (toàn bộ case hiện có) không có judge chạy; bắt buộc field này chặn `EvalHarness.run()` viết tiếp; điền hằng số giả bị `judge.py` tự cấm (làm sai chỉ số agreement-check) | [contracts#1](https://github.com/AI20K-VGR/agentcore-studio-contracts/pull/1) | 🟡 chờ review (AIE-2 bút, mentor CODEOWNERS) |
| **DL-11.2** | `TraceEvent.citations` — sửa comment sai (`# from kb-retrieve` → chỉ `llm-step` set) | Comment không khớp hành vi thật của `agentcore-studio-engine/interpreter.py`; nêu độc lập ở cả `kb/trace-event.v0.md` §7 và `evalhub/scorecard-v0.md` §2.7.2 | [contracts#2](https://github.com/AI20K-VGR/agentcore-studio-contracts/pull/2) | 🟡 chờ review (DE bút, AIE-1 xác nhận hành vi) |
| **DL-11.3** | `graph_lint()` — implement thân hàm thật, 4 luật (node-type ∈ 6 đóng, edge-destination resolvable, no cycle, tool ∈ whitelist); `recipe.v0.md` freeze-ready | Trước là spec-stub `NotImplementedError`; test đã sẵn từ trước chờ implement | [workbench#12](https://github.com/AI20K-VGR/agentcore-studio-workbench/pull/12) | 🟡 chờ review |
| **DL-11.4** | Q-4 (recipe.dag's node_type = đúng 6 `NodeType`, DE hỏi ở kb#10) — đóng | `recipe.py` và `trace.py` dùng chung `studio_contracts.nodes.NodeType`; Pydantic chặn ở tầng kiểu, không phụ thuộc `graph_lint()` | [kb#10 comment](https://github.com/AI20K-VGR/agentcore-studio-kb/pull/10#issuecomment-5162808694) | ✅ đóng |

## Câu hỏi còn mở (không đóng được trong 1 lane — cần cả nhóm hoặc người cụ thể)

| # | Hỏi ai | Nội dung | Trạng thái |
|---|---|---|---|
| Q-3 | AIE-1 | cost-source + xác nhận carrier `citations` + stub `kb.search` (DE hỏi ở kb#10) | 🔴 chờ AIE-1 |
| Q-5 | AIE-2 | field nào eval cần đọc từ trace + `expected_citation` khớp `chunk_id` (DE hỏi ở kb#10) | 🔴 chờ AIE-2 |
| Q2 (scorecard) | AIE-1+DE+AIE-2 | `citation_accuracy=1.0` hard-code cho case từ-chối, làm sai lệch aggregate (`harness.py:172`) | 🔴 chưa ai sửa |
| Q-Publish | AIE-2 | `publish()` cần `Scorecard` thật (không phải `SmokeResult`) từ `EvalHarness.run()` — chưa xong | 🔴 chờ AIE-2 |

*Cập nhật file này khi có quyết định mới hoặc câu hỏi mới phát sinh — mỗi dòng nên có PR/issue link làm bằng chứng, không ghi quyết định suông không kèm nguồn.*
