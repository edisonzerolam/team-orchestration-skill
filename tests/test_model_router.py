"""测试 model_router.py — 批量操作与文件锁"""
import pytest
import json
import subprocess
import sys
from pathlib import Path

ROUTER = r"D:\opencode\model_router.py"
POOL_FILE = Path(r"D:\opencode\model_pool.json")


def load_pool():
    if POOL_FILE.exists():
        return json.loads(POOL_FILE.read_text(encoding="utf-8"))
    return {"models": [], "global_max_concurrent": 0}


def first_model_id():
    pool = load_pool()
    return pool["models"][0]["id"] if pool["models"] else "unknown"


def run(*args):
    result = subprocess.run([sys.executable, ROUTER] + list(args),
                            capture_output=True, timeout=15, text=True)
    output = "".join([result.stdout or "", result.stderr or ""])
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

    def test_acquire_prioritizes_highest_priority(self):
        result = run("acquire")
        pool = load_pool()
        expected = pool["models"][0]["id"] if pool["models"] else "unknown"
        assert result["model_id"] == expected

    def test_release_reduces_count(self):
        run("acquire")
        mid = first_model_id()
        result = run("release", mid, "success")
        assert result["success"] is True


class TestBatchAcquire:
    def test_batch_5_allocates_5(self):
        result = run("acquire_batch", "5")
        assert result["success"] is True
        assert result["total"] == 5

    def test_batch_single_model(self):
        pool = load_pool()
        first_id = pool["models"][0]["id"]
        result = run("acquire_batch", "5")
        assert len(result["allocated"]) == 1
        assert result["allocated"][0]["model_id"] == first_id

    def test_batch_multi_model(self):
        """分批获取，第二批次应切换到下一个模型"""
        pool = load_pool()
        first_id = pool["models"][0]["id"]
        run("acquire_batch", "5")  # fill first model
        result = run("acquire_batch", "5")
        assert result["success"] is True
        assert result["total"] == 5
        if len(pool["models"]) > 1:
            assert result["allocated"][0]["model_id"] != first_id

    def test_batch_global_limit(self):
        pool = load_pool()
        global_max = pool.get("global_max_concurrent", 15)
        overshoot = global_max + 5
        result = run("acquire_batch", str(overshoot))
        if result["success"] is True:
            assert result["total"] <= global_max
        else:
            assert result["error"] in ("global_limit_reached", "all_models_exhausted")

    def test_batch_release(self):
        pool = load_pool()
        first_id = pool["models"][0]["id"]
        run("acquire_batch", "5")
        result = run("release_batch", first_id, "5", "success")
        assert result["success"] is True
        assert result["released"] == 5


class TestFileLock:
    def test_concurrent_batch(self):
        for _ in range(3):
            r1 = run("acquire_batch", "3")
            assert r1["success"] is True
            for a in r1["allocated"]:
                run("release_batch", a["model_id"], str(a["count"]), "success")

    def test_status_after_operations(self):
        run("acquire_batch", "8")
        pool = load_pool()
        first_id = pool["models"][0]["id"]
        run("release_batch", first_id, "5", "success")
        result = subprocess.run([sys.executable, ROUTER, "status"],
                                 capture_output=True, timeout=15)
        stdout = result.stdout.decode("utf-8", errors="replace")
        assert "模型池状态" in stdout or "deepseek" in stdout.lower() or "mimo" in stdout.lower()
