"""`studio_scorer` — role thứ ba, `BYPASSRLS`, cho bộ chấm cross-tenant của evalhub (evalhub#37).

Vì sao role này tồn tại: `app#40` bật `ENABLE`+`FORCE ROW LEVEL SECURITY` trên `obs.trace_events`.
Hai hàm đọc-xuyên-tenant của evalhub (`read_run_unscoped`/`list_runs_all_tenants`) **cố ý** không set
`app.tenant_id` — chúng phải nhìn thấy event của mọi tenant thì `tenant_scope_ok` mới bắt được run mà
node đầu mang tenant A còn node sau mang tenant B. Dưới policy đó, mọi role không `BYPASSRLS` khớp 0
dòng và nhận `[]` **im lặng**.

Hai bài dưới khoá phần **kit kiểm soát được**: file initdb tạo đúng role, đúng thuộc tính, và trên
DB thật thì `BYPASSRLS` chỉ thuộc về role này chứ không lan sang `studio_owner`/`studio_app`.

**Vế còn lại — "role này chỉ có SELECT, và chỉ trên `obs.trace_events`" — được khoá ở
`apps/studio`**, không phải ở đây. Lý do là cơ học chứ không phải sở thích: GRANT phải chạy SAU
`ensure_all_schemas()` (bảng chưa tồn tại lúc initdb), nên nó sống trong
`studio_app.core.schema.grant_scorer_privileges()`; mà CI của kit reconstruct workspace theo **con
trỏ submodule đang ghim**, nên một bài ở đây khẳng định về hàm đó sẽ đỏ cho tới tận lần bump con
trỏ. Bài kiểm quyền đi kèm chính hàm cấp quyền — xem `apps/studio/tests/test_scorer_privileges.py`.

`BYPASSRLS` bỏ qua RLS, nên quyền BẢNG là lưới duy nhất còn lại: nếu role này lỡ được cấp DML hoặc
cấp trên bảng khác thì nó thành cửa hậu đọc-ghi xuyên tenant mà không policy nào chặn được. Đó là lý
do vế kia bắt buộc phải có bài, chứ không phải chỉ ghi trong comment.

Bài chạy trên DB test thật; không có DSN thì fixture `admin_pool` tự skip (conftest gốc kit).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
_ROLES_SQL = ROOT / "docker" / "postgres-init" / "00-roles.sql"


def test_init_sql_khai_studio_scorer_bypassrls() -> None:
    """KHÓA tĩnh: file initdb phải tạo role với ĐÚNG `BYPASSRLS` và ĐÚNG `NOSUPERUSER`.

    Tĩnh chứ không chỉ động, vì bài động dưới đây đọc DB — mà DB có thể đã mang role từ một bản
    cũ hơn của chính file này. Bài tĩnh khoá cái sẽ đến với mọi máy clone sạch.
    """
    sql_text = _ROLES_SQL.read_text(encoding="utf-8")
    assert "CREATE ROLE studio_scorer" in sql_text, "initdb chưa tạo studio_scorer"
    assert "BYPASSRLS LOGIN" in sql_text, "studio_scorer phải có BYPASSRLS"
    assert "CREATE ROLE studio_scorer NOSUPERUSER NOCREATEDB NOCREATEROLE" in sql_text, (
        "studio_scorer phải NOSUPERUSER + NOCREATEDB + NOCREATEROLE — BYPASSRLS là quyền DUY NHẤT "
        "được nới, mọi thứ khác giữ như 2 role kia"
    )
    assert "ALTER ROLE studio_scorer BYPASSRLS" in sql_text, (
        "cần đường thứ hai: role đã tồn tại từ bản cũ của file này thì CREATE bị bỏ qua, "
        "thuộc tính phải được set bằng ALTER — cùng khuôn 'hai đường' của các ddl() quadrant"
    )
    assert "TO studio_owner, studio_app, studio_scorer" in sql_text, "thiếu GRANT CONNECT cho studio_scorer"


async def test_studio_scorer_bypass_duoc_RLS_tren_DB_that(admin_pool: Any) -> None:
    """KHÓA động: trên DB thật, `row_security_active('obs.trace_events')` phải `false` cho
    studio_scorer và `true` cho hai role kia.

    Đây chính là vị từ mà `studio_evalhub.run_report._assert_doc_xuyen_tenant_duoc` hỏi. Bài này
    khoá hai đầu của cùng một hợp đồng gặp nhau: guard bên evalhub hỏi đúng câu, và role bên kit
    trả lời đúng.
    """
    async with admin_pool.connection() as conn:
        cur = await conn.execute(
            "SELECT rolname, rolbypassrls, rolsuper FROM pg_roles "
            "WHERE rolname IN ('studio_owner', 'studio_app', 'studio_scorer') ORDER BY rolname"
        )
        rows = {r[0]: (r[1], r[2]) for r in await cur.fetchall()}

    assert "studio_scorer" in rows, (
        "DB test chưa có studio_scorer — volume có trước thay đổi này thì initdb KHÔNG chạy lại. "
        "Áp tay một lần: docker exec -i <pg> psql -U postgres -d studio_test "
        "< docker/postgres-init/00-roles.sql"
    )
    assert rows["studio_scorer"] == (True, False), "studio_scorer phải BYPASSRLS và KHÔNG superuser"
    assert rows["studio_owner"] == (False, False), "studio_owner KHÔNG được có BYPASSRLS — FORCE RLS phải cắn cả owner"
    assert rows["studio_app"] == (False, False), "studio_app KHÔNG được có BYPASSRLS"
