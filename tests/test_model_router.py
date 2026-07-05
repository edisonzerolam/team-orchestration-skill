"""测试 model_router.py — 批量操作与文件锁"""
import pytest
import json
import subprocess
import sys
from pathlib import Path

ROUTER = str(Path.home() / ".." / ".." / "D:" / "opencode" / "model_router.py").replace("..\\..\\D:", "D:")
# Use direct path
ROUTER = r"D:\opencode\model_router.py"


def run(*args):
    result = subprocess.run([sys.executable, ROUTER] + list(args),
                            capture_output=True, timeout=15, text=True)
    output = "".join([result.stdout or "", result.stderr or ""])
    # Find JSON in output
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"success": False, "raw": output}


@pytest.fixture(autouse=True)
def reset_state():
    run("reset")
    yield
    run("reset")


class TestSingleAcquire:
    def test_acquire_returns_model(self):
        result = run("acquire")
        assert result["success"] is True
        assert "model_id" in result
        assert "agent_type" in result

    def test_acquire_prioritizes_deepseek(self):
        result = run("acquire")
        assert result["model_id"] == "deepseek-v4-flash"

    def test_release_reduces_count(self):
        run("acquire")
        result = run("release", "deepseek-v4-flash", "success")
        assert result["success"] is True


class TestBatchAcquire:
    def test_batch_5_allocates_5(self):
        result = run("acquire_batch", "5")
        assert result["success"] is True
        assert result["total"] == 5

    def test_batch_single_model(self):
        result = run("acquire_batch", "5")
        assert len(result["allocated"]) == 1
        assert result["allocated"][0]["model_id"] == "deepseek-v4-flash"

    def test_batch_multi_model(self):
        run("acquire_batch", "5")  # fill ds
        result = run("acquire_batch", "5")
        assert result["success"] is True
        assert result["total"] == 5
        # Should use mimo-v2.5 (next priority)
        assert result["allocated"][0]["model_id"] == "mimo-v2.5"

    def test_batch_exhausted(self):
        run("acquire_batch", "15")  # fill all
        result = run("acquire_batch", "5")
        assert result["success"] is False
        assert "all_models_exhausted" in result.get("error", "")

    def test_batch_release(self):
        run("acquire_batch", "5")
        result = run("release_batch", "deepseek-v4-flash", "5", "success")
        assert result["success"] is True
        assert result["released"] == 5


class TestFileLock:
    def test_concurrent_batch(self):
        """Simulate concurrent access by running acquire/release in sequence"""
        for _ in range(3):
            r1 = run("acquire_batch", "3")
            assert r1["success"] is True
            for a in r1["allocated"]:
                run("release_batch", a["model_id"], str(a["count"]), "success")

    def test_status_after_operations(self):
        run("acquire_batch", "8")
        run("release_batch", "deepseek-v4-flash", "5", "success")
        result = subprocess.run([sys.executable, ROUTER, "status"],
                                 capture_output=True, timeout=15)
        stdout = result.stdout.decode("utf-8", errors="replace")
        assert "模型池状态" in stdout or "deepseek" in stdout.lower()
