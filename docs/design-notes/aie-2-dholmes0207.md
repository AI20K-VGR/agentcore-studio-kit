---
id: studio.design-note.aie-2
type: design-note
day: D11
issue: "#83"
author: AIE-2 — Lưu Tiến Duy (@dholmes0207)
date: 2026-08-03
scope: eval harness v1 · golden-set · judge cap ≤100/cache · descope exact-match
status: ĐÃ NỘP · Duyệt: CHỜ
---

# Design-note — AIE-2 · Bộ chấm: eval harness v1, golden-set, judge cap, descope

> **Chỗ đặt:** kit root, **không** trong submodule `evalhub`. Lý do là lý do chấm điểm: file trong
> submodule chỉ thấy được **nếu con trỏ kit đã bump**, và lệch con trỏ đã lấy điểm hai lần (`kit#73`,
> `kit#76`/`#77`). DE và SWE đặt design-note trong repo của mình — cả hai cách đều được, miễn con trỏ
> được bump; chọn kit vì nó không phụ thuộc bước đó.
>
> **Neo, không suy lại:** GUIDE-C §4.1 (`:280`) — gate = **AND** hai ngưỡng · toán tử **`>=`** · tầng
> **aggregate**. GUIDE-C §3.2 — ngưỡng là **số thập phân tròn, chốt và ghi ra TRƯỚC khi dựng dataset**.

## 1 · Scope — và non-scope

**Trong scope hôm nay (D11):** hợp đồng `scorecard` freeze-ready (9 clause) · 5 quyết định treo từ D2
đã có đáp án · luật bump cho ca thứ tư · pin nhánh từ-chối · đổi neo xfail `no-trace-no-proof`.

**Non-scope, nói rõ để không ai chờ:**

| Không làm | Vì sao |
|---|---|
| Wiring publish/rollback đọc `gate.verdict` | S3 / D24 — bút SWE |
| Dashboard / trace viewer | D25 |
| Implement `compute_scorecard` / `EvalHarness.run` | Xem §3 — đây là **phương án bỏ**, không phải việc quên |
| Fence chunk-level, trục INV-1 roles | S3 / D21-22. Bộ chấm **quan sát** hàng rào, không **tạo** hàng rào |
| Đổi `harness.py:159` | GUIDE-C `:305` — *"must NOT be changed"* (register §11 từng chỉ thị rồi **thu hồi**, CP-2.1) |

## 2 · Phương án chọn — bộ chấm là *quan sát viên*, không phải *người làm hàng rào*

Một câu: **bộ chấm đọc TRACE, không đọc lời agent tự khai.**

- `citation_accuracy` + leak-check lấy từ `CaseRun.events`, **không** từ `AgentAnswer.citations`. Bằng
  chứng đã có trong repo, không phải lập luận: `_LeakyKb` (`e2e_smoke_eval.py`) là KB cố ý hỏng fence —
  agent **vẫn nói năng lịch sự bình thường**, không gì trong câu trả lời tố cáo điều gì, mà conjunct
  `no_leak` **đỏ**, vì chunk chéo tenant **đã nằm trong trace trước khi LLM mở miệng**. Hàng rào đặt ở
  đầu ra không đổi được sự thật là dữ liệu đã bị lấy ra; nó chỉ đổi cách dữ liệu được phát âm.
- `tenant_scope_ok` **observe-only, không gate `success`** — hai lý do, cả hai là lý do chứ không phải
  tiện: (a) bộ chấm không tạo fence nên không phát verdict thay fence; (b) `score_case` không nhận
  `events` nên **cấu trúc mà nói** không đọc được `tenant_id`.
- **`no-trace-no-proof` thuộc tầng giữ `events`, không thuộc `score_case`.** Đây là chỗ bản vá hiển
  nhiên **là sai**, và nói ra điều đó là một phần của thiết kế: invariant đúng là *"không có trace quan
  sát được ⇒ FAIL"*, **không** phải *"citation rỗng ⇒ FAIL"* — luật sau ngược oracle F02
  (GUIDE-C `:592`: *"refused, cited nothing ⇒ the case PASSES"*).

