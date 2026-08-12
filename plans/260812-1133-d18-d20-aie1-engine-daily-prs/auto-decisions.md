# Auto-Decision Ledger — 260812-1133-d18-d20-aie1-engine-daily-prs

> Quyết-định con-AI TỰ ra ở chế-độ tự-quyết (KHÔNG phải sổ DEC user-duyệt `docs/decisions.md`). Sổ **chỉ để đọc, advisory** — không chặn việc gì. Nguồn sự-thật = `artifacts/auto-decisions.jsonl`; file này là VIEW sinh ra.

## ⚠ Phải soát (chưa)

_(none)_


## Đã soát

_(none)_


## Chỉ truy-vết

| id | label | in_plan | skill/mode | what | why | evidence | reviewed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 65ad0f6ae2d6 | BEHAVIOR | yes | hs:cook/default | llm_source classification frozenset expanded beyond the plan's literal wording (FixtureLLM/known doubles in demo_stubs.py) to also recognize _GoldenAwareLLM (scripts/run_golden_batch.py) and ExtractiveFakeLLM (apps/studio providers/fakes.py) by class name | code-review finding H-1: without this, both real running harnesses (golden-batch D16, apps/studio smoke-eval) would be mislabeled llm_source=gateway despite being pure fixture/fake replay with no live model call, defeating the field's stated purpose (judge-consumption stability signal) | packages/engine/src/studio_engine/executors.py:194 (_KNOWN_STUB_LLM_CLASS_NAMES); packages/engine/scripts/run_golden_batch.py:106 (_GoldenAwareLLM); apps/studio/src/studio_app/providers/fakes.py:33 (ExtractiveFakeLLM) | no |

