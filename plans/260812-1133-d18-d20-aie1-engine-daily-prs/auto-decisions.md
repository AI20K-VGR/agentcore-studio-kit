# Auto-Decision Ledger — 260812-1133-d18-d20-aie1-engine-daily-prs

> Quyết-định con-AI TỰ ra ở chế-độ tự-quyết (KHÔNG phải sổ DEC user-duyệt `docs/decisions.md`). Sổ **chỉ để đọc, advisory** — không chặn việc gì. Nguồn sự-thật = `artifacts/auto-decisions.jsonl`; file này là VIEW sinh ra.

## ⚠ Phải soát (chưa)

_(none)_


## Đã soát

_(none)_


## Chỉ truy-vết

| id | label | in_plan | skill/mode | what | why | evidence | reviewed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 65ad0f6ae2d6 | BEHAVIOR | no | hs:cook/default | llm_source classification frozenset expanded beyond the plan's literal wording (FixtureLLM/known doubles in demo_stubs.py) to also recognize _GoldenAwareLLM (scripts/run_golden_batch.py) and ExtractiveFakeLLM (apps/studio providers/fakes.py) by class name | code-review finding H-1: without this, both real running harnesses (golden-batch D16, apps/studio smoke-eval) would be mislabeled llm_source=gateway despite being pure fixture/fake replay with no live model call, defeating the field's stated purpose (judge-consumption stability signal) | packages/engine/src/studio_engine/executors.py:194 (_KNOWN_STUB_LLM_CLASS_NAMES); packages/engine/scripts/run_golden_batch.py:106 (_GoldenAwareLLM); apps/studio/src/studio_app/providers/fakes.py:33 (ExtractiveFakeLLM) | no |
| cc9d93730e75 | TRIVIAL | yes | hs:cook/default | Main applied 3 rounds of code-review fix-loops directly (R-1/R-2/R-3/R-4 line-anchor + stale-claim corrections, then F-1's 6-anchor off-by-one fix) instead of re-delegating each round to @developer, deviating from cook's delegate-by-default nudge for phase red-green work | Each fix was a text-only prose/comment/line-number correction (no behavior, no test-logic, no API change), independently verified against live source with grep/sed before writing and against the full 6-command regression gate after; re-delegating a 1-line docstring/anchor fix for a 3rd/4th time to a fresh @developer would have cost more context than it protected against, and the cook_delegate_nudge fired advisory (non-blocking) each time | packages/engine/src/studio_engine/executors.py:121-122,255-259; packages/engine/docs/design-notes/aie1-day19-retrieval-failure-modes.md:12,26-27,32,51,63; review-decision.yaml rationale | no |