**Golden-set:** DE sở hữu **giá trị** (case + nhãn tay + tên bộ), AIE-2 sở hữu **nơi lưu + loader**
(`eval.golden_sets`). Chọn bảng đó vì nó là bảng **có người ghi được** — `obs.golden_sets` nằm trong
`apps/studio`, ngoài fence-lane của DE, nên DE không điền được. Đó là câu hỏi của chính DE, trả bằng
quyền chứ không bằng sở thích.

**Judge cap ≤100/ngày + cache:** cap là **điều kiện kích hoạt descope**, không phải tính năng. Khi
chạm trần ⇒ rơi về exact-match scorer (INV-7). Cache theo `(case_id, actual)` vì `actual` tất định với
`ExtractiveFakeLLM`, nên cache hit trong CI là 100% và cap không bao giờ chạm trong test.

## 3 · Phương án BỎ (bắt buộc) — và đây là phương án mạnh nhất có thật

### Bỏ 1 · Implement `compute_scorecard` hôm nay để đóng `O3.1`

`O3.1` là ô **nặng nhất** trong grid (+1.91), và nó hỏi *"thứ đó có tồn tại không"* — hôm nay
`gate.verdict` vẫn chưa có, **0/9 ô Grid C dựng được**. Nên đây là phương án hấp dẫn nhất, không phải
bù nhìn.

**Bỏ, vì land hôm nay là tự phá 4 ô đắt nhất trong grid của chính mình.** GUIDE-C §3.2 đòi ngưỡng
literal phải **có trước** dataset; dataset (golden-30) về **D14-15**, sau corpus D13. Viết gate trước
khi có ngưỡng chốt-trước nghĩa là ngưỡng sẽ được chọn *sau* khi thấy số — đúng thứ §3.2 cấm
(`threshold := giá trị mà lượt chạy vừa tính ra`). Hệ quả đo được: 4 ô *"exactly-at"* (D-22 so `==`
trên ngưỡng tròn, `11/20 = 0.55` exact trong CPython 3.14) thành `unknown`.

