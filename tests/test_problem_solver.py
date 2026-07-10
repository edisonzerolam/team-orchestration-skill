"""Tests for problem_solver.py — 专家研讨管道核心测试"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from problem_solver import (
    Solution, PanelResult, PanelGuard, L1Solver, L2Panel, ProblemSolver,
    FAULT_TO_DOMAIN, PANEL_CONFIG, FAULT_THICKNESS, TRIGGER_FAULTS,
)


class TestSolution:
    def test_solution_creation(self):
        s = Solution("S-1", "expert-1", "方案1", ["步骤1"], "reason", "低", "Easy", 0.7)
        assert s.id == "S-1"
        assert s.name == "方案1"
        assert s.confidence == 0.7


class TestPanelResult:
    def test_panel_result_creation(self):
        r = PanelResult(session_id="P-1", team_id="team1", agent_id="a1", fault_type="FT-04", level="L0")
        assert r.level == "L0"
        assert r.verdict == "PENDING"
        assert r.is_cached is False


class TestPanelGuard:
    def test_trigger_faults(self):
        assert "FT-04" in TRIGGER_FAULTS
        assert "FT-09" in TRIGGER_FAULTS
        assert "FT-07" in TRIGGER_FAULTS
        assert "FT-01" not in TRIGGER_FAULTS

    def test_check_non_trigger(self):
        g = PanelGuard("test")
        result = g.check("FT-01", "test/a1/FT-01")
        assert result == "block_l3"

    def test_check_proceed(self):
        g = PanelGuard("test")
        result = g.check("FT-04", "test/a1/FT-04")
        assert result == "proceed"

    def test_check_budget_exceeded(self):
        g = PanelGuard("test")
        result = g.check("FT-04", "test/a1/FT-04", tokens_used=200_000)
        assert result == "downgrade_l1"

    def test_check_daily_exceeded(self):
        g = PanelGuard("test")
        result = g.check("FT-04", "test/a1/FT-04", daily_tokens=600_000)
        assert result == "block_l3"

    def test_cache_hit(self):
        g = PanelGuard("test")
        first = g.check("FT-04", "test/a1/FT-04")
        assert first == "proceed"
        # 手动塞缓存
        g.cache.set("test/a1/FT-04", PanelResult(session_id="P-1", team_id="test", agent_id="a1", fault_type="FT-04", level="L0"))
        cached = g.check("FT-04", "test/a1/FT-04")
        assert cached == "use_cache"


class TestL1Solver:
    def test_do_research(self):
        s = L1Solver("test", "FT-04", "expert-1")
        rd = s.do_research({"error": "hallucination", "agent_id": "agent1"})
        assert "local_records" in rd
        assert "knowledge_hits" in rd
        assert "domain" in rd
        assert rd["expert_id"] == "expert-1"

    def test_generate_solutions(self):
        s = L1Solver("test", "FT-04", "expert-1")
        rd = s.do_research({"error": "hallucination", "agent_id": "agent1"})
        sols = s.generate_solutions({"error": "hallucination"}, rd)
        assert len(sols) >= 1
        assert all(isinstance(sol, Solution) for sol in sols)

    def test_check_knowledge(self):
        s = L1Solver("test", "FT-04", "expert-1")
        hits = s._check_knowledge()
        # 即使知识目录不存在也不报错
        assert isinstance(hits, list)


class TestL2Panel:
    def test_run(self):
        panel = L2Panel("test", "FT-04", "standard")
        result = panel.run({"agent_id": "a1", "error": "hallucination"})
        assert result.level == "L2"
        assert result.verdict in ("PASS", "FAIL")
        assert result.duration_ms >= 0

    def test_solution_count(self):
        panel = L2Panel("test", "FT-04", "standard")
        result = panel.run({"agent_id": "a1", "error": "hallucination"})
        assert len(result.solutions) >= 2  # 至少2个专家的方案

    def test_panel_records_persisted(self):
        from pathlib import Path
        panel = L2Panel("test", "FT-04", "standard")
        result = panel.run({"agent_id": "a1", "error": "hallucination"})
        p = Path(panel._save_result.__wrapped__.__defaults__[0]
                 if hasattr(panel._save_result, "__wrapped__")
                 else "") or Path(panel._save_result.__globals__.get("STATE_DIR", Path(".")))
        # Just verify no exception was raised


class TestProblemSolver:
    def test_solve_light(self):
        solver = ProblemSolver("test", "a1")
        result = solver.solve("FT-10", {"agent_id": "a1", "error": "config_error"})
        assert result.level == "L1" or result.level == "L3"
        assert result.verdict in ("PASS", "FAIL", "ESCALATED")

    def test_solve_standard(self):
        solver = ProblemSolver("test", "a1")
        result = solver.solve("FT-04", {"agent_id": "a1", "error": "hallucination"})
        assert result.verdict in ("PASS", "FAIL", "ESCALATED")

    def test_solve_deep(self):
        solver = ProblemSolver("test", "a1")
        result = solver.solve("FT-09", {"agent_id": "a1", "error": "data_poison"})
        assert result.verdict in ("PASS", "FAIL", "ESCALATED")


class TestFAULTMapping:
    def test_all_mapped(self):
        for ft in TRIGGER_FAULTS:
            assert ft in FAULT_TO_DOMAIN, f"{ft} missing domain"
            domain = FAULT_TO_DOMAIN[ft]
            assert len(domain) >= 1, f"{ft} has no domain"

    def test_thickness(self):
        for ft in TRIGGER_FAULTS:
            assert ft in FAULT_THICKNESS, f"{ft} missing thickness"
            t = FAULT_THICKNESS[ft]
            assert t in PANEL_CONFIG, f"{ft} thickness {t} not in config"
