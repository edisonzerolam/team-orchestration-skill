"""测试 concurrency_check.py — 并发参考数据检查器（v3.9 · TC-20260816-6 补强）

注意：所有测试读写隔离的临时数据文件（monkeypatch cc.DATA_FILE），不污染真实参考数据。
"""
import importlib.util
import json
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "concurrency_check", str(SKILL / "scripts" / "concurrency_check.py")
)
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

# 隔离数据文件：每个测试用独立临时文件
_TMP = Path(tempfile.mkdtemp(prefix="cc-test-"))


def _iso_data():
    cc.DATA_FILE = _TMP / "data.json"
    cc._save({
        "updated_at": "2026-08-16", "max_spawned": 6,
        "max_spawned_history": [6, 5, 6],
        "models": {"default_model": {"official_concurrency": 2500}}
    })


def test_data_file_exists_and_valid():
    _iso_data()
    data = cc._load()
    assert isinstance(data, dict)
    assert "models" in data and "max_spawned" in data


def test_days_since():
    assert cc.days_since("2026-08-16") <= 2  # 近两天
    assert cc.days_since("1970-01-01") > 1000


def test_check_fresh():
    _iso_data()
    r = cc.check()
    assert r["status"] == "fresh"
    assert r["suggested"] >= 1


def test_check_stale_suggests_probe():
    _iso_data()
    d = cc._load()
    d["updated_at"] = "2026-07-01"
    d["max_spawned"] = 6
    cc._save(d)
    r = cc.check()
    assert r["status"] == "stale"
    assert r["days_since"] > 14
    assert r["suggested"] == 7  # max_spawned(6)+1


def test_record_updates_max():
    _iso_data()
    r = cc.record(8)
    assert r["max_spawned"] == 8
    assert 8 in r["history"]
