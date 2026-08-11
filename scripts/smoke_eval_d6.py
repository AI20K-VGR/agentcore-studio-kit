"""Smoke-eval D6 trên LUỒNG THẬT — form → interpreter → KB → trace → eval.

    uv run python scripts/smoke_eval_d6.py

Đây là deliverable D6 của **AIE-2**, do **DE (Nguyễn Đông Anh) làm thay ngày 27/07 vì AIE-2 nghỉ**.
Ghi rõ để hồ sơ hai người không bị đọc lệch.

## Vì sao là script ở repo cha, không phải module trong `studio_evalhub`

`.importlinter` cấm `studio_evalhub` import `studio_engine`/`studio_kb`; chỗ hợp lệ duy nhất để
dựng cả bốn quadrant là `apps/studio` (composition root) — mà đó là vùng mentor, 4 kỹ sư chỉ READ
(câu hỏi Q-A của `plans/day06_plan.md`, chưa có trả lời). Chính plan đó đã chốt sẵn phương án lui:

> *Nếu không kịp: chấp nhận D6 chứng minh bằng script/test ngoài tầng package, **ghi rõ đó là dàn
> dựng để chạy thử, chưa phải composition thật***.

File này là đúng cái đó. Nó **không** phải composition root, và cố ý không nằm trong `packages/**`
để không bị import-linter quét, cũng không bị pytest gom (CI của các repo con clone repo cha theo
con trỏ submodule đã ghi, hiện đang cũ — một file test import engine mới sẽ làm đỏ cả suite).

## Bốn quadrant đều là hàng thật, không mock lẫn nhau

| chặng | dùng gì | của ai |
|---|---|---|
| form | `create_recipe_d6()` | workbench (SWE) |
| interpreter | `studio_engine.run()` — đi động theo `dag.edges` | engine (AIE-1) |
| KB | `StaticKbSearch()` trên 25 chunk Callisto thật | kb (DE) |
| trace | `TraceEvent` thật do interpreter emit | contracts + engine |
| eval | `EvalHarness.run_smoke` + `score_case` | evalhub (AIE-2) |

Golden-set đọc **thẳng từ `packages/kb/golden/smoke-10.yaml`** (`callisto-smoke-10-v0`, 10 case),
không chép tay — bản chép in-code ở
`studio_evalhub/cli.py::_demo_golden_set` là nguồn sự thật thứ hai, sửa YAML mà quên sửa nó thì lệch
im lặng. Script này không có vấn đề đó.

Trace lấy từ `RunResult.events` (bản trong bộ nhớ) chứ không qua Postgres: Docker chưa dựng được
hôm nay. `CaseRun.events` cho phép cả hai nguồn. Vòng round-trip qua `obs.trace_events` được chứng
minh riêng ở `packages/kb/tests/test_spine_live.py` (8 test, **chưa chạy xanh — vẫn chờ Postgres**).

## Mảnh giả duy nhất còn lại, và vì sao nó phải giả

`_NaiveExtractiveLLM`. `LLM` là seam nhà cung cấp **ngoài**, không phải một trong 4 quadrant, nên nó
không thuộc luật *"không mock lẫn nhau"* — `FixtureLLM` (engine) và `FakeLLM` (studio) đều là double
theo đúng thiết kế.

Nó **cố ý không biết đáp án golden**. Một double trả sẵn `"3 ngày làm việc"` sẽ cho điểm tuyệt đối
và chứng minh **số không** — đó đúng là kiểu né-tích-hợp mà DoD `:54` sinh ra để diệt. Một double
luôn trả `[[REFUSED]]` cũng là gian lận, chỉ theo chiều ngược lại. DoD viết *"in **N**/5"*, không
viết 5/5: con số thật, dù thấp, là kết quả; con số đẹp từ runner dàn xếp thì không.
"""

from __future__ import annotations

import asyncio
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID

import yaml
from studio_contracts.nodes import NodeType
from studio_engine import run
from studio_evalhub.agent_runner import AgentAnswer, CaseRun
from studio_evalhub.golden_case import GoldenCase, GoldenSet
from studio_evalhub.harness import EvalHarness, SmokeResult, citations_from_trace
from studio_kb.doc_factory import TENANT_IDS
from studio_kb.static_search import StaticKbSearch
from studio_workbench import create_recipe_d6
from studio_workbench.tenant_wall import resolve_session

_ROOT = Path(__file__).resolve().parent.parent
_GOLDEN = _ROOT / "packages" / "kb" / "golden" / "smoke-10.yaml"
_AGENT_ID = "agent-callisto-d6"