Cộng thêm ba giá độc lập: `test_gate_blocks_on_fail` là `xfail(strict=True)` ⇒ land hôm nay làm nó
**XPASS ⇒ FAIL** trong lúc quyền đổi marker (M6, GUIDE-C §2.3: *"Do not edit that marker on your own
authority"*) **chưa chốt**; `test_harness_judge_compute_not_implemented` đỏ ngay ngày freeze; và #50
xếp eval-gate blocking là **gold-plating** (S3/D24), ETA của GUIDE-C là D20, #108 là D16.

⇒ Đúng hạn là **D16**, và claim `O3.1 = I` hôm nay là calibration, không phải khiêm tốn.

### Bỏ 2 · Cho `citation_accuracy` gate `success` ở mức per-case

**Bỏ** vì nó **đếm hai lần** mọi lỗi citation: trace sai đã làm `citation_accuracy` tụt ở tầng
aggregate; cho nó gate `success` nữa thì cùng một lỗi kéo cả hai trục của một gate **AND** ⇒ ngưỡng
mất nghĩa. Thêm một lý do đọc-tài-liệu: register của mentor **từng chỉ thị rồi thu hồi** đúng điểm này
(GUIDE-C §4.1 / CP-2.1, `:305`) — nêu nó ra là để chứng minh đã đọc **phần thu hồi**, không chỉ phần
chỉ thị.

## 4 · Trade-off — nói cả chiều lệch

| Chọn | Được | Mất | Chiều lệch |
|---|---|---|---|
| **token-contains** thay exact-match | Câu trả lời đúng ý mà khác cách diễn đạt vẫn PASS; `"1 ngày"` **không** khớp `"11 ngày"` (token `"11"` ≠ `"1"`) nên tránh bẫy substring thô | Không bắt **phủ định** — câu phủ định vẫn "chứa" cụm nên vẫn PASS. Ghi là **giới hạn đã biết, KHÔNG xfail** | **Lệch LÊN** ở ca phủ định (nguy hiểm hơn) |
| **exact-match** thay judge (descope) | Tất định, không phụ thuộc quota/mạng | Câu đúng ý khác chữ bị tính sai | **Lệch XUỐNG** — gate có thể chặn bản đạt, **không** cho lọt bản không đạt. Đây là chiều lệch đúng cho một hàng rào |
| **leak sanity mức slug** thay fence UUID | Chạy được hôm nay, 0 phụ thuộc | `_citation_tenant` cắt tiền tố chuỗi `chunk_id` (`harness.py:49-57`) — **nhãn mềm**: trùng được, sửa được | Chỉ chứng minh tới **mức nhãn**; fence thật là `StaticKbSearch` so UUID + RLS |

Đường lên mức UUID **không cần đổi contract** — đây là chỗ đã **tự rút một tiền đề của mình**:
`outputs["chunks"]` đã mang `tenant_id: UUID` per-chunk từ D5, 4 consumer đang đọc. Thiếu là **một
dòng hợp đồng**, không phải một field. `scorecard-v0.md:335-337` từng định giá nó thành *"mini-RFC +
4/4 chữ ký"* — sai, và định giá quá cao làm việc bị hoãn vô cớ.

## 5 · Rủi ro

| Rủi ro | Vì sao nó thật | Trạng thái |
|---|---|---|
| **Không có nguồn nhãn tay cho `Judge.agreement`** | Field **đích** đã có (`scorecard.py:19`); field **nguồn không tồn tại** ở bất kỳ đâu trong workspace; hằng số **bị cấm** (`judge.py:6-9`) ⇒ **mọi ô judge là `todo:` không có ETA cam kết được**. Đây là món **không tự đặt đáp án** | 🔴 chặn · chủ **mentor** · hạn D18 |
| **Mọi ngưỡng đang pin vào một stand-in** | `ExtractiveFakeLLM` chỉ đọc top-1, không có năng lực quyết định refusal. Với mặc định `0.9/0.95` (`builder.py:48-49`), số đo thật là bộ 5 → `0.80`, bộ 10 → `0.60` / `citation_accuracy` `0.833` ⇒ **một recipe TỐT cũng FAIL cả hai trục**, nên demo *"sửa instructions tệ → FAIL → chặn publish"* chứng minh **số không** | 🟡 recalibrate D16, chủ AIE-2. **Không** hạ số hôm nay — hạ bây giờ là hiệu chỉnh theo stand-in |
| **golden-30 về sau corpus D13** | Corpus-cutover D13 gần chắc làm `smoke-5`/`smoke-10` hiện tại vỡ ⇒ số ở D16 có thể bị đọc là **hồi quy của bộ chấm**. Kế hoạch: sáng D13 hỏi lịch cutover, chiều re-run và báo lệch trước | 🟡 chủ DE (giao bộ) + AIE-2 (báo lệch) · hạn D15 |
| **Carrier `citations` là hành vi, không phải cấu trúc** | `citations_from_trace` gom **node-agnostic** (`harness.py:85-89`) nên phân biệt retrieved/grounded **chỉ vì engine hôm nay tình cờ hành xử vậy**. Bất kỳ node trả **dict** có key `"citations"` sẽ mang citations vào trace — `condition`/`tool-call` đều trả dict | 🟡 chờ clause AIE-1 (D12). Lưới đỡ đã có: siết theo `node_type` **phía evalhub** |
| **`refused` cho dương-tính-giả (#14)** | `refused = not citations`: câu bịa trọn vẹn mà quên đóng ngoặc ⇒ `citations=[]` ⇒ `refused=True` ⇒ **SC-04 PASS dù agent đã bịa**. Trên bài kiểm hàng rào, **xanh-giả nguy hiểm hơn đỏ-giả** | 🟡 chủ **AIE-1** · hạn D17 |
| **`eval.scorecards`/`eval.golden_sets` không có `tenant_id` và không có RLS** | Tự khai: workspace có RLS trên **1/11** bảng; hai bảng của AIE-2 là **0/2**. Đề nghị đồng-ký mini-RFC schema-drift (carry #8) của DE với hai bảng này tính vào | 🟡 chủ AIE-2 + DE |

---

**Trạng thái nộp:** `ĐÃ NỘP docs/design-notes/aie-2-dholmes0207.md@<sha> lúc <giờ> · Duyệt: CHỜ`
Ô DoD *"4/4 design-note approved"* **không tick** — đó là hành động của approver, không phải của người nộp.
