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
> **Vì sao file này tồn tại dù kit#130 đã closed:** #130 chốt được **quy tắc** rồi đóng, nên quy tắc
> có mà **chỗ tra thì không**. Bản tổng hợp cuối D11 của AIE-1 làm đúng việc tra đó — nhưng nó nằm
> trong một **comment**, tức ở bước verify *"clone repo fresh"* nó không phải artifact. File này là
> bản trong-clone của đúng thứ đó.
>
> **Vì sao ở kit chứ không ở submodule:** file trong submodule chỉ thấy được **nếu con trỏ kit đã
> bump**. Lệch con trỏ đã lấy điểm hai lần (`kit#73`, `kit#76`/`#77`). Index ở kit root thì
> `git clone --recursive` thấy ngay.

## ⚠️ File này KHÔNG ghi trạng thái — cố ý

Không có cột *"đã merge chưa"*, *"mấy chữ ký"*, *"freeze chưa"*. Một bảng trạng thái viết tay trong
một ngày 9 PR thì **sai trước khi ai đọc tới** — bản đầu của chính file này có những cột đó và chúng
lạc hậu trong vài giờ.

Thứ ở đây là thứ **không mục**: đường dẫn canonical, cơ chế, và **lệnh sinh ra sự thật khi chạy**.

```bash
# Trạng thái thật của mọi PR hợp đồng — chạy cái này, đừng tin một bảng viết tay.
# (nguồn: bản tổng hợp cuối D11 của @TranBaDat2607, kit#84)
for r in kb workbench evalhub engine contracts; do
  gh pr list --repo AI20K-VGR/agentcore-studio-$r --state open \
    --json number,title,reviews \
    --jq --arg R "$r" '.[]|"\($R)#\(.number)  \([.reviews[]|"\(.author.login):\(.state)"]|join(","))  \(.title)"'
done
```

```bash
# Chữ ký thật trên một PR, kèm SHA nó ký lên — Approve bị dismiss khi tác giả push,
# nên phải đối chiếu commit_id với head thì mới biết chữ ký còn hiệu lực.
gh pr view <N> --repo AI20K-VGR/<repo> --json reviews,headRefOid \
  --jq '.headRefOid[0:8] as $h | .reviews[] | "\(.author.login) \(.state) \(.commit.oid[0:8]) \(if .commit.oid[0:8]==$h then "còn hiệu lực" else "STALE" end)"'
```

## Bốn hợp đồng — decision-log ở repo của bút

| Hợp đồng | Bút | Decision-log |
|---|---|---|
| **recipe** | SWE — @Dozyboy | `workbench:docs/decisions/recipe.md` |
| **trace-event** | DE — @DongAnh2704 | `kb:docs/decisions/decision-log-trace-event.md` |
| **kb.search** | DE — @DongAnh2704 | `kb:docs/decisions/decision-log-kb-search.md` |
| **scorecard** | AIE-2 — @dholmes0207 | `evalhub:docs/decisions/scorecard.md` |

