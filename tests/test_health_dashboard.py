"""测试 health-dashboard.py（v2.0 — Prometheus / CB / API）"""
import json
import os
import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))
import health_dashboard as hd


# ── fixture ──────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_globals():
    hd.CB_DIR = pathlib.Path(__file__).parent / "mock_cb"
    hd.REPAIR_DIR = pathlib.Path(__file__).parent / "mock_repair"
    hd.TEAMS_DIR = pathlib.Path(__file__).parent / "mock_teams"
    yield
    for d in [hd.CB_DIR, hd.REPAIR_DIR, hd.TEAMS_DIR]:
        if d.exists():
            for f in d.glob("*.json"):
                f.unlink()
            d.rmdir()


def _write_team(name: str, agents: list[dict]):
    hd.TEAMS_DIR.mkdir(parents=True, exist_ok=True)
    (hd.TEAMS_DIR / f"{name}.json").write_text(
        json.dumps({"name": name, "agents": agents}, ensure_ascii=False), encoding="utf-8")


def _write_cb(name: str, state: str, failures: int = 0, success: int = 0):
    hd.CB_DIR.mkdir(parents=True, exist_ok=True)
    (hd.CB_DIR / f"{name}.json").write_text(
        json.dumps({"name": name, "state": state,
                    "failure_count": failures, "success_count": success,
                    "failure_threshold": 3}, ensure_ascii=False), encoding="utf-8")


def _write_repair(records: list[dict]):
    hd.REPAIR_DIR.mkdir(parents=True, exist_ok=True)
    (hd.REPAIR_DIR / "test-team.json").write_text(
        json.dumps(records, ensure_ascii=False), encoding="utf-8")


# ── Teams ────────────────────────────────────────────────────────────────────────

class TestLoadTeams:
    def test_empty_dir(self):
        assert hd.load_teams() == []

    def test_loads_teams(self):
        _write_team("alpha", [{"name": "a1", "status": "alive"}])
        _write_team("beta", [{"name": "b1", "status": "dead"}])
        teams = hd.load_teams()
        assert len(teams) == 2

    def test_skips_corrupted(self):
        hd.TEAMS_DIR.mkdir(parents=True, exist_ok=True)
        (hd.TEAMS_DIR / "bad.json").write_text("not json", encoding="utf-8")
        assert hd.load_teams() == []


# ── Circuit Breakers ─────────────────────────────────────────────────────────────

class TestCircuitBreakers:
    def test_empty(self):
        assert hd.load_circuit_breakers() == []

    def test_loads_cbs(self):
        _write_cb("svc-a", "CLOSED")
        _write_cb("svc-b", "OPEN", failures=5)
        cbs = hd.load_circuit_breakers()
        assert len(cbs) == 2
        states = {cb["name"]: cb["state"] for cb in cbs}
        assert states["svc-a"] == "CLOSED"
        assert states["svc-b"] == "OPEN"

    def test_cb_state_icon(self):
        icon, cls = hd._cb_state_icon("CLOSED")
        assert "closed" in cls
        icon, cls = hd._cb_state_icon("OPEN")
        assert "open" in cls
        icon, cls = hd._cb_state_icon("HALF_OPEN")
        assert "half-open" in cls
        icon, cls = hd._cb_state_icon("UNKNOWN")
        assert "unknown" in cls


# ── Repair Records ───────────────────────────────────────────────────────────────

class TestRepairRecords:
    def test_empty(self):
        assert hd.load_repair_records() == []

    def test_loads_records(self):
        _write_repair([
            {"fault_type": "FT-01", "action": "restart"},
            {"fault_type": "FT-02", "action": "escalate"},
        ])
        records = hd.load_repair_records()
        assert len(records) == 2
        assert all(r.get("_source") for r in records)


# ── Prometheus Metrics ───────────────────────────────────────────────────────────

