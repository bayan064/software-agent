import builtins
from types import SimpleNamespace

from tools.file_tools import save_code
# 将 run_pytest 改为 run_tests
from tools.executor import run_tests


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


# 测试 Python (pytest) 运行逻辑
def test_run_tests_python(monkeypatch):
    fake_output = "collected 2 items\n\nfoo.py .F\n\n1 passed, 1 failed in 0.01s\n"

    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout=fake_output, stderr="", returncode=1)

    monkeypatch.setattr("tools.executor.subprocess.run", fake_run)

    # 传入 language="Python" 进行测试
    result = run_tests("fake_test.py", language="Python")

    assert result["passed"] == 1
    assert result["failed"] == 1
    assert "1 passed" in result["output"]


# 测试 Java (JUnit) 运行逻辑 (预留测试用例)
def test_run_tests_java(monkeypatch):
    fake_output = "Thanks for using JUnit\n[  2 tests successful ]\n[  0 tests failed ]\n"

    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout=fake_output, stderr="", returncode=0)

    monkeypatch.setattr("tools.executor.subprocess.run", fake_run)

    # 传入 language="Java" 进行测试
    result = run_tests("FakeTest.java", language="Java")

    assert result["returncode"] == 0
    assert "successful" in result["output"]


def test_run_tests_crash(monkeypatch):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout="", stderr="Internal Error", returncode=2)

    monkeypatch.setattr("tools.executor.subprocess.run", fake_run)

    # 默认或指定语言崩溃测试
    result = run_tests("fake_test.py", language="Python")

    assert result["passed"] == 0
    assert result["failed"] == 1
    assert "Internal Error" in result["output"]