class _NaiveExtractiveLLM:
    """`LLM` double **chỉ đọc prompt**, không bao giờ đọc golden-set.

    Thay cho `_ContextBlindLLM` của bản trước. Bản đó trả một câu trung tính vì lúc ấy prompt thật
    sự không chứa chunk nào — `LlmStepExecutor` chỉ truyền `node.params["prompt"]` (= `instructions`
    của recipe). Engine `22627e7` đã sửa: `build_prompt(query, chunks)` nay dựng prompt từ chính
    kết quả truy xuất, mỗi đoạn trích mở đầu bằng `[chunk_id]` trên một dòng riêng. Giữ double mù
    sau khi chunk đã vào prompt là đo sai — nó sẽ báo 0 điểm cho một đường đã thông.

    **Chính sách: lấy đoạn trích ĐẦU TIÊN, chép lại, trích đúng id của nó.** Đây là hành vi của một
    model ngoan nhưng ngu — nó đọc thứ được đưa, không suy luận, không xếp hạng lại, không tự quyết
    có nên từ chối hay không.

    Vì sao đây KHÔNG phải gian lận: nó không hề thấy `expected` hay `expected_citation`. `chunk_id`
    nó trích đến từ **dữ liệu KB vừa truy xuất**, không từ người viết fixture. Đổi kho tài liệu hay
    đổi công thức xếp hạng thì câu trả lời tự đi theo — đúng tính chất mà một fixture gõ tay không
    có (xem `_DemoRunner`/`StubAgentRunner` của evalhub: 5 câu trả lời soạn cho khớp `expected`,
    luôn ra điểm tuyệt đối và chứng minh số không).

    Hai chỗ nó dốt là **cố ý**, và chỗ nó fail chỉ ra đúng giới hạn thật:

    - **Chỉ đọc top-1.** Đáp án nằm ở hạng 2–3 thì nó trượt (SC-10). Một model thật đọc cả 3 đoạn.
    - **Không biết từ chối.** Truy xuất ra chunk nào là nó chép chunk đó, kể cả khi chẳng liên quan
      tới câu hỏi (SC-04/07/09). Một model thật đọc header prompt — header đã dặn *"nếu các đoạn
      trích không chứa câu trả lời, hãy nói rõ là không có thông tin và KHÔNG trích dẫn gì"*.

    Nói cách khác: điểm của bộ này là **cận dưới** của hệ thống với một model tệ nhất còn đọc được,
    không phải điểm của hệ thống.
    """

    # `[id]` đứng một mình trên một dòng — đúng khuôn `build_prompt` dựng ra.
    _EXCERPT_RE = re.compile(r"^\[([\w#-]+)\]\n", re.MULTILINE)

    def __init__(self) -> None:
        self.prompts_seen: list[str] = []

    async def complete(self, prompt: str, **kwargs: object) -> str:
        del kwargs
        self.prompts_seen.append(prompt)

        marks = list(self._EXCERPT_RE.finditer(prompt))
        if not marks:
            # Không đoạn trích nào (truy xuất rỗng, vd SC-05 chéo-vai) → không có gì để chép và
            # không có gì để trích. Không trích ⇒ engine đọc thành `refused=True`.
            return "Không có đoạn trích nào để trả lời."

        first = marks[0]
        end = marks[1].start() if len(marks) > 1 else prompt.rfind("\n\nCâu hỏi:")
        body = prompt[first.end() : end if end != -1 else len(prompt)].strip()
        return f"{body}\n\n[{first.group(1)}]"


class _UnusedEmbedding:
    """`EmbeddingService` double. `LlmStepExecutor` nhận qua constructor nhưng không dùng ở phase
    này; recipe D6 không có bước embed."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        del texts
        return []


class EngineAgentRunner:
    """`AgentRunner` **thật**: dựng recipe của SWE, chạy qua interpreter của AIE-1, KB của DE.

    Đây là adapter `#29` mà `agent_runner.py` mô tả (*"bản thật là adapter mỏng bọc
    `studio_engine.run`, tiêm từ `studio_app`"*) — chỗ đúng của nó là composition root; ở đây là
    bản dàn dựng vì chỗ đúng chưa tồn tại.

    Map `RunResult` → `CaseRun`: `answer` lấy từ output node `llm-step` (**tra theo `dag`, không
    hardcode `"n2"`** — vòng đi giờ suy từ `dag.edges` nên id node không còn đoán được), `events`
    đổ thẳng `RunResult.events`.
    """

    def __init__(self, kb_search: StaticKbSearch, tenant_slugs: Mapping[UUID, str]) -> None:
        self._kb_search = kb_search
        self._tenant_slugs = tenant_slugs
        self.llm = _NaiveExtractiveLLM()

    async def run_case(
        self,
        *,
        agent_id: str,
        query: str,
        tenant_id: UUID,
        section_roles: list[str],
    ) -> CaseRun:
        slug = self._tenant_slugs[tenant_id]
        recipe = create_recipe_d6(
            agent_id=agent_id,
            tenant_id=tenant_id,
            instructions="Bạn là trợ lý nội bộ. Trả lời dựa trên tài liệu được cung cấp.",
            model="gemini-2.5-flash",
            tool_whitelist=["kb_search"],
            kb_id="kb-callisto-v1",
            scope=f"{slug}/{','.join(section_roles)}",
            query=query,
        )
        session_context = resolve_session({"tenant_id": tenant_id, "user": "eval-harness", "roles": section_roles})
        result = await run(
            recipe,
            kb_search=self._kb_search,
            llm=self.llm,
            embedding=_UnusedEmbedding(),
            trace_writer=_NullTraceWriter(),
            session_context=session_context,
        )

        llm_node_ids = [n.id for n in recipe.dag.nodes if n.type is NodeType.LLM_STEP]
        raw = result.final_state.get(llm_node_ids[0], {}) if llm_node_ids else {}
        out: dict[str, object] = raw if isinstance(raw, dict) else {}

        return CaseRun(
            answer=AgentAnswer(
                answer=str(out.get("answer", "")),
                citations=[c for c in out.get("citations", []) if isinstance(c, str)],
                refused=bool(out.get("refused", False)),
            ),
            events=result.events,
        )


class _NullTraceWriter:
    """Sink không-làm-gì. Trace mà bộ chấm dùng lấy từ `RunResult.events`; đường xuống Postgres
    (`PgTraceWriter`) cần Docker, hôm nay chưa dựng được — xem docstring đầu file."""

    async def write(self, event: object) -> None:
        del event


def load_golden_set(path: Path = _GOLDEN) -> GoldenSet:
    """Đọc golden-set từ YAML **nguồn** của DE, không chép tay."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return GoldenSet(
        golden_set_ref=raw["golden_set_ref"],
        cases=[GoldenCase(**case) for case in raw["cases"]],
    )