class TestMetrics:
    def test_metrics_empty(self):
        metrics = hd.build_metrics([])
        assert "clawteam_team_total 0" in metrics
        assert "clawteam_up 1" in metrics

    def test_metrics_team_counts(self):
        _write_team("t1", [{"name": "a1", "status": "alive"}, {"name": "a2", "status": "dead"}])
        teams = hd.load_teams()
        metrics = hd.build_metrics(teams)
        assert "clawteam_team_total 1" in metrics
        assert "clawteam_agent_alive 1" in metrics
        assert "clawteam_agent_dead 1" in metrics

    def test_metrics_cb_included(self):
        _write_cb("svc-x", "OPEN", failures=3)
        teams = []
        metrics = hd.build_metrics(teams)
        assert 'clawteam_circuit_breaker{name="svc-x",state="OPEN"} 2' in metrics
        assert 'clawteam_circuit_breaker_failures{name="svc-x"} 3' in metrics

    def test_metrics_repair_included(self):
        _write_repair([{"fault_type": "FT-01"}, {"fault_type": "FT-01"}, {"fault_type": "FT-02"}])
        teams = []
        metrics = hd.build_metrics(teams)
        assert 'clawteam_repairs_total{fault_type="FT-01"} 2' in metrics
        assert 'clawteam_repairs_total{fault_type="FT-02"} 1' in metrics
        assert "clawteam_repairs_total_all 3" in metrics

    def test_metrics_format_compliant(self):
        """验证 Prometheus 文本格式合规（不以空格开头，注释正确）"""
        metrics = hd.build_metrics([])
        for line in metrics.strip().split("\n"):
            if line.startswith("#") or line.startswith("clawteam") or line.startswith("# EOF"):
                continue
            pytest.fail(f"非法 Prometheus 行: {line}")


# ── HTML Dashboard ───────────────────────────────────────────────────────────────

class TestHTML:
    def test_html_empty(self):
        html = hd.build_html([])
        assert "<!DOCTYPE html>" in html
        assert "0</div>团队" in html
        assert "Prometheus" in html

    def test_html_includes_cb_section(self):
        _write_cb("svc-a", "CLOSED")
        teams = hd.load_teams()  # returns empty list since no teams written
        html = hd.build_html([])
        assert "熔断器" in html
        assert "名称" in html

    def test_html_includes_failure_section(self):
        _write_repair([{"fault_type": "FT-01", "action": "restart"}])
        html = hd.build_html([])
        assert "失败聚合" in html
        assert "FT-01" in html
        assert "restart" in html

    def test_html_links(self):
        html = hd.build_html([])
        assert "/metrics" in html
        assert "/api/teams" in html
        assert "/api/circuit-breakers" in html
        assert "/api/failures" in html


class TestPromLabel:
    def test_escapes_backslash(self):
        assert hd._prom_label("a\\b") == "a\\\\b"

    def test_escapes_quote(self):
        assert hd._prom_label('a"b') == 'a\\"b'

    def test_escapes_newline(self):
        assert hd._prom_label("a\nb") == "a\\nb"

    def test_plain_string_unchanged(self):
        assert hd._prom_label("hello") == "hello"


class TestHTTPEndpoints:
    """直接测试 handler 响应构造逻辑（无需启动真实 HTTP 服务器）"""

    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self._cb_dir = pathlib.Path(__file__).parent / "mock_cb_http2"
        self._repair_dir = pathlib.Path(__file__).parent / "mock_repair_http2"
        self._teams_dir = pathlib.Path(__file__).parent / "mock_teams_http2"
        hd.CB_DIR = self._cb_dir
        hd.REPAIR_DIR = self._repair_dir
        hd.TEAMS_DIR = self._teams_dir
        self._cb_dir.mkdir(parents=True, exist_ok=True)
        (self._cb_dir / "svc.json").write_text(
            json.dumps({"name": "svc", "state": "CLOSED"}), encoding="utf-8")
        self._repair_dir.mkdir(parents=True, exist_ok=True)
        (self._repair_dir / "team.json").write_text(
            json.dumps([{"fault_type": "FT-01", "action": "restart"}]),
            encoding="utf-8")
        self._teams_dir.mkdir(parents=True, exist_ok=True)
        (self._teams_dir / "t.json").write_text(
            json.dumps({"name": "t1", "agents": [{"name": "a1", "status": "alive"}]}),
            encoding="utf-8")
        yield
        import shutil
        for d in [self._cb_dir, self._repair_dir, self._teams_dir]:
            if d.exists(): shutil.rmtree(str(d))

    def test_metrics_content_via_function(self):
        teams = hd.load_teams()
        metrics = hd.build_metrics(teams)
        assert "clawteam_up 1" in metrics
        assert "clawteam_team_total 1" in metrics

    def test_api_teams_content_via_load(self):
        teams = hd.load_teams()
        assert len(teams) >= 1
        assert any(t.get("name") == "t1" for t in teams)

    def test_api_cb_content_via_load(self):
        cbs = hd.load_circuit_breakers()
        assert len(cbs) >= 1
        assert any("svc" in cb.get("name", "") for cb in cbs)

    def test_api_failures_content_via_load(self):
        records = hd.load_repair_records()
        assert len(records) >= 1
        assert records[0]["fault_type"] == "FT-01"