> DE giữ **hai** hợp đồng nên tách hai file (kb#10, `844feb22`, 04/08); `kb:docs/decisions/decision-log.md`
> giờ là **index nội bộ kb**, không còn là nội dung. Bảng trên từng trỏ vào file cũ cho cả hai dòng —
> đúng loại lạc hậu mà một index phải tự tránh, và là lý do file này **không** giữ cột trạng thái.

## Design-note D11 — cũng ở repo của bút

| Vai | File |
|---|---|
| AIE-1 — @TranBaDat2607 | `engine:docs/design-notes/aie1-day11.md` |
| AIE-2 — @dholmes0207 | `evalhub:docs/design-notes/aie2-day11.md` |
| DE — @DongAnh2704 | `kb:docs/design-notes/de-day11.md` |
| SWE — @Dozyboy | `workbench:docs/design-notes/swe-day11.md` |

> AIE-2 từng đặt **cả decision-log lẫn design-note** ở kit root rồi phải chuyển về `evalhub` — hai lần,
> cùng một lớp lỗi. Bản tổng hợp của AIE-1 soi `evalhub#6` và kết luận design-note *"không tách file
> riêng"*, vì từ trong evalhub thì thật sự không thấy. **Một artifact đặt ở chỗ người audit không nghĩ
> tới thì mất giá trị đúng ở bước nó cần có giá trị nhất** — đó là lý do quy tắc "nội dung ở repo của
> bút" đáng giữ, và lý do file index này không được phình ra thành chỗ chứa nội dung.

## Cơ chế chữ ký (ADR-D11-01)

1. **Chữ ký thật = bấm Approve trên PR** chứa hợp đồng — xác thực bằng tài khoản GitHub, không giả
   được. Bảng tự-điền trong file bị loại: ai sửa file cũng gõ được tên người khác.
2. **Decision-log chỉ ghi DẤU VẾT** của Approve (ai · PR · ngày · `<repo>@<sha>`), không phải chỗ ký.

**Hai giới hạn cơ học của cơ chế này** (đo bởi @TranBaDat2607, kit#84 §5 — cần vào ADR):

- GitHub **không cho tác giả tự approve PR của mình** ⇒ bút của một hợp đồng không ký được hợp đồng
  đó ⇒ **trần cứng là 3/4**, ô *"4/4 chữ ký"* không đạt được theo định nghĩa. Đề nghị câu bổ sung:
  *"tác giả PR tính là đã ký; cần 3 Approve từ 3 người còn lại."*
- **Mỗi lần tác giả push là xoá sạch chữ ký.** Đo được: kb#10 approve `09:51:27` → push `10:04:53` →
  dismiss `10:04:58`. ⇒ 4/4 không phải đích tiến dần tới, nó là thứ phải gom trong **một cửa sổ không
  ai đụng vào PR**.

## ADR

| ADR | Nội dung | Tác giả | Chỗ ở |
|---|---|---|---|
| **ADR-D11-01** | Nơi đóng dấu freeze · decision-log ở đâu · hình thức 4/4 chữ ký | @Dozyboy | **chỉ trong comment** [#84](https://github.com/AI20K-VGR/agentcore-studio-kit/issues/84#issuecomment-5163714300) — chưa có file |
| **ADR-D11-02** | Nới `required`→`optional` không bump `SCHEMA_VERSION` + **ca thứ tư** (tương thích dây, không tương thích reader) | @dholmes0207 | chưa land — chờ chốt chỗ ở |

> **ADR-D11-01 đặt luật freeze cho cả 4 hợp đồng nhưng không có trong clone sạch.** Đề xuất một chỗ ở
> chung (`docs/adr/`) đang mở trên #84. **Không land hộ** — ký tên người khác lên một ADR là đúng cái
> lớp-1 muốn chống; ADR-D11-02 của AIE-2 cũng chưa land vì tạo namespace mới là việc hỏi team trước.

## Mini-RFC cross-lane

| Mini-RFC | Nội dung | Chỗ ở |
|---|---|---|
| **tenant + RLS** | Chuẩn `tenant_id UUID` + RLS cho 3/11 bảng có đường user đọc; loại trừ có chủ đích `core.jobs`/`core.outbox`; DROP `obs.golden_sets` | @DongAnh2704, trong `kb:docs/mini-rfc-tenant-schema-unify.md` |
| **AgentRunner Protocol seam** | Promote `AgentRunner` lên `studio_contracts.protocols` | @dholmes0207, `evalhub:docs/mini-rfc/MRFC-2026-08-03-agentrunner-protocol-seam.md` — **PRE-WRITTEN, cố ý chưa nộp** |

Khuôn dùng lại được, kèm bảng *"KHÔNG dùng khi nào"* (4 ca hay bị định giá quá cao):
`evalhub:docs/mini-rfc/TEMPLATE.md`.

## Cách cập nhật file này

Mỗi bút tự sửa **dòng của hợp đồng mình**; không ai viết hộ dòng người khác (umbrella-contract §2).
Thêm ADR/mini-RFC mới thì thêm một hàng.

**Không thêm cột trạng thái.** Nếu thấy cần biết trạng thái, chạy một trong hai lệnh ở đầu file — một
lệnh không bao giờ lạc hậu, một bảng viết tay thì có.
