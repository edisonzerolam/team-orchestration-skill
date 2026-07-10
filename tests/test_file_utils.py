"""测试 file_utils.py — 原子写入与安全读取"""
import json
import pytest
from pathlib import Path

SKILL_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration"
import importlib.util
spec = importlib.util.spec_from_file_location("fu",
    str(SKILL_DIR / "scripts" / "file_utils.py"))
fu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fu)


class TestAtomicWrite:
    def test_write_and_read_back(self, tmp_path):
        data = {"name": "test", "value": 42}
        p = tmp_path / "test.json"
        fu.atomic_write(p, data)
        assert p.exists()
        loaded = json.loads(p.read_text(encoding="utf-8"))
        assert loaded == data

    def test_atomicity_temp_file_cleaned(self, tmp_path):
        p = tmp_path / "atomic.json"
        fu.atomic_write(p, {"key": "value"})
        # temp files should be cleaned
        temps = list(tmp_path.glob("*.tmp.*"))
        assert len(temps) == 0

    def test_overwrite_existing(self, tmp_path):
        p = tmp_path / "data.json"
        fu.atomic_write(p, {"v": 1})
        fu.atomic_write(p, {"v": 2})
        assert json.loads(p.read_text(encoding="utf-8")) == {"v": 2}


class TestSafeRead:
    def test_read_existing(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text('{"a": 1}', encoding="utf-8")
        assert fu.read_json(p) == {"a": 1}

    def test_read_nonexistent(self, tmp_path):
        result = fu.read_json(tmp_path / "nonexistent.json")
        assert result is None

    def test_read_corrupt(self, tmp_path):
        p = tmp_path / "corrupt.json"
        p.write_text("{invalid json", encoding="utf-8")
        result = fu.read_json(p)
        assert result is None

    def test_read_json_or_empty_nonexistent(self, tmp_path):
        assert fu.read_json_or_empty(tmp_path / "nope.json") == {}

    def test_read_json_or_empty_corrupt(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("nope", encoding="utf-8")
        assert fu.read_json_or_empty(p) == {}


class TestWriteJson:
    def test_write_json_compat(self, tmp_path):
        p = tmp_path / "compat.json"
        fu.write_json(p, {"status": "ok"})
        assert json.loads(p.read_text(encoding="utf-8")) == {"status": "ok"}
