# Demo Scope and Scenario — agentcore-studio-kit (Day-25 graduation demo)

> Rút gọn từ bản đầy đủ (probe trực tiếp code HEAD 2026-08-20: `Makefile`, `tests/e2e/test_lifecycle.py`,
> `docker-compose.yml`, `.env.example`, `seed_demo_tenants.py`, `ingest_callisto_v2.py`,
> `test_golden_set_ref_default.py`). Day 25 = **2026-08-21** (`CLAUDE.md` hard floor: 1 hệ thống tích
> hợp đủ 4 quadrant, từ 1 clone `--recursive` sạch, không phải 4 demo quadrant ghép tay).

## 1. Repo có 2 khung "8-bước" khác nhau

- **Khung A — product spine** (`CLAUDE.md`/`srs.md`): Login → Ingest → Build recipe → Run → Trace →
  Eval → Gate/Publish → Chat. Mentor chấm Day-25 theo khung này.
- **Khung B — graduation charter** (`tests/e2e/test_lifecycle.py`, `system-architecture.md` §6):
  Form → 2 tool+KB → Canvas → Test/trace → **Fence-proof** (money-shot) → Eval-gate→Publish →
  **Regression→rollback** (money-shot) → HITL-pause. Không có Login/Chat riêng, nhưng có 2 money-shot
  = P2/P3 trong 4 tiêu chí production-block.

⇒ Kịch bản mục 4 lấy **hợp cả hai** = 9 bước, không bỏ bên nào.

## 2. 3 sự thật xác minh trực tiếp code — đọc trước khi chuẩn bị

1. **`make demo` chỉ là `echo`** — không có harness tự động. Demo bắt buộc là live walkthrough có
   người lái.
2. **`tests/e2e/test_lifecycle.py` — 8/8 test đều `pytest.skip`** dù business logic 4 quadrant đã
   implement thật. Không có 1 dòng test xanh nào trích được cho mentor — mọi PASS phải tự chụp bằng
   chứng lúc demo (mục 5).
3. **Landmine `golden_set_ref`:** `apps/web`'s `recipe/sample.ts` gửi mặc định
   `callisto-smoke-5-v0`, nhưng file thật tên `smoke-5.yaml` → nút "Chấm điểm" 400 ngay lần đầu nếu
   dùng nguyên sample. **Luôn gõ tay `callisto-2.0-golden-30-v1`** (khớp file thật) khi cấu hình agent.

## 3. Pre-flight (fresh recursive clone)

```bash
git clone --recursive <repo-url> && cd agentcore-studio-kit
cp .env.example .env   # cần thật: STUDIO_JWT_SECRET (>=32 ký tự), STUDIO_LLM_PROVIDER
make setup
docker compose --profile app up -d --build   # postgres + app:8000 (make dev suông chỉ bật postgres)
uv run python apps/studio/scripts/seed_demo_tenants.py     # → tenant ankor/borea
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5432/studio
uv run python packages/kb/scripts/ingest_callisto_v2.py    # → 400+400 chunk, vector thật, offline OK
cd apps/web && npm install && npm run dev
```

- **2 tenant demo cố định:** `ankor` (`admin@ankor.vn`) / `borea` (`admin@borea.vn`), UUID hardcode
  khớp 3 nơi trong code (script tự assert trước khi ghi) — không đổi tay.
- **Fake vs LLM thật:** `STUDIO_USE_FAKE_PROVIDERS=true` (mặc định) an toàn, không phụ thuộc mạng;
  `=false`+key thật thuyết phục hơn cho P1/P2 nhưng rủi ro mạng/quota live. Dry-run bằng fake trước,
  demo chính nên chạy thật nếu có key.

## 4. Kịch bản — 9 bước

