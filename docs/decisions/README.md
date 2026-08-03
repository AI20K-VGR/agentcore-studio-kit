---
id: studio.decision-log.index
type: decision-log-index
owner: cả nhóm (SWE/DE/AIE-1/AIE-2) — mỗi bút tự cập nhật dòng của mình
scope: agentcore-studio (4 quadrant, 9 repo)
started: 2026-08-03
canonical_rule: nội dung ở repo của bút · kit chỉ giữ index
---

# Decision-log — index cross-repo

> **Kit chỉ là INDEX. Không repo nào có nội dung bị nhân bản ở đây.**
>
> Nguồn quy tắc: **ADR-D11-01** (@Dozyboy, [#84](https://github.com/AI20K-VGR/agentcore-studio-kit/issues/84#issuecomment-5163714300))
> và lần lặp cuối của [kit#130](https://github.com/AI20K-VGR/agentcore-studio-kit/pull/130)
> (*"kit stays pure index, no repo's content duplicated here"*).
>
> **Vì sao file này tồn tại dù kit#130 đã closed:** #130 chốt được **quy tắc** rồi đóng, nên quy tắc có
> mà **chỗ tra không có** — muốn biết trạng thái 4 hợp đồng phải mở 4 repo. File này chỉ bù đúng chỗ đó:
> một bảng trỏ đi, không chép nội dung, không thay bút ai. Nếu @Dozyboy muốn mở lại #130 theo cách khác
> thì file này nhường — nó là chỗ tra tạm, không phải một convention mới.
>
> **Vì sao ở kit chứ không ở submodule:** file trong submodule chỉ thấy được **nếu con trỏ kit đã bump**.
> Lệch con trỏ đã lấy điểm hai lần (`kit#73`, `kit#76`/`#77`), và luật chấm là *"closing an issue whose
> artifact I cannot find in a fresh clone counts against you"*. Index ở kit root thì `git clone
> --recursive` thấy ngay, không phụ thuộc bước bump.

## 4 hợp đồng schema

| Hợp đồng | Bút | Decision-log (ở repo của bút) | Trạng thái freeze |
|---|---|---|---|
| **recipe** | SWE — @Dozyboy | [`workbench:docs/decisions/recipe.md`](https://github.com/AI20K-VGR/agentcore-studio-workbench/blob/day11/recipe-freeze-ready/docs/decisions/recipe.md) · PR [workbench#12](https://github.com/AI20K-VGR/agentcore-studio-workbench/pull/12) | 🟡 FREEZE-READY, chờ merge |
| **trace-event** | DE — @DongAnh2704 | [`kb:docs/decisions/decision-log.md`](https://github.com/AI20K-VGR/agentcore-studio-kb/pull/10) · PR [kb#10](https://github.com/AI20K-VGR/agentcore-studio-kb/pull/10) | 🟡 FREEZE-READY, chờ merge |
| **kb.search** | DE — @DongAnh2704 | cùng nguồn PR kb#10 | 🟡 FREEZE-READY, chờ merge |
| **scorecard** | AIE-2 — @dholmes0207 | [`evalhub:docs/decisions/scorecard.md`](https://github.com/AI20K-VGR/agentcore-studio-evalhub/blob/aie-2/day11-scorecard-freeze/docs/decisions/scorecard.md) · PR [evalhub#6](https://github.com/AI20K-VGR/agentcore-studio-evalhub/pull/6) | 🟡 FREEZE-READY, chờ merge |

**Không hợp đồng nào `FROZEN`** tính tới 2026-08-03. Cả 4 đều là **FREEZE-READY** — có nội dung chốt,
chưa đủ điều kiện lật cờ (PR chưa merge và/hoặc chưa đủ 4/4 chữ ký). Mỗi file ở trên tự liệt kê điều
kiện còn thiếu của nó.

## Cơ chế chữ ký (ADR-D11-01)

1. **Chữ ký thật = bấm Approve trên PR** chứa hợp đồng đó — xác thực bằng tài khoản GitHub, không giả
   được. Bảng tự-điền trong file bị loại: ai sửa file cũng gõ được tên người khác.
2. **Decision-log chỉ ghi DẤU VẾT** của Approve (ai · PR · ngày · `<repo>@<sha>`) để có một chỗ nhìn
   tổng. Không phải chỗ ký thay.

Verify không cần tin ai:

```bash
gh pr view <N> --repo AI20K-VGR/<repo> --json reviews \
  --jq '.reviews[]|"\(.author.login) \(.state) \(.commit.oid[0:8])"'
```

## ADR

| ADR | Nội dung | Tác giả | Chỗ ở |
|---|---|---|---|
| **ADR-D11-01** | Nơi đóng dấu freeze · decision-log ở đâu · hình thức 4/4 chữ ký | @Dozyboy | hiện **chỉ trong comment** [#84](https://github.com/AI20K-VGR/agentcore-studio-kit/issues/84#issuecomment-5163714300) — chưa có file trong repo |
| **ADR-D11-02** | Nới `required`→`optional` không bump `SCHEMA_VERSION` + **ca thứ tư** (tương thích dây, không tương thích reader) | @dholmes0207 | chưa land — đang xin đồng thuận chỗ ở trên #84 |

> ⚠️ **Một lỗ đáng ghi:** ADR-D11-01 đặt ra luật freeze cho cả 4 hợp đồng nhưng **chỉ sống trong một
> comment GitHub** ⇒ ở bước verify *"I clone your repo fresh"* nó **không phải artifact**. Và mentor đã
> nói ADR là một trong các tiêu chí chấm S2. Đề xuất một chỗ ở chung (`docs/adr/`) đang mở trên #84 —
> **không land hộ ADR-D11-01**, vì ký tên người khác lên một ADR là đúng cái lớp-1 muốn chống.

## Mini-RFC cross-lane đang mở

| Mini-RFC | Nội dung | Chỗ ở | Chữ ký |
|---|---|---|---|
| **tenant + RLS** | Chuẩn hoá `tenant_id UUID` + bật RLS cho 3/11 bảng có đường user đọc; loại trừ có chủ đích `core.jobs`/`core.outbox`; DROP `obs.golden_sets` | DE, trong [kb#10](https://github.com/AI20K-VGR/agentcore-studio-kb/pull/10) (`docs/mini-rfc-tenant-schema-unify.md`) | DE ✅ · SWE ⬜ · AIE-1 ⬜ · AIE-2 ⬜ |
| **AgentRunner Protocol seam** | Promote `AgentRunner` lên `studio_contracts.protocols` | AIE-2, [`evalhub:docs/mini-rfc/MRFC-2026-08-03-agentrunner-protocol-seam.md`](https://github.com/AI20K-VGR/agentcore-studio-evalhub/blob/aie-2/day11-scorecard-freeze/docs/mini-rfc/MRFC-2026-08-03-agentrunner-protocol-seam.md) | **PRE-WRITTEN, cố ý chưa nộp** — quyết định D11 là chưa promote |

Khuôn mini-RFC dùng lại được (kèm bảng *"KHÔNG dùng khi nào"* — 4 ca hay bị định giá quá cao):
[`evalhub:docs/mini-rfc/TEMPLATE.md`](https://github.com/AI20K-VGR/agentcore-studio-evalhub/blob/aie-2/day11-scorecard-freeze/docs/mini-rfc/TEMPLATE.md).

## Cách cập nhật file này

Mỗi bút tự sửa **dòng của hợp đồng mình**. Không ai viết hộ dòng người khác — cùng nguyên tắc *"mỗi
quadrant 1 owner"* (umbrella-contract §2). Nếu thêm ADR hoặc mini-RFC mới thì thêm một hàng, không chép
nội dung vào đây.