def render(results: list[SmokeResult]) -> str:
    header = f"{'case_id':<10} {'nhánh':<12} {'success':<9} {'citation_acc':>12}"
    lines = [header, "-" * len(header)]
    for r, case in zip(results, load_golden_set().cases, strict=True):
        branch = "từ-chối" if case.expects_refusal else "trả-lời"
        lines.append(f"{r.case_id:<10} {branch:<12} {'PASS' if r.success else 'FAIL':<9} {r.citation_accuracy:>12.2f}")
    passed = sum(1 for r in results if r.success)
    lines.append("-" * len(header))
    lines.append(f"{passed}/{len(results)} PASS")
    return "\n".join(lines)


async def main() -> int:
    golden = load_golden_set()
    runner = EngineAgentRunner(StaticKbSearch(), {uuid: slug for slug, uuid in TENANT_IDS.items()})

    print(f"golden-set : {golden.golden_set_ref}  ({len(golden.cases)} case, đọc từ {_GOLDEN.relative_to(_ROOT)})")
    print(f"agent      : {_AGENT_ID}\n")

    results = await EvalHarness().run_smoke(_AGENT_ID, golden, runner, TENANT_IDS)
    print(render(results))

    # ── Chẩn đoán: vì sao ra con số đó ────────────────────────────────────────
    print("\nCHẨN ĐOÁN — trace nói gì (đây là phần đi vào daily-note):\n")
    for case in golden.cases:
        cr = await runner.run_case(
            agent_id=_AGENT_ID,
            query=case.query,
            tenant_id=TENANT_IDS[case.tenant],
            section_roles=case.section_roles,
        )
        retrieve = [e for e in cr.events if e.node_type is NodeType.KB_RETRIEVE]
        chunks = [c["chunk_id"] for e in retrieve for c in e.outputs.get("chunks", [])]
        print(f"  {case.case_id}  kb-retrieve → {len(chunks)} chunk: {chunks}")
        print(f"         citations trong trace = {citations_from_trace(cr.events)}  refused={cr.answer.refused}")

    print(f"\n  LLM đã nhận {len(set(runner.llm.prompts_seen))} prompt khác nhau cho {len(golden.cases)} case.")
    n_excerpt = sum(len(_NaiveExtractiveLLM._EXCERPT_RE.findall(p)) for p in runner.llm.prompts_seen)
    print(f"  Tổng {n_excerpt} đoạn trích `[chunk_id]` đã vào prompt (engine `22627e7` build_prompt).")

    # ── Tách bạch trách nhiệm: KB có trả đúng chunk không? ────────────────────
    # `citation_accuracy` chấm trên chunk ĐƯỢC TRÍCH. Phép đo dưới đây chấm trên chunk ĐƯỢC TRUY
    # XUẤT — cùng công thức, khác nguồn. Nó trả lời câu "0 điểm là do KB lấy sai chunk, hay do đoạn
    # LLM→citation đứt?". KHÔNG phải điểm số, không thay `citation_accuracy`; chỉ để quy trách nhiệm.
    print("\n  Nếu chấm citation trên chunk ĐÃ TRUY XUẤT thay vì ĐÃ TRÍCH:")
    hits = total = 0
    for case in golden.cases:
        if not case.expected_citation:
            continue
        cr = await runner.run_case(
            agent_id=_AGENT_ID,
            query=case.query,
            tenant_id=TENANT_IDS[case.tenant],
            section_roles=case.section_roles,
        )
        retrieved = {c["chunk_id"] for e in cr.events for c in e.outputs.get("chunks", [])}
        hit = sum(1 for c in case.expected_citation if c in retrieved)
        hits, total = hits + hit, total + len(case.expected_citation)
        print(f"    {case.case_id}  {hit}/{len(case.expected_citation)}  kỳ vọng {case.expected_citation}")
    print(f"    → {hits}/{total} chunk kỳ vọng ĐÃ được KB lấy về đúng.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
