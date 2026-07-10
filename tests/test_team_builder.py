"""测试 team_builder.py — 团队构建器（match→crop 链路）"""
import pytest
from scripts import team_builder


class TestBuildTeam:
    def test_build_team_analysis(self):
        result = team_builder.build_team(
            task="分析腾讯股票",
            subtasks=[{"type": "analysis_judgment"}, {"type": "information_retrieval"}],
            task_type="analysis_judgment",
        )
        assert "team_name" in result
        assert len(result["agents"]) > 0
        assert result["mode"] in ("standard", "economy", "no_crop", "no_match")

    def test_build_team_creation(self):
        result = team_builder.build_team(
            task="写一篇关于AI的文章",
            subtasks=[{"type": "creation_generation"}],
            task_type="creation_generation",
        )
        assert "team_name" in result
        assert result["token_estimate"] > 0

    def test_build_team_force_team(self):
        result = team_builder.build_team(
            task="测试任务",
            force_team="investment-masters-team",
        )
        assert result["team_name"] == "investment-masters-team"
        assert len(result["agents"]) > 0

    def test_build_team_empty_subtasks(self):
        result = team_builder.build_team(
            task="测试",
            subtasks=[],
        )
        assert result["mode"] in ("standard", "economy", "no_crop", "no_match")

    def test_build_team_token_estimate(self):
        result = team_builder.build_team(
            task="简单任务",
            subtasks=[{"type": "decision_execution"}],
        )
        assert result["token_estimate"] > 0

    def test_build_team_from_spec(self):
        spec = {
            "task": "分析茅台",
            "subtasks": [{"type": "analysis_judgment"}, {"type": "information_retrieval"}],
            "task_type": "analysis_judgment",
        }
        result = team_builder.build_team_from_spec(spec)
        assert result["team_name"] != ""


class TestBuildAndRun:
    def test_build_and_run_returns_plan(self):
        decomposition = {
            "subtasks": [{"type": "analysis_judgment"}, {"type": "information_retrieval"}],
            "domains": ["finance"],
            "pi_types": ["analysis_judgment"],
            "main_type": "analysis_judgment",
        }
        result = team_builder.build_and_run("测试任务", decomposition)
        assert "team_name" in result
        assert "execution_plan" in result

    def test_build_and_run_empty_subtasks(self):
        decomposition = {"subtasks": [], "domains": [], "pi_types": [], "main_type": ""}
        result = team_builder.build_and_run("空任务", decomposition)
        assert isinstance(result["execution_plan"], list)


class TestOrchestratorIntegration:
    def test_orchestrator_uses_build_team(self):
        from scripts import orchestrator as orch
        o = orch.NexusOrchestrator()
        r = o.run("分析股票市场趋势")
        assert r["status"] in ("PASS", "PARTIAL", "CLARIFICATION_NEEDED")
        if r["status"] != "CLARIFICATION_NEEDED":
            assert hasattr(o, "team_result")
