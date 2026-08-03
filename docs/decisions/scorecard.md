---
id: studio.decision-log.scorecard
type: decision-log
contract: scorecard
pen: AIE-2 — Lưu Tiến Duy
freeze: FREEZE-READY   # chưa FROZEN — xem "Còn mở" bên dưới
---

# Decision-log — scorecard (AIE-2)

> Khung + chỗ đặt theo [kit#130](https://github.com/AI20K-VGR/agentcore-studio-kit/pull/130) (@Dozyboy)
> và **ADR-D11-01** ([#84](https://github.com/AI20K-VGR/agentcore-studio-kit/issues/84)). File này là
> **bản tổng cross-repo**; chi tiết kỹ thuật + câu chữ clause nằm ở
> [`agentcore-studio-evalhub/docs/contracts/scorecard.v1.md`](https://github.com/AI20K-VGR/agentcore-studio-evalhub/blob/main/docs/contracts/scorecard.v1.md).
>
> **Về cách đánh id:** `recipe.md` dùng `DL-R*`. File này dùng `DEC-*` vì các id đó **đã được trích ở
> nhiều chỗ khác** trước khi có khung chung — trong `scorecard.v1.md`, trong `scorecard-v0.md` §3, và
> trong docstring test (`test_smoke_runner.py`). Đổi id bây giờ sẽ làm chết những chỗ trích đó.

## D11 · 2026-08-03

| # | Quyết định | Lý do | PR / bằng chứng | Trạng thái |
|---|---|---|---|---|
| **DEC-01** | Nới `required` → `optional` **KHÔNG bump** `SCHEMA_VERSION`, **điều kiện**: đếm được **0 reader giả định non-null**. Nếu > 0 ⇒ breaking cho reader dù guard payload xanh | `contracts/__init__.py:5-12` chỉ liệt kê **3** loại breaking (rename · removal · required-add) ⇒ ca này là **ca thứ tư**: *tương thích trên dây, KHÔNG tương thích với reader*. `test_freeze_guard.py:36` chỉ đo chiều required-add ⇒ cơ chế hiện có **không phát hiện** ca này. Đo: **0 reader / 4 constructor** toàn test fixture; `331 → 333 passed` đúng +2 test mới; mypy `110 file` không đổi | ADR-D11-02 · `grep -rn "\.judge\b\|judge=" packages apps scripts tests` | ✅ quyết (phần áp cho `judge`) · 🟡 clause chung chờ 4 bút, hạn D12 |
| **DEC-02** | `CaseResult.judge: Judge \| None = None`. `None` = *"case chấm KHÔNG qua LLM-judge"* — giá trị trung thực **duy nhất** trước S3. Hằng số `Judge(...)` bị **cấm** | `judge.py:6-9` cấm giá trị hằng; `agreement` đo *scorer có đồng ý với nhãn tay hay không*, nên với case exact-match FAIL nó **không xác định** — không phải 1.0, không phải 0. Điền 1.0 là bịa phép đo và **không phân biệt được** với judge thật đồng thuận 100% ⇒ hỏng âm thầm mọi aggregate trên `agreement` (INV-4). GUIDE-C `:855-887` | [contracts#1](https://github.com/AI20K-VGR/agentcore-studio-contracts/pull/1) (@Dozyboy mở, AIE-2 xác nhận với tư cách giữ bút) | 🟡 chờ merge |
| **DEC-03** | `Scorecard.recipe_hash: str \| None = None`, kèm luật consumer: publish coi `None` là *"không verify được ⇒ từ chối"* (**fail-closed**) ⇒ optional là đủ, **không** cần required-add | Ruling **D-24** (`02-MATRIX.md:284`): *"Add `recipe_hash` to `Scorecard`"*, owner AIE-2. Hôm nay giá 1 dòng; sau freeze giá 4 chữ ký. Điểm yếu nói thẳng: **land một field chưa có producer** — `Recipe` chưa có `version`/hash (`recipe.py:79-94`) dù `wb.recipe_versions` đã tồn tại (`workbench/.../schema.py:39`) | PR riêng (AIE-2) — **chưa mở tại thời điểm ghi dòng này** | 🔴 chưa mở PR |
| **DEC-04** | `citation_accuracy` nhánh từ-chối, **ba tầng**: per-case giữ `1.0` **là quy ước, có pin test** · aggregate **loại khỏi mẫu số** · render in `n/a` | Số: bộ 10 báo `0.90` vs thật **`0.833`** (+0.067; 3 case đã đỏ SC-04/07/09 vẫn góp `1.00`). Phép tính chí tử (GUIDE-C Q8): `10×1.0 + 20×0.85 = đúng 0.90` ⇒ với `>=` một bản **đáng FAIL** lại PASS ngay ngưỡng 0.9. Không đổi per-case: `SmokeResult.citation_accuracy` phải giữ `float` — 3 renderer `:.2f` sẽ `TypeError` với `None`; và quy ước vacuous-truth tồn tại **cả hai nhánh** (`harness.py:167`) | `test_refusal_citation_accuracy_is_pinned_convention_not_measurement` (mới, D11) · GUIDE-C §6.4.2 đòi pin, §9 ghi **chưa tồn tại** | ✅ quyết + pin xanh |
| **DEC-05** | `no-trace-no-proof`: invariant đúng là *"không có trace quan sát được ⇒ FAIL"*, **KHÔNG** phải *"citation rỗng ⇒ FAIL"*. Cưỡng chế ở **tầng giữ `events`**, không ở `score_case`. Chữ ký `score_case` **không đổi**. Hiện thực D16 | `score_case` chỉ nhận `retrieved_citations: list[str]` (`harness.py:145`) ⇒ **cấu trúc mà nói** không phân biệt được *"chưa có run"* vs *"có run, không trích gì"*; `tenant_scope_ok` phân biệt được **vì nhận `events`** (`harness.py:119-120`). Nguyên nhân là **tầng**, không phải cẩu thả. Luật cũ ngược oracle **F02** (GUIDE-C `:592`: *"refused, cited nothing ⇒ the case PASSES"*). Fixture `test_determinism.py:113` dựng ca từ-chối bằng `events=[_event([])]` — **một event, zero citation** = F02, không phải no-trace | xfail `test_smoke_runner.py` **đổi neo** sang `run_smoke` với `CaseRun.events == []`, giữ `strict=True` · docstring `test_refusal_success` sửa từ *"ghi hành vi hiện tại"* → *"khoá luật đúng"* | ✅ quyết · cặp test mâu thuẫn thành cặp đã-quyết |
| **DEC-06** | Chữ ký = **Approve trên PR** (xác thực GitHub); decision-log chỉ ghi **dấu vết**. **Bỏ** ý định làm bảng tự-điền trong file contract, và **bỏ** ý định làm `sig-<github-id>.md` per-người | Theo ADR-D11-01 + kit#130. Bảng tự-điền: ai sửa file cũng gõ được tên người khác. `sig-*.md` per-người: lập luận gốc của nó là *"một người gõ hộ 4 dòng thì `git log --format='%an'` ra một tên"* — tách theo **hợp đồng** (kit#130) đã giải quyết chính xác điều đó, nên `sig-*.md` thành **dư**. Xin thêm **một cột `<repo>@<sha>`**: chữ ký không nêu bytes nó ký thì là trang trí | ADR-D11-01 · kit#130 | ✅ theo team |
| **DEC-Q3** | `section_roles` resolve **server-side**, harness dựng phiên mang quyền rồi chạy case — **không** truyền `case.section_roles` thẳng vào `kb.search` | Chữ trong doc AIE-2 đã đúng (`golden_case.py:110-116`); phần còn thiếu là **code của người khác**: lỗ nằm ở recipe tự khai roles (`executors.py:138` đọc `node.params.get("section_roles")`), và `Recipe` là bút SWE | `scorecard-v0.md` §3 Q3 | 🟡 hoãn — chủ **SWE + DE**, hạn **D17** |
| **DEC-Q4** | **KHÔNG** promote `AgentRunner` lên `studio_contracts.protocols` hôm nay | Thêm seam thứ 4/5 vào layer đáy là **mở rộng bề mặt freeze đúng ngày đóng băng nó**; `AgentRunner` (`agent_runner.py:76`) chạy tốt như Protocol nội bộ và `lint-imports` đã `1 kept, 0 broken` ⇒ layering **không** đòi promote; adapter sống ở composition root `apps/studio`. Phương án bỏ: promote ⇒ 4/4 chữ ký cho **mỗi** lần đổi shape seam, trong lúc seam còn tiến hoá qua D14/D16 | `docs/mini-rfc/MRFC-2026-08-03-agentrunner-protocol-seam.md` (**PRE-WRITTEN**, cố ý chưa nộp) | 🟡 hoãn — chủ **AIE-2 + AIE-1**, hạn **D14** |
| **DEC-Q5** | `eval.golden_sets` (`schema.py:20-25`, bút AIE-2) là **nguồn sự thật**. DE **sinh + gán nhãn**, giao YAML ở `packages/kb/golden/`; AIE-2 **nạp**. `obs.golden_sets` bỏ | Lý do là **quyền**, không phải sở thích — và là Q-D của chính DE (`trace-event.v0.md:242`): *"`obs.golden_sets` nằm trong `apps/studio/` — không phải fence-lane của DE. DE điền bằng cách nào?"* Đáp: **không điền được**. Ranh giới: DE sở hữu **giá trị**, AIE-2 sở hữu **nơi lưu + loader** (§2.6). Loader hết blocker: `pyyaml>=6.0` khai tường minh `pyproject.toml:26` từ `kit#65` | `scorecard-v0.md` §3 Q5 · review trên [kb#10](https://github.com/AI20K-VGR/agentcore-studio-kb/pull/10) | 🟡 chờ DE xác nhận |
| **DEC-07** | Rút một tiền đề của chính AIE-2: leak-check mức UUID **KHÔNG** cần đổi contract | `scorecard-v0.md:335-337` viết *"cần `tenant_id` per-chunk → đổi contract → mini-RFC + 4/4 chữ ký"*. Đo lại: dữ liệu **đã có từ D5** ở `outputs["chunks"]` (`interpreter.py:265-268`; `KbSearchResultItem.tenant_id: UUID`), **4 consumer đang đọc**. Thiếu là **một dòng hợp đồng** (`trace-event.v0.md:77` khai `outputs` là *"⏸ hoãn S2"*), **0 bump, 0 mini-RFC**. Định giá quá cao làm việc bị hoãn vô cớ | `scorecard-v0.md` §2.8 (giữ cả câu sai + phần rút) | ✅ rút, có ghi lại |

## Còn mở — chặn `FROZEN` thật sự

| # | Nội dung | Chờ ai | Hạn |
|---|---|---|---|
| F-1 | [contracts#1](https://github.com/AI20K-VGR/agentcore-studio-contracts/pull/1) (`judge` → optional) merge | @TranBaDat2607 / @hieubui2409 (CODEOWNERS) | D11 |
| F-2 | PR `recipe_hash` (DEC-03) mở + merge | AIE-2 mở · CODEOWNERS merge | D11 |
| F-3 | 4/4 Approve trên hai PR trên | SWE · DE · AIE-1 · AIE-2 | D11 |
| F-4 | Clause **carrier `citations` chỉ trên `llm-step`** — hành vi engine đã đúng và **đã có test engine khoá** (`test_trace_event_emission.py:152`), nhưng clause chưa tồn tại ⇒ bảo đảm hiện tại là **hành vi**, không phải **cấu trúc** | **AIE-1** | D12 |
| F-5 | Clause **`outputs["chunks"]`** thành invariant có tên (DEC-07) | **DE** | D15 |
| F-6 | **Nguồn nhãn tay** cho `Judge.agreement` — field đích đã có (`scorecard.py:19`), field **nguồn không tồn tại**, hằng số bị cấm ⇒ **chặn mọi ô judge** | **mentor** | D18 |

**Chưa lật `freeze: FROZEN`** — F-1…F-3 chưa đủ cả ba. Trạng thái báo cáo là **freeze-ready**.

## Hoãn — mọi món có chủ + hạn (0 món vô chủ)

| Món | Chủ | Hạn |
|---|---|---|
| Cách biểu diễn DEC-04 trong `Aggregate` (nullable vs `n_scored_citation`). Ghi đúng chữ: *"`aggregate` không tính lại được từ payload `results` đã lưu"* | AIE-2 | D16 |
| Hiện thực `no-trace-no-proof` ở tầng `run_smoke`/`EvalHarness.run` (DEC-05) | AIE-2 | D16 |
| Recalibrate ngưỡng `success`/`citation_accuracy` sau golden-30 trên corpus thật. Số đo nay: bộ 5 → `0.80`, bộ 10 → `0.60` / `0.833` thật ⇒ **với mặc định `0.9/0.95` một recipe TỐT cũng FAIL cả hai trục** | AIE-2 | D16 |
| Giao **golden-30** (`callisto-golden-30-v1`, sinh SAU corpus D13). Nhận chia lô 20@D15 + 10@sáng D16 **nếu chia lô có trong log**. Không nhận *"sẽ có"* | **DE** | D15 |
| Dọn alias `_retrieved_citations` — comment `harness.py:237-247` ghi *"KHÔNG dọn trước D11 freeze"*, **hạn đó hết hôm nay** nên phải cấp hạn mới. Consumer thật còn lại: `scripts/smoke_eval_d6.py:66,249` | AIE-2 | D16 |
| `match_mode` (`exact`/`judge`) thành field **optional** trên `GoldenCase` khi bộ 30 về. `GoldenCase` là kiểu **nội bộ quadrant** (`golden_case.py:8`) ⇒ **không bao giờ** cần mini-RFC | AIE-2 + DE | D16 |
| Breakpoint #14 — `refused = not citations` cho **dương-tính-giả**: câu bịa trọn vẹn mà quên đóng ngoặc ⇒ `citations=[]` ⇒ `refused=True` ⇒ **SC-04 PASS dù agent đã bịa**. Trên bài kiểm hàng rào, **xanh-giả nguy hiểm hơn đỏ-giả** | **AIE-1** | D17 |
| **Chủ trục INV-1 roles** — #74 §6: *"needs an owner at D11 freeze. AIE-1 or SWE"*. AIE-2 **không nhận**: bộ chấm **quan sát** hàng rào, không **tạo** hàng rào. Đề xuất **SWE** (#112/D17 đã gán *"Own INV-1: session_id resolve {tenant,user,roles} server-side"*) | **chưa có chủ** — đề xuất SWE | gán **D12** |
| Job CI so con trỏ kit với `main` từng submodule (đã lệch mất điểm 2 lần: `kit#73`, `kit#76`/`#77`) | AIE-2 (issue follow-up) | S2 |

## Dấu vết chữ ký (ADR-D11-01 lớp 2 — KHÔNG phải chỗ ký)

Chữ ký thật = **Approve trên PR**. Bảng này chỉ **chép lại** trạng thái đã có thật trên GitHub.

| Vai | GitHub | PR | Approve? | Ngày | `<repo>@<sha>` |
|---|---|---|---|---|---|
| AIE-2 (bút) | @dholmes0207 | contracts#1 | — | — | — |
| AIE-1 | @TranBaDat2607 | contracts#1 | — | — | — |
| DE | @DongAnh2704 | contracts#1 | — | — | — |
| SWE | @Dozyboy | contracts#1 | *(tác giả PR)* | 2026-08-03 | `contracts@2b95ca9` |

Verify không cần tin ai:

```bash
gh pr view 1 --repo AI20K-VGR/agentcore-studio-contracts --json reviews \
  --jq '.reviews[]|"\(.author.login) \(.state) \(.commit.oid[0:8])"'
```

**Trạng thái: 0/4 chữ ký thật.** Không báo 4/4, và không tick ô DoD nào dựa trên bảng này.
