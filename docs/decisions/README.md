---
id: studio.decision-log.index
type: decision-log-index
owner: cả nhóm (SWE/DE/AIE-1/AIE-2)
scope: agentcore-studio (toàn bộ 4 quadrant)
started: 2026-08-03
canonical_location: agentcore-studio-kit/docs/decisions/
---

# Decision-log chung — index theo hợp đồng

> Đặt tại `agentcore-studio-kit` theo đề xuất Q-2a, **ADR-D11-01**
> ([issue #84](https://github.com/AI20K-VGR/agentcore-studio-kit/issues/84#issuecomment-5163714300)).
> Tách **1 file / 1 hợp đồng** (không tách theo người) — vì 1 quyết định về hợp đồng ràng buộc cả
> 4 người (cần đủ 4/4 chữ ký, INV-5), không phải quyết định riêng của 1 người.
>
> Bản "local" từng repo (vd decision-log của DE trong `agentcore-studio-kb`) giữ nguyên làm chi
> tiết kỹ thuật; các file dưới đây là bản tổng, cross-repo.

| Hợp đồng | Bút | File | Trạng thái |
|---|---|---|---|
| recipe | SWE | [`recipe.md`](./recipe.md) | ✅ đã tạo (SWE tự viết) |
| trace-event | DE | *chưa tạo* | 🟡 nội dung thật đã có, đang ở PR [`agentcore-studio-kb#10`](https://github.com/AI20K-VGR/agentcore-studio-kb/pull/10) (`docs/decisions/decision-log.md`, nhánh `day11/de-contract-freeze` — chưa merge `main` nên chưa có link `blob/main` cố định) |
| kb.search | DE | *chưa tạo* | 🟡 cùng nguồn PR kb#10 như trên |
| scorecard | AIE-2 | *chưa tạo* | 🔴 chờ AIE-2 tự viết — hiện AIE-2 chưa có decision-log riêng nào |

**Mỗi người tự viết file hợp đồng mình giữ bút** — không ai viết hộ người khác (đúng nguyên tắc "mỗi quadrant 1 owner", umbrella-contract §2). File này (README) chỉ là khung/index, không thay thế việc từng người tự điền.

## Quyết định xuyên nhiều lane (không thuộc riêng 1 trong 4 hợp đồng trên)

| # | Nội dung | Nguồn | Cần ký |
|---|---|---|---|
| **mini-RFC tenant+RLS** | Chuẩn hoá `tenant_id UUID` + bật RLS cho 5/11 bảng đang hở INV-1 (gồm `wb.recipes`/`wb.recipe_versions`) | DE, trong PR [kb#10](https://github.com/AI20K-VGR/agentcore-studio-kb/pull/10) (`docs/mini-rfc-tenant-schema-unify.md`) | DE ✅ · SWE ⬜ · AIE-1 ⬜ · AIE-2 ⬜ · mentor ⬜ |

Phần "cột workbench `tenant`→`tenant_id`" (mục A trong RFC) đã được SWE tự sửa xong, không cần ký — xem [workbench#13](https://github.com/AI20K-VGR/agentcore-studio-workbench/pull/13). Phần **bật RLS thật** (mục B/B2/C) đổi hành vi runtime, cần đủ chữ ký mới thực thi.

Nguồn luật freeze: umbrella-contract §3 (`:92-93`) · D-12 · INV-5 · GITFLOWS §5.
