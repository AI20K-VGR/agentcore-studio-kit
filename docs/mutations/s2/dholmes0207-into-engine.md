---
id: studio.mutations.s2.dholmes0207-into-engine
type: mutation-report
target_quadrant: packages/engine (bút AIE-1 — @TranBaDat2607)
seeded_by: AIE-2 — Lưu Tiến Duy (@dholmes0207)
date: 2026-08-03
day: D11
method: khai-trước (declared-first) — kế thừa phương pháp của DE
engine_sha: 3f61e2aaaf8d7dbd226bb8c711595ee0d3ff7fc4
pushed: false   # mutation KHÔNG bao giờ push — worktree local, revert sau mỗi lượt
---

# 5 mutation gieo vào `packages/engine` — bảng khai-trước vs thực đo

> **Vì sao engine, không phải kb hay workbench.** Carry #7 ghi rõ engine **chưa có sweep mutation tự
> động** (so với sweep 93-mutant của DE mà mentor gọi là chuẩn) ⇒ yield thông tin/mutation cao nhất. Và
> engine sản xuất **mọi** tín hiệu bộ chấm tiêu thụ (carrier · `refused` · thứ tự `ts` · `tenant_id` mỗi
> event · `outputs["chunks"]`) ⇒ mỗi mutation map **1:1** với một clause `scorecard` đang xin freeze.
> Tức bài tập này **chính là bước verify của freeze**, không phải việc phụ: bắt được là bằng chứng
> **cho** cách viết clause; không bắt được là một test chủ quadrant phải viết. **Cả hai kết cục đều đẩy
> freeze đi.**
>
> **Phương pháp là của DE**, dùng lại nguyên: nêu mutation **và** bài phải đỏ **trước khi chạy**. Mentor
> gọi đó là instrument tốt nhất nhóm và nó từng bắt hai bug trong chính tooling của DE. Chỗ hai cột
> **lệch nhau** chính là finding.
>
> **Luật tính điểm:** chỉ **assertion ngữ nghĩa** tính là *bắt được*. `SyntaxError` / `ImportError` /
> collection error = **KHÔNG** bắt (xem M5 lượt 1 — đó là lỗi của người gieo, không phải bằng chứng).

## Bảng kết quả

| # | Seam · Mutation | KHAI TRƯỚC | THỰC ĐO | Khớp? |
|---|---|---|---|---|
| **M1** | carrier `citations` · `interpreter.py:270` `citations = None` → `[c["chunk_id"] for c in outputs["chunks"]]` | engine **ĐỎ** ở `test_non_llm_events_have_zero_tokens_and_no_citations`; **evalhub XANH** | engine **1 failed** — đúng bài đã khai. **evalhub 42 passed, 2 xfailed — XANH** | ✅ **khớp** |
| **M2** | `refused` · `executors.py:264` `not citations` → `not retrieved_chunks` (về mốc D4) | engine **ĐỎ**; evalhub xanh ⇒ lệch im lặng | engine **3 failed**; **evalhub XANH** | 🟡 khớp về kết cục, **lệch về số bài** (khai 5, thực 3) |
| **M3** | thứ tự `ts` · `interpreter.py:285-287` xoá clamp `now = last_ts + timedelta(microseconds=1)` | engine **ĐỎ** ở `test_event_timestamps_strictly_increase`; kb reader **XANH** | engine **84 passed — XANH**. Chạy lại bài đó **30 lượt: 0/30 đỏ**. kb reader 17 passed | ❌ **LỆCH — finding lớn nhất** |
| **M4** | trục INV-1 roles · `executors.py:152` `else []` → `else ["public","hr","finance","engineering"]` (fail-**open**) | **KHÔNG CHẮC** — nhánh `else` có thể không test nào đi qua | engine **84 passed**, kb **71 passed, 2 xfailed** — **XANH HẾT** | ✅ khớp (khai đúng là *không chắc*, và kết cục là không ai bắt) |
| **M5** | key `outputs["chunks"]` · `interpreter.py:266` rename `"chunks"` → `"retrieved"` | **XANH HẾT trong CI** ⇒ invariant đang xin DE freeze có **0 lớp test bảo vệ** | engine **1 failed** (`test_kb_retrieve_event_outputs_wraps_raw_list_in_dict`) · kb `test_spine_live` **3 failed** · apps/studio 39 passed · evalhub xanh | ❌ **LỆCH — và nó sửa chính lập luận của tôi** |

**2/5 dòng lệch** (M3, M5) — vượt ngưỡng DoD *"≥1 dòng declared ≠ actual"*.

## Finding 1 (M3) · Clamp `ts` KHÔNG được test nào bảo vệ, và bài trông-như-bảo-vệ-nó pass vì lý do tình cờ

**Đo:** xoá hẳn clamp ⇒ `test_event_timestamps_strictly_increase` (assert `len(set(timestamps)) == 4`)
vẫn xanh **30/30 lượt**.

