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


def test_subtree_squashed_excludes_mentor() -> None:
    """KHÓA (F13): subtree export SẠCH squashed (KHÔNG full-history `git subtree split` trần),
    allowlist kit-only path, NDA denylist hook chặn file mentor/rubric."""
    script = ROOT / "scripts" / "subtree-split.sh"
    allowlist = ROOT / ".subtree-allowlist"
    denylist_hook = ROOT / "scripts" / "nda-denylist.sh"

    assert script.exists(), "scripts/subtree-split.sh must exist (F13)"
    assert allowlist.exists(), ".subtree-allowlist must exist (F13)"
    assert denylist_hook.exists(), "scripts/nda-denylist.sh must exist (F13 pre-commit guard)"

    script_text = script.read_text()
    # Must NOT be a bare, un-squashed `git subtree split` (full-history leak risk) — either it
    # passes --squash explicitly, or it avoids `git subtree split` entirely (snapshot-copy +
    # fresh git init, which is squashed by construction: exactly 1 commit).
    bare_subtree_split = re.search(r"git\s+subtree\s+split(?!.*--squash)", script_text)
    if bare_subtree_split and "--squash" not in script_text:
        raise AssertionError(
            "subtree-split.sh must not run a bare `git subtree split` without --squash "
            "(full history would replay every commit that touched this path, F13)"
        )
    assert "git init" in script_text or "--squash" in script_text, (
        "subtree-split.sh must build a squashed export: either a fresh `git init` snapshot-copy, "
        "or `git subtree split --squash`"
    )
    # A squashed snapshot-copy export must produce exactly one commit.
    assert re.search(r"git commit", script_text), "subtree-split.sh must commit the squashed snapshot"

    denylist_text = denylist_hook.read_text()
    for keyword in ("mentor", "rubric"):
        assert keyword in denylist_text.lower(), f"nda-denylist.sh must guard against '{keyword}' files"

    pre_commit_config = (ROOT / ".pre-commit-config.yaml").read_text()
    assert "nda-denylist" in pre_commit_config, ".pre-commit-config.yaml must wire the nda-denylist hook"


def test_subtree_export_runs_and_is_clean(tmp_path: Path) -> None:
    """KHÓA (F13, EXECUTION — not just grep): actually RUN subtree-split.sh and assert the export
    RECURSED the source tree (catches the `rsync --files-from` cancels-implied-`-r` bug that
    grep-only tests miss), stayed CLEAN (no node_modules/dist/cache), shipped docs, and is
    squashed to exactly 1 commit. Dual-review catch (@code-reviewer HIGH)."""
    script = ROOT / "scripts" / "subtree-split.sh"
    export_dir = tmp_path / "export"
    proc = _run(["bash", str(script), str(export_dir)])
    assert proc.returncode == 0, f"subtree-split.sh failed:\n{proc.stdout}\n{proc.stderr}"
    # tree recursed — the -r bug shipped an EMPTY packages/ (only top-level files copied)
    pkg_pyproject = export_dir / "packages" / "contracts" / "pyproject.toml"
    assert pkg_pyproject.is_file(), "export missing package source (rsync -r regression)"
    assert (export_dir / "apps" / "studio" / "src" / "studio_app" / "app.py").is_file(), "export missing app source"
    assert (export_dir / "docs" / "ONBOARDING.md").is_file(), "export must ship docs/ (allowlist)"
    # clean — no build/cache artifacts smuggled into the 'clean' export
    assert not list(export_dir.rglob("node_modules")), "node_modules must never enter the clean export"
    assert not list(export_dir.rglob("__pycache__")), "__pycache__ must not enter the export"
    # squashed — exactly 1 commit, no source history to archaeology through
    count = _run(["git", "-C", str(export_dir), "rev-list", "--count", "HEAD"])
    assert count.stdout.strip() == "1", f"export must be squashed to 1 commit, got {count.stdout!r}"


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
