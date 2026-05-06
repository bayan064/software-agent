import builtins
from types import SimpleNamespace

from tools.file_tools import save_code
from tools.executor import run_pytest


def test_save_code_success(tmp_path):
    test_path = tmp_path / "nested" / "hello.py"
    content = "print('hello')"

    assert save_code(content, str(test_path)) is True
    assert test_path.exists()
    assert test_path.read_text(encoding="utf-8") == content


def test_save_code_failure(monkeypatch, tmp_path):
    def raise_io_error(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(builtins, "open", raise_io_error)

    test_path = tmp_path / "fail.py"
    assert save_code("print('x')", str(test_path)) is False


def test_run_pytest_logic(monkeypatch):
    fake_output = "collected 2 items\n\nfoo.py .F\n\n1 passed, 1 failed in 0.01s\n"

    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout=fake_output, stderr="", returncode=1)

    monkeypatch.setattr("tools.executor.subprocess.run", fake_run)

    result = run_pytest("fake_test.py")

    assert result["passed"] == 1
    assert result["failed"] == 1
    assert "1 passed" in result["output"]


def test_run_pytest_crash(monkeypatch):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout="", stderr="Internal Error", returncode=2)

    monkeypatch.setattr("tools.executor.subprocess.run", fake_run)

    result = run_pytest("fake_test.py")

    assert result["passed"] == 0
    assert result["failed"] == 1
    assert "Internal Error" in result["output"]