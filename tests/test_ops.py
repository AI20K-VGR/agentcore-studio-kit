"""Phase 9 — Ops Delivery gate tests.

These 4 tests lock the ops-delivery contract (Dockerfile F4, compose 3-profile, subtree
squashed-export F13, CI leak-test non-blocking F5) before the ops artifacts exist. They must go
RED before this phase's files are created and GREEN after. See
plans/260717-1516-studio-kit-template/phases/phase-9-ops-delivery.md.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def test_compose_config_valid() -> None:
    """KHÓA: docker-compose.yml (3-profile: default/app/obs) parse hợp lệ qua `docker compose config`.

    `docker compose config` only renders services ACTIVE for the requested profile set (default
    invocation = no profile → only the no-profile services show), so this validates BOTH the
    bare default invocation AND the full stack with every profile explicitly activated — a
    typo'd profile name or a service dangling on an unreachable profile would still surface here.
    """
    compose_path = ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist at kit root"

    default_result = _run(["docker", "compose", "-f", str(compose_path), "config"])
    assert default_result.returncode == 0, (
        f"docker compose config (default profile) failed:\n"
        f"stdout={default_result.stdout}\nstderr={default_result.stderr}"
    )

    full_result = _run(
        ["docker", "compose", "-f", str(compose_path), "--profile", "app", "--profile", "obs", "config"]
    )
    assert full_result.returncode == 0, (
        f"docker compose config (app+obs profiles) failed:\nstdout={full_result.stdout}\nstderr={full_result.stderr}"
    )

    rendered = yaml.safe_load(full_result.stdout)
    services = rendered.get("services", {})
    # docker compose config strips the `profiles:` key from rendered output once a profile is
    # activated, so profile membership is checked against the RAW (unrendered) compose file below
    # — here we only assert the full stack has strictly more services than the default one, and
    # that it renders at all (the assertion above).
    default_rendered = yaml.safe_load(default_result.stdout)
    default_services = default_rendered.get("services", {})
    assert len(services) > len(default_services), (
        f"expected app+obs profiles to add services beyond the default set; "
        f"default={sorted(default_services)}, full={sorted(services)}"
    )
    assert default_services, "expected at least one default (no-profile) service — the default pgvector DB"

    raw = yaml.safe_load(compose_path.read_text())
    profiles_seen: set[str] = set()
    for svc in raw.get("services", {}).values():
        profiles_seen.update(svc.get("profiles", []) or [])
    assert "app" in profiles_seen, f"expected an 'app' profile service, got profiles: {profiles_seen}"
    assert "obs" in profiles_seen, f"expected an 'obs' profile service (Langfuse cluster), got: {profiles_seen}"


def test_compose_uses_pgvector_image() -> None:
    """KHÓA (Decision #2): default DB image là `pgvector/pgvector:pg17`, KHÔNG `postgres:17` trần."""
    compose_path = ROOT / "docker-compose.yml"
    raw = compose_path.read_text()
    doc = yaml.safe_load(raw)
    services = doc.get("services", {})
    default_services = [svc for svc in services.values() if not (svc.get("profiles") or [])]
    assert default_services, "no default (no-profile) service found in docker-compose.yml"
    images = [svc.get("image", "") for svc in default_services]
    assert any("pgvector/pgvector" in img for img in images), (
        f"default service must use pgvector/pgvector:pg17 image, got: {images}"
    )
    assert not any(re.fullmatch(r"postgres:1[0-9]", img) for img in images), (
        f"default service must NOT be a bare postgres image (needs CREATE EXTENSION vector), got: {images}"
    )


def test_dockerfile_copies_all_member_pyproject_no_editable() -> None:
    """KHÓA (F4): builder stage copy TẤT CẢ member pyproject.toml (workspace resolve) TRƯỚC source,
    và `uv sync --no-editable` bắt buộc (.venv runtime không giữ editable-path chết sau khi source
    bị bỏ lại ở builder stage)."""
    dockerfile = ROOT / "Dockerfile"
    assert dockerfile.exists(), "Dockerfile must exist at kit root"
    text = dockerfile.read_text()

    assert re.search(r"FROM .+ AS builder", text), "Dockerfile must have a named `builder` stage"
    assert re.search(r"FROM .+ AS runtime", text), "Dockerfile must have a named `runtime` stage"

    member_pyprojects = [
        "packages/contracts/pyproject.toml",
        "packages/kb/pyproject.toml",
        "packages/engine/pyproject.toml",
        "packages/workbench/pyproject.toml",
        "packages/evalhub/pyproject.toml",
        "apps/studio/pyproject.toml",
    ]
    for member in member_pyprojects:
        assert member in text, f"Dockerfile builder stage must COPY {member} before source (F4 workspace resolve)"
    assert "uv.lock" in text, "Dockerfile must COPY uv.lock (frozen sync)"
    assert re.search(r"COPY\s+pyproject\.toml", text), "Dockerfile must COPY the root pyproject.toml"

    assert "--no-editable" in text, "Dockerfile MUST run `uv sync --no-editable` (F4, mandatory)"
    assert "--frozen" in text, "Dockerfile sync steps must be --frozen (no silent relock in image build)"

    # --no-editable sync must come AFTER source is copied in, and must be the LAST sync (so the
    # installed .venv reflects real source, not just the dep-only pre-warm layer).
    no_install_idx = text.find("--no-install-project")
    no_editable_idx = text.find("--no-editable")
    assert no_install_idx != -1, "Dockerfile must have a dep-only warm layer (`--no-install-project`)"
    assert no_install_idx < no_editable_idx, "--no-install-project (deps-only) must precede the --no-editable sync"

    # Runtime stage must not carry the uv toolchain / builder source — only the .venv.
    runtime_stage = text[text.index("AS runtime") :]
    assert "COPY --from=builder" in runtime_stage, "runtime stage must COPY artifacts FROM builder"
    assert ".venv" in runtime_stage, "runtime stage must copy the builder's .venv"


def test_nda_denylist_catches_pluralized_and_concatenated() -> None:
    """KHÓA (F13): the NDA denylist must catch pluralized/concatenated mentor-material names
    (`rubrics/`, `mentornotes.md`, `solutions/`, `answer_keys.txt`), not only the `mentor-`/
    `rubric.` separator forms. Dual-review catch (@code-reviewer MEDIUM regex hole)."""
    hook = (ROOT / "scripts" / "nda-denylist.sh").read_text()
    # The patterns themselves contain ')' (e.g. `(^|/)`), so split on the array's closing line.
    block_match = re.search(r"DENYLIST_PATTERNS=\((.*?)\n\)", hook, re.DOTALL)
    assert block_match, "could not locate DENYLIST_PATTERNS array"
    patterns = re.findall(r"'([^']+)'", block_match.group(1))
    assert patterns, "could not extract DENYLIST_PATTERNS"
    must_block = ["docs/rubrics/week1.md", "mentornotes.md", "src/solutions/answer.py",
                  "grading/key.csv", "mentor-guide.md", "x.rubric.yaml", "answer_keys.txt"]
    for name in must_block:
        assert any(re.search(p, name, re.IGNORECASE) for p in patterns), f"NDA denylist must block {name!r}"
    for ok in ["packages/kb/src/studio_kb/search.py", "README.md", "apps/web/src/App.tsx"]:
        assert not any(re.search(p, ok, re.IGNORECASE) for p in patterns), f"NDA denylist false-positive on {ok!r}"


def test_leak_job_continue_on_error() -> None:
    """KHÓA (F5): CI job `leak-test` là continue-on-error — đỏ-by-design KHÔNG chặn merge."""
    ci_path = ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists(), ".github/workflows/ci.yml must exist"
    doc = yaml.safe_load(ci_path.read_text())
    jobs = doc.get("jobs", {})
    assert "leak-test" in jobs, f"ci.yml must have a `leak-test` job, got jobs: {list(jobs)}"
    leak_job = jobs["leak-test"]
    assert leak_job.get("continue-on-error") is True, (
        f"leak-test job must set continue-on-error: true (F5, red-by-design non-blocking), got: {leak_job}"
    )
    for required_job in ("lint", "test", "build"):
        assert required_job in jobs, f"ci.yml must have a `{required_job}` job, got jobs: {list(jobs)}"