| # | Bước | Hành động | Kết quả cần thấy |
|---|---|---|---|
| 0 | Login (UC-01) | Login sai mật khẩu trước, đúng sau | 401 rồi mới vào được — fail-closed |
| 1 | Ingest (UC-02) | Verify UI ingest bằng mắt trước giờ demo | Không phát hiện "Placeholder" live |
| 2 | Build recipe form (UC-03) | Điền 8 field, `goldenSetRef=callisto-2.0-golden-30-v1`, thử 1 tool ngoài whitelist | Tool ngoài whitelist bị chặn trước runtime |
| 3 | Canvas 6-node (UC-03) | Vẽ chuỗi thẳng `kb-retrieve→llm-step→condition→tool-call→end`; thử nối 1 node ra 2 cạnh | Banner đỏ tức thời (client, không round-trip). **Không** demo `condition` phân nhánh — `graph_lint` rule 4 chưa nới, sẽ bị chặn |
| 4 | Test + Trace (UC-04) | Bấm Test, xem `TraceViewer` | Đủ event, `agentIdsMatch`/`wiringOk`/`monotonic` xanh; `cost` luôn `0.0` — khai trước với mentor, không phải bug |
| 5 | **MONEY-SHOT** Fence-proof (P2) | Login ankor, hỏi câu chỉ có ở KB borea | `refused=true`, không lộ/bịa; trace vẫn ghi audit |
| 6 | Eval → Publish (UC-05/06) | Chấm điểm → Publish | Verdict PASS → 200, version bump (`GET /versions` phản ánh) |
| 7 | **MONEY-SHOT** Regression → Rollback (P3) | Sửa instructions xấu → re-eval → Publish lại | Verdict FAIL → 409 → tự rollback về bản cũ TRƯỚC khi trả lỗi; verify bằng `GET recipe`/chat thật, không chỉ tin thông báo |
| 8 | HITL-pause (P4, known-gap) | Thêm node `hitl-pause`, chạy Test | Trả đúng shape `{"paused":true,...}` nhưng **không dừng thật** — nói thẳng với mentor, không diễn |
| 9 | Chat (UC-07) | Chat trong scope; admin thử "Thử vai trò" hẹp hơn rồi rộng hơn | Trả lời đúng scope hẹp; mở rộng vượt section bị chặn (UR-08) |

## 5. Known-gap phải khai trước (không để mentor tự phát hiện)

| Gap | Lộ ở bước | Cách nói |
|---|---|---|
| HITL-pause chưa dừng/chờ thật | 8 | Known-gap P4, `CLAUDE.md` mục 6 |
| Cost luôn `0.0` | 4, 7 | Thiết kế hiện tại (D19/kit#120), không phải bug |
| `make demo`/e2e 8/8 skip | Toàn bộ | Không dẫn CI xanh — bằng chứng là ảnh/log live (mục 6) |
| `graph_lint` rule 4 chưa nới cho `condition` | 3 | Chỉ demo dạng thẳng, không hứa phân nhánh |
| `consent_purge` chưa xác nhận route HTTP | — | Không demo trừ khi đã verify |
| Ingest UI tên "Placeholder" | 1 | Verify bằng mắt trước, không phát hiện live |

## 6. Bằng chứng cần thu lúc demo (vì không có test tự động)

- Ảnh/video `TraceViewer` — Bước 4, 5.
- JSON response `/evaluate` — verdict PASS (6) và FAIL (7).
- HTTP 409 body + `GET .../recipe` chứng minh rollback — Bước 7.
- Trace event JSON của `hitl-pause` cho thấy walk không dừng — Bước 8.

## 7. Liên hệ Sprint-3

Tài liệu này = hạng mục Day-25 hard floor (`CLAUDE.md` Sprint 3), lead sở hữu điều phối 8-bước —
không phải ghép 4 demo quadrant tay. Sau ≥1 dry-run xanh, việc kế tiếp: nộp tự-chấm 12-cell trước
Gate-3 (2026-08-28, [[sprint3-scoring-plan]]).