**Nghĩa là:** `datetime.now(UTC)` ở độ phân giải microsecond tự nhiên đã cho 4 giá trị phân biệt tăng
dần cho 4 node chạy tuần tự trên máy này. Nên bài đó **không** đo clamp — nó pass **nhờ độ phân giải
đồng hồ**, một tính chất của môi trường, không phải của code.

**Hai hệ quả, và cả hai đều quan trọng cho freeze:**

1. **Clamp là code không có lưới.** Xoá nó thì toàn bộ engine vẫn xanh. Một refactor dọn "nhánh `if`
   trông như không bao giờ chạy" sẽ xoá đúng thứ giữ cho `ts` phân biệt, và **không bài nào báo**.
2. **Bài `ts` hiện là flaky-chờ-xảy-ra.** Nó pass vì 4 node chạy chậm hơn 1µs so với nhau. Trên đồng hồ
   thô hơn (Windows ~15.6ms), trong container bị giảm timer resolution, hoặc khi số node tăng và mỗi
   node nhanh hơn, `now` sẽ trùng ⇒ `len(set(...)) < 4` ⇒ đỏ **ngẫu nhiên**, và lúc đó người ta sẽ đi
   sửa *bài test* thay vì nhận ra clamp mới là chỗ cần đo.

**Điều này SỬA lập luận DE-2 của tôi.** Tôi định nói với DE rằng vế producer *"mọi emitter PHẢI phát
`ts` tăng nghiêm ngặt"* **đã có lưới đỡ thật** là clamp `interpreter.py:285-287`. Đo lại thì: clamp có
trong code, nhưng **không có gì verify clamp hoạt động**. Nên clause producer nếu freeze hôm nay sẽ là
một clause **chưa được đo**.

**Test đề xuất cho AIE-1** (không tự vá — đây là quadrant của AIE-1):

```python
async def test_ts_clamp_forces_distinct_when_clock_is_coarse() -> None:
    """KHÓA CLAMP, không khoá đồng hồ: với một clock trả CÙNG một giá trị cho mọi lần gọi,
    `ts` vẫn phải phân biệt và tăng — đó là việc của clamp `interpreter.py:285-287`.
    Bài `test_event_timestamps_strictly_increase` KHÔNG khoá được điều này: xoá clamp,
    nó vẫn xanh 30/30 vì `datetime.now(UTC)` tự nó đã đủ mịn trên máy CI hiện tại."""
```

Cần một seam để tiêm clock (hiện `interpreter.py` gọi `datetime.now(UTC)` trực tiếp) — đó là quyết định
của chủ quadrant, nên nêu chứ không tự làm.

## Finding 2 (M5) · Tôi đã sai, và phép đo sửa tôi trước khi tôi kịp gửi

**Khai trước:** *"xanh hết trong CI ⇒ invariant `outputs["chunks"]` đang xin DE freeze hiện có **0 lớp
test bảo vệ**"* — và tôi đã viết đúng câu đó vào bản nháp review `kb#10` như một lập luận **bằng số**.

**Thực đo: sai.** Rename key `"chunks"` → `"retrieved"` bị bắt bởi:

- `engine/tests/test_trace_event_emission.py::test_kb_retrieve_event_outputs_wraps_raw_list_in_dict`
  — **1 assertion ngữ nghĩa, ngay trong engine**. Tôi đã bỏ sót bài này khi khảo sát.
- `packages/kb/tests/test_spine_live.py` — **3 failed** (`test_kb_retrieve_got_a_real_uuid_scoped_call`,
  `test_citations_are_grounded`, `test_inv1_recipe_tu_khai_tenant_khac_thi_phien_thang`). Tôi khai là
  "gated bởi Postgres nên khả năng cao không chạy" — Postgres **có** chạy, và chúng bắt được.

⇒ **Invariant đó có 2 lớp bảo vệ, không phải 0.** Lập luận "bằng số" của tôi sẽ là một lập luận **sai
bằng số** nếu gửi đi. Đã sửa bản nháp review trước khi gửi.

**Cái vẫn còn đúng, và giờ là ask nhỏ hơn nhiều:** hợp đồng `trace-event.v0.md:77` vẫn khai `outputs`
là *"⏸ hoãn S2"*. Nên chỗ hở **không** phải thiếu test — mà là **doc không khai một invariant mà code
và test đều đang cưỡng chế**. Ask đổi từ *"xin freeze một thứ chưa ai bảo vệ"* thành *"xin doc ghi lại
đúng thứ 2 lớp test đã bảo vệ"*. Ask sau dễ đồng ý hơn, và đúng hơn.

**Đây là lý do phương pháp khai-trước đáng giá:** nó biến một niềm tin sai thành một finding về chính
mình, **trước** khi niềm tin đó thành một câu nói với đồng đội.

## Finding 3 (M4) · Trục INV-1 roles: fail-open không ai bắt — bằng chứng từ một lượt chạy

`executors.py:152` đổi `else []` (fail-closed) thành `else ["public","hr","finance","engineering"]`
(fail-**open**: roles méo ⇒ mở hết mọi vai) ⇒ **engine 84 passed, kb 71 passed — không ai đỏ.**

