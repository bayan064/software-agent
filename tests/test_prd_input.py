import os
import pytest

from tools import prd_runner


def test_run_prd_text_empty():
    with pytest.raises(ValueError):
        prd_runner.run_prd_text("", "out")


def test_run_prd_file_missing(tmp_path):
    missing_file = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        prd_runner.run_prd_file(str(missing_file), str(tmp_path / "out"))


def test_run_prd_text_invokes_agent(tmp_path, monkeypatch):
    output_dir = tmp_path / "out"
    calls = {}

    def fake_invoke(payload):
        calls["payload"] = payload
        return {
            "code": "print('ok')",
            "test_code": "def test_ok():\n    assert True",
            "test_result": {"passed": 1, "failed": 0},
        }

    monkeypatch.setattr(prd_runner.app, "invoke", fake_invoke)

    result = prd_runner.run_prd_text("demo prd", str(output_dir), language="Python")

    assert output_dir.exists()
    assert result["code"] == "print('ok')"
    assert calls["payload"]["requirement"] == "demo prd"
    assert calls["payload"]["output_dir"] == str(output_dir)
    assert calls["payload"]["language"] == "Python"


def test_run_prd_file_invokes_agent_with_txt(monkeypatch, tmp_path):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    prd_file = os.path.join(base_dir, "tests", "prds", "test.txt")
    calls = {}

    with open(prd_file, "r", encoding="utf-8") as f:
        expected_prd = f.read().strip()

    def fake_invoke(payload):
        calls["payload"] = payload
        return {"code": "x", "test_code": "y", "test_result": {}}

    monkeypatch.setattr(prd_runner.app, "invoke", fake_invoke)

    result = prd_runner.run_prd_file(prd_file, str(tmp_path / "out"), language="Java")

    assert result["code"] == "x"
    assert calls["payload"]["requirement"] == expected_prd
