"""测试 failure-analyzer.py — 失败模式聚合报表"""
import importlib.util
import json
import pathlib
import sys
import pytest

_FA_PATH = str(pathlib.Path(__file__).parent.parent / "scripts" / "failure-analyzer.py")
_spec = importlib.util.spec_from_file_location("failure_analyzer", _FA_PATH)
fa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fa)

FAKE_RECORDS = [
    {"fault_type": "FT-01", "action": "restart", "target": "agent-a", "timestamp": 1700000000},
    {"fault_type": "FT-01", "action": "restart", "target": "agent-a", "timestamp": 1700000100},
    {"fault_type": "FT-02", "action": "escalate", "target": "agent-b", "timestamp": 1700000200},
    {"fault_type": "FT-03", "action": "restart", "target": "agent-c", "timestamp": 1700000300},
    {"fault_type": "FT-01", "action": "restart", "target": "agent-a", "timestamp": 1700000400},
]


@pytest.fixture(autouse=True)
def _mock_dir(monkeypatch, tmp_path):
    d = tmp_path / "repair-records"
    d.mkdir(parents=True)
    (d / "test-team.json").write_text(json.dumps(FAKE_RECORDS), encoding="utf-8")
    monkeypatch.setattr(fa, "REPAIR_DIR", d)


class TestLoadAll:
    def test_loads_all(self):
        records = fa.load_all()
        assert len(records) == 5
        assert all(r.get("_source") for r in records)

    def test_load_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(fa, "REPAIR_DIR", tmp_path / "empty")
        assert fa.load_all() == []


class TestByType:
    def test_grouping(self):
        r = fa._report_by_type(FAKE_RECORDS)
        assert r["total"] == 5
        types = {t["code"]: t for t in r["types"]}
        assert types["FT-01"]["count"] == 3
        assert types["FT-02"]["count"] == 1
        assert types["FT-03"]["count"] == 1

    def test_percentage(self):
        r = fa._report_by_type(FAKE_RECORDS)
        ft01 = next(t for t in r["types"] if t["code"] == "FT-01")
        assert ft01["pct"] == 60.0


class TestByAgent:
    def test_grouping(self):
        r = fa._report_by_agent(FAKE_RECORDS)
        assert r["total"] == 5
        agents = {a["agent"]: a for a in r["agents"]}
        assert agents["agent-a"]["total_failures"] == 3
        assert agents["agent-b"]["total_failures"] == 1
        assert len(agents["agent-a"]["top_types"]) == 1
        assert agents["agent-a"]["top_types"][0]["type"] == "FT-01"

    def test_empty(self):
        r = fa._report_by_agent([])
        assert r["total"] == 0
        assert r["agents"] == []


class TestTimeline:
    def test_daily_aggregation(self):
        r = fa._report_timeline(FAKE_RECORDS)
        assert r["total"] == 5
        assert len(r["daily"]) >= 1
        total_counted = sum(d["count"] for d in r["daily"])
        assert total_counted == 5

    def test_empty(self):
        r = fa._report_timeline([])
        assert r["total"] == 0
        assert r["daily"] == []


class TestSummary:
    def test_full_report(self):
        r = fa.summary()
        assert "total_records" in r
        assert r["total_records"] == 5
        assert "by_type" in r
        assert "by_agent" in r
        assert "timeline" in r
        assert "generated_at" in r
