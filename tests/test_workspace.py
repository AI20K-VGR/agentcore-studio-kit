"""Phase 1 — Workspace Foundation gate tests.

These 5 tests lock the workspace contract before any per-quadrant business logic exists
(P2+). They must go RED before the workspace is built and GREEN after `uv lock` + `uv sync`
succeed. See plans/260717-1516-studio-kit-template/phases/phase-1-workspace-foundation.md.
"""

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MEMBERS = (
    "studio_contracts",
    "studio_kb",
    "studio_engine",
    "studio_workbench",
    "studio_evalhub",
    "studio_app",
)


def test_single_lockfile() -> None:
    """KHÓA: đúng 1 uv.lock ở root (KHÔNG lockfile phụ ở member nào)."""
    lockfiles = sorted(p for p in ROOT.rglob("uv.lock") if ".venv" not in p.parts)
    assert lockfiles == [ROOT / "uv.lock"], f"expected exactly 1 uv.lock at repo root, found: {lockfiles}"


def test_all_members_importable() -> None:
    """KHÓA: 6 Python member import được từ 1 venv duy nhất (workspace resolve đúng)."""
    code = "import " + ", ".join(MEMBERS)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"import-smoke failed:\nstdout={result.stdout}\nstderr={result.stderr}"


def test_import_linter_passes() -> None:
    """KHÓA: layers-contract enforce — studio_app (top) > 4 quadrant siblings > studio_contracts (bottom)."""
    result = subprocess.run(
        ["lint-imports"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"lint-imports failed:\nstdout={result.stdout}\nstderr={result.stderr}"


def test_ddl_returns_schema_sql() -> None:
    """KHÓA: mỗi quadrant export ddl() callable trả DDL thật — seam cho P3 aggregator.

    (P1 chốt stub trả ''; sau khi P5/P7/P8 điền thân ddl() ở batch, guard này chuyển sang
    khoá 'ddl() trả CREATE SCHEMA khác rỗng' — vẫn giữ răng: ddl() phải callable + non-empty +
    tạo đúng schema của quadrant.)"""
    import studio_evalhub.schema as evalhub_schema
    import studio_kb.schema as kb_schema
    import studio_workbench.schema as workbench_schema

    expected_schema = {"studio_kb.schema": "kb", "studio_workbench.schema": "wb", "studio_evalhub.schema": "eval"}
    for module in (kb_schema, workbench_schema, evalhub_schema):
        assert callable(module.ddl), f"{module.__name__} must export a callable ddl()"
        sql = module.ddl()
        want = expected_schema[module.__name__]
        assert isinstance(sql, str) and sql.strip(), f"{module.__name__}.ddl() must return non-empty DDL"
        assert "CREATE SCHEMA" in sql.upper(), f"{module.__name__}.ddl() must CREATE its schema"
        assert want in sql, f"{module.__name__}.ddl() must target schema {want!r}"


def test_members_declare_runtime_deps() -> None:
    """KHÓA (F7): kb + app pyproject khai HẾT runtime dep (psycopg/pydantic) NGAY ở P1 — P5-P8 KHÔNG relock."""
    kb_data = tomllib.loads((ROOT / "packages" / "kb" / "pyproject.toml").read_text())
    app_data = tomllib.loads((ROOT / "apps" / "studio" / "pyproject.toml").read_text())

    kb_deps = " ".join(kb_data["project"]["dependencies"])
    app_deps = " ".join(app_data["project"]["dependencies"])

    assert "psycopg" in kb_deps, f"packages/kb pyproject must declare psycopg (F7), got: {kb_deps}"
    assert "psycopg" in app_deps, f"apps/studio pyproject must declare psycopg (F7), got: {app_deps}"
    assert "pydantic" in app_deps, f"apps/studio pyproject must declare pydantic (F7), got: {app_deps}"
    assert "fastapi" in app_deps, f"apps/studio pyproject must declare fastapi (F7), got: {app_deps}"