Nhánh `else` chỉ chạy khi `raw_roles` **không phải list** — và không test nào đi qua đường đó. Nghĩa là:
nếu một recipe (hoặc một payload lỗi) làm `section_roles` méo kiểu, hàng rào vai **mở hết** và toàn bộ
suite vẫn xanh.

Đây là **bằng chứng cứng từ một lượt chạy** (không phải từ một báo cáo) rằng trục **INV-1 roles cần chủ
hôm nay** — #74 §6: *"needs an owner at D11 freeze. AIE-1 or SWE"*. AIE-2 **không nhận** trục này: bộ
chấm **quan sát** hàng rào, không **tạo** hàng rào. Đề xuất **SWE** (#112/D17 đã gán *"Own INV-1:
session_id resolve {tenant,user,roles} server-side"*), hạn gán **D12**.

## Finding 4 (M1) · Phân biệt retrieved/grounded của bộ chấm là TÌNH CỜ — clause thành bắt buộc

Đây là phép đo **đắt giá nhất** trong 5, và nó khớp khai trước:

- engine **ĐỎ** đúng một bài: `test_non_llm_events_have_zero_tokens_and_no_citations` ⇒ AIE-1 **đã**
  khoá đúng câu tôi cần.
- **evalhub XANH hoàn toàn** (42 passed, 2 xfailed) ⇒ khi `kb-retrieve` **cũng** mang `citations`, helper
  `citations_from_trace` node-agnostic (`harness.py:85-89`) **đếm gộp vui vẻ**, và không một bài nào của
  bộ chấm báo.

⇒ `citation_accuracy` của tôi phân biệt *retrieved* với *grounded* **chỉ vì engine hôm nay tình cờ hành
xử vậy**. Bảo đảm hiện tại là **hành vi**, không phải **cấu trúc**. Đó chính là lý do clause §6 của
`scorecard.v1.md` là **bắt buộc**, không phải nice-to-have — và cũng là lý do tôi tự dựng lưới phía
evalhub (siết theo `node_type is NodeType.LLM_STEP`) thay vì chỉ chờ clause.

## Finding 5 (M2) · Đổi công thức `refused` lần thứ ba sẽ lệch bộ chấm im lặng

engine **3 failed** (đúng nhóm đã khai, lệch số lượng):
`test_refused_true_when_chunks_were_retrieved_but_none_answered` ·
`test_refused_true_when_bracket_names_a_chunk_from_another_tenant` ·
`test_golden_case_refusal_flag_matches_its_label[SC-04-cross-tenant-retrieval-NOT-empty]`.

**evalhub XANH.** ⇒ AIE-1 bảo vệ tốt công thức ở phía mình, nhưng bộ chấm **không có lưới nào** cho việc
công thức đổi nghĩa. `refused` đã đổi nghĩa **hai lần trong 4 ngày**
(`not retrieved_chunks` → sentinel → `not citations`). Lần thứ ba mà không báo thì `SC-04`/`SC-07`/`SC-09`
lật **im lặng** trên bảng điểm của tôi.

Đây là lập luận cho clause A1-2: freeze **seam + nghĩa** của `refused`, **không** freeze công thức, kèm
điều kiện *đổi công thức phải báo trên #84 cùng ngày*. Rủi ro tôi nhận, và lưới tôi tự dựng: test A4 của
adapter chạy `interpreter.run` lấy quyết định gốc rồi so với `AgentAnswer` đã map — khoá *"adapter map
trung thực"*, không khoá *"engine quyết bằng công thức nào"*.

## Kỷ luật thực thi

| | |
|---|---|
| Mutation đã push? | **KHÔNG.** Worktree local, `git checkout -- src/` sau **mỗi** lượt |
| Cây sau T9 | `git -C packages/engine status --short` → **rỗng**; con trỏ engine vẫn `3f61e2aa` = `origin/main` |
| Bẫy DE #1 — ANSI | pytest phát ANSI dù stdout là pipe ⇒ regex `FAILED` khớp rỗng. Lưới: `--color=no` **và** đọc **exit code**, không chỉ grep |
| Bẫy DE #2 — `.pyc` | bytecode cache khoá theo `(mtime giây, size)` ⇒ mutant 1 ký tự viết trong cùng giây load bytecode cũ. Lưới: `PYTHONDONTWRITEBYTECODE=1` |
| Lỗi của chính người gieo | M5 **lượt 1 vô hiệu**: comment `# MUTANT M5` chèn vào giữa dict literal ⇒ `SyntaxError` ⇒ 13 collection error. Theo luật, collection error **không tính là bắt được** ⇒ đã gieo lại M5 không có inline comment. Ghi lại thay vì im, vì một sweep báo "bắt được 13" bằng `SyntaxError` là một sweep nói dối |

## `## Phản hồi của chủ quadrant`

*Chỗ này để @TranBaDat2607 tự append bằng commit của chính mình — một artifact, hai tác giả chứng minh
được (mentor: "Both of you write down what happened"). Không ai viết hộ phần này.*
