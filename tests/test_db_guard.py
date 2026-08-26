"""Chốt an toàn DSN ở `conftest.py` gốc (F11) — hàng rào duy nhất giữa suite test và một database
thật.

Suite này `TRUNCATE` mọi bảng trong cả 5 schema trước mỗi bài (`_truncate_all`). Chốt sai nghĩa là
mất dữ liệu, không phải một bài đỏ. Đó là lý do nó có bài riêng, và là lý do bài này kiểm cả nhánh
**cho qua** lẫn nhánh **chặn** — một chốt luôn-chặn cũng vô dụng y như một chốt luôn-cho-qua.

Ca `studio_demo` bên dưới là ca đã xảy ra thật: `studio_demo` chạy trên CÙNG cổng 5433 với
`studio_test` (database riêng, dựng ra chính để dữ liệu demo sống sót qua suite). Với điều kiện
`or` cũ, DSN trỏ vào nó đi lọt chốt vì đúng cổng, rồi suite xoá sạch.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Nạp `conftest.py` gốc kit theo ĐƯỜNG DẪN TƯỜNG MINH, không `from conftest import ...`.
#
# `tests/` không phải package (không có `__init__.py`), nên pytest chèn chính thư mục chứa file test
# vào `sys.path` — và trong một lượt chạy cả workspace thì `apps/studio/tests/` cũng được chèn y
# hệt. Tên module `conftest` khi đó bị tranh chấp, và bên nào vào `sys.modules` trước thì thắng:
#
#     ImportError: cannot import name 'TEST_DB_NAME' from 'conftest'
#       (/…/apps/studio/tests/conftest.py)
#
# Bài này XANH khi chạy riêng file và ĐỎ khi chạy cả suite — và CI không thấy, vì job
# `test (root, tests)` chỉ chạy `tests/`, ở đó không có conftest nào tranh chấp. Nạp theo đường dẫn
# thì không phụ thuộc `sys.path` nữa, nên không còn phụ thuộc thứ tự thu thập.
_ROOT_CONFTEST = Path(__file__).resolve().parents[1] / "conftest.py"
_spec = importlib.util.spec_from_file_location("kit_root_conftest", _ROOT_CONFTEST)
assert _spec is not None and _spec.loader is not None
_root_conftest = importlib.util.module_from_spec(_spec)
sys.modules["kit_root_conftest"] = _root_conftest
_spec.loader.exec_module(_root_conftest)

TEST_DB_NAME = _root_conftest.TEST_DB_NAME
TEST_DB_PORT = _root_conftest.TEST_DB_PORT
guard_admin_dsn = _root_conftest.guard_admin_dsn

_OK = f"postgresql://studio_owner:changeme@127.0.0.1:{TEST_DB_PORT}/{TEST_DB_NAME}"


def test_correct_dsn_passes() -> None:
    """Nhánh cho qua. Thiếu bài này, đổi chốt thành `raise` vô điều kiện vẫn xanh mọi bài khác."""
    guard_admin_dsn(_OK)


def test_no_dsn_configured_passes() -> None:
    """Không khai DSN nào ⇒ không chặn: fixture từng bài sẽ tự `skip`. Chặn ở đây sẽ làm mọi lượt
    chạy không-DB (lint, test thuần) đỏ vì một lý do không liên quan."""
    guard_admin_dsn(None)
    guard_admin_dsn("")


def test_demo_database_on_the_same_port_is_REFUSED() -> None:
    """Bài trung tâm của file.

    `studio_demo` đúng cổng 5433 nhưng KHÁC database. Điều kiện cũ (`not (port_ok or dbname_ok)`)
    cho nó đi lọt vì vế cổng đã đúng — và `_truncate_all` xoá sạch dữ liệu demo. Đây là sự cố đã
    xảy ra, không phải giả định."""
    with pytest.raises(pytest.UsageError) as raised:
        guard_admin_dsn(f"postgresql://studio_owner:changeme@127.0.0.1:{TEST_DB_PORT}/studio_demo")
    assert "studio_demo" in str(raised.value), "thông điệp phải nêu đích danh database bị từ chối"


def test_right_dbname_on_the_wrong_port_is_REFUSED() -> None:
    """Vế đối xứng: cổng 5432 là stack dev (`docker-compose.yml`), và một database TÊN
    `studio_test` nằm ở đó vẫn là database của người khác. Điều kiện cũ cũng cho ca này lọt."""
    with pytest.raises(pytest.UsageError):
        guard_admin_dsn(f"postgresql://studio_owner:changeme@127.0.0.1:5432/{TEST_DB_NAME}")


def test_neither_half_matches_is_REFUSED() -> None:
    """Ca duy nhất mà điều kiện cũ đã chặn đúng — giữ lại để bản vá không đánh mất nó."""
    with pytest.raises(pytest.UsageError):
        guard_admin_dsn("postgresql://postgres:postgres@db.cong-ty.internal:5432/production")


def test_error_message_names_both_halves() -> None:
    """Người đọc lỗi này đang bị chặn giữa chừng, và thứ họ cần là biết SỬA GÌ — nên thông điệp
    phải nêu cả cổng lẫn tên database mong đợi, kèm giá trị thật họ vừa truyền."""
    with pytest.raises(pytest.UsageError) as raised:
        guard_admin_dsn("postgresql://u:p@127.0.0.1:5432/studio_demo")
    message = str(raised.value)
    assert str(TEST_DB_PORT) in message
    assert TEST_DB_NAME in message
    assert "5432" in message and "studio_demo" in message


def test_this_module_loaded_the_KIT_ROOT_conftest_not_another_one() -> None:
    """Khẳng định ĐÚNG FILE NÀO đã được nạp, thay vì tin vào `sys.path`."""
    loaded_from = _root_conftest.__file__
    assert loaded_from is not None, "module nạp bằng importlib phải có __file__"
    assert Path(loaded_from).resolve() == _ROOT_CONFTEST
    assert _ROOT_CONFTEST.parent.name != "tests", "phải là conftest ở GỐC kit, không phải trong tests/"


def test_loading_still_works_when_a_RIVAL_conftest_shadows_the_name() -> None:
    """Tái lập **đúng** va chạm đã xảy ra, ngay trong tiến trình này.

    Bài trên một mình chưa đủ: nó xanh cả khi chạy đơn lẻ, nên nó chứng minh "lần này nạp đúng file"
    chứ không chứng minh "nạp đúng file **kể cả khi** có kẻ tranh chấp tên" (nhận xét review
    kit#245, TranBaDat2607).

    Ở đây dựng lại đúng điều kiện gây lỗi: đặt `apps/studio/tests` lên ĐẦU `sys.path` và bơm sẵn
    một module tên `conftest` trỏ vào file của nó — tức trạng thái mà một lượt chạy cả workspace
    tạo ra. Rồi nạp lại conftest gốc theo cùng cách module này dùng, và đòi vẫn ra đúng file gốc.

    Với `from conftest import ...` cũ, đúng trạng thái này cho `ImportError: cannot import name
    'TEST_DB_NAME' from 'conftest'`."""
    rival_dir = _ROOT_CONFTEST.parent / "apps" / "studio" / "tests"
    rival_conftest = rival_dir / "conftest.py"
    if not rival_conftest.exists():
        pytest.skip("không có apps/studio/tests/conftest.py để dựng va chạm")

    saved_path = list(sys.path)
    saved_module = sys.modules.get("conftest")
    try:
        sys.path.insert(0, str(rival_dir))
        rival_spec = importlib.util.spec_from_file_location("conftest", rival_conftest)
        assert rival_spec is not None and rival_spec.loader is not None
        rival = importlib.util.module_from_spec(rival_spec)
        sys.modules["conftest"] = rival
        rival_spec.loader.exec_module(rival)

        assert not hasattr(rival, "TEST_DB_NAME"), (
            "fixture của bài này hỏng: conftest đối thủ phải KHÔNG có TEST_DB_NAME, "
            "nếu không thì va chạm không tái lập được"
        )

        spec = importlib.util.spec_from_file_location("kit_root_conftest_probe", _ROOT_CONFTEST)
        assert spec is not None and spec.loader is not None
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)

        assert probe.TEST_DB_NAME == TEST_DB_NAME
        assert probe.TEST_DB_PORT == TEST_DB_PORT
    finally:
        sys.path[:] = saved_path
        if saved_module is None:
            sys.modules.pop("conftest", None)
        else:
            sys.modules["conftest"] = saved_module
