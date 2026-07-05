"""测试 path-selector.py — 执行路径选择器"""
import pytest
import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "scripts"
spec = importlib.util.spec_from_file_location("path_selector", str(SCRIPTS_DIR / "path-selector.py"))
ps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ps)


def make_match(name, score, agent_names=None, agent_count=0):
    return {"name": name, "score": score, "agent_names": agent_names or [name], "agent_count": agent_count}


class TestComplexityLevel:
    def test_parse_full(self):
        assert ps.ComplexityLevel.parse("L1-简单") == 1

    def test_parse_short(self):
        assert ps.ComplexityLevel.parse("L3") == 3

    def test_parse_unknown(self):
        assert ps.ComplexityLevel.parse("L5") == 0

    def test_le_true(self):
        assert ps.ComplexityLevel.le("L1", "L3")

    def test_le_false(self):
        assert not ps.ComplexityLevel.le("L3", "L1")

    def test_ge_true(self):
        assert ps.ComplexityLevel.ge("L3", "L1")

    def test_ge_false(self):
        assert not ps.ComplexityLevel.ge("L1", "L3")


class TestTemplateMatching:
    def test_match_engineering(self):
        assert ps.find_matching_template(["02-Engineering"]) == "software-team"

    def test_match_finance(self):
        assert ps.find_matching_template(["08-FinanceInvestment"]) == "investment-masters"

    def test_no_match(self):
        assert ps.find_matching_template(["99-Unknown"]) is None

    def test_match_by_team_name(self):
        assert ps.find_matching_template([], ["software-team"]) == "software-team"

    def test_first_match_wins(self):
        assert ps.find_matching_template(["02-Engineering", "08-FinanceInvestment"]) == "software-team"


class TestPathSelection:
    def test_direct_call_high_score_low_complexity(self):
        matches = [make_match("analyst", 0.9)]
        result = ps.select_path(matches, ["08-FinanceInvestment"], "L1-简单")
        assert result["selected_path"] == "direct_call"

    def test_team_path_high_complexity(self):
        matches = [make_match("research-team", 0.7)]
        result = ps.select_path(matches, ["04-DataAI"], "L3-复杂")
        assert result["selected_path"] == "team_path"

    def test_team_path_multi_domain(self):
        matches = [make_match("consultant", 0.6)]
        result = ps.select_path(matches, ["08-FinanceInvestment", "04-DataAI"], "L2-中等")
        assert result["selected_path"] == "team_path"

    def test_fast_path_template_match(self):
        matches = [make_match("software-team", 0.6)]
        result = ps.select_path(matches, ["02-Engineering"], "L2-中等",
                                available_templates=["software-team"])
        assert result["selected_path"] == "fast_path"

    def test_fallback_low_score(self):
        matches = [make_match("some-expert", 0.3)]
        result = ps.select_path(matches, ["99-Unknown"], "L1-简单")
        assert result["selected_path"] == "fallback"

    def test_direct_call_beats_team_path(self):
        """测试互斥：直调路径优先级高于团队路径"""
        matches = [make_match("analyst", 0.9)]
        result = ps.select_path(matches, ["08-FinanceInvestment"], "L2-中等")
        assert result["selected_path"] == "direct_call"

    def test_team_beats_fast_path(self):
        """测试互斥：团队路径优先级高于快速路径"""
        matches = [make_match("research-team", 0.7)]
        result = ps.select_path(matches, ["04-DataAI", "02-Engineering"], "L3-复杂",
                                available_templates=["research-team", "software-team"])
        assert result["selected_path"] == "team_path"

    def test_confidence_in_range(self):
        matches = [make_match("some-expert", 0.5)]
        result = ps.select_path(matches, ["99-Unknown"], "L1-简单")
        assert 0 <= result["confidence"] <= 1

    def test_debug_info_included(self):
        matches = [make_match("expert", 0.9)]
        result = ps.select_path(matches, ["08-FinanceInvestment"], "L1-简单")
        assert "debug" in result
        assert "top_score" in result["debug"]
        assert "complexity" in result["debug"]

    def test_empty_matches_fallback(self):
        result = ps.select_path([], ["99-Unknown"], "L1-简单")
        assert result["selected_path"] == "fallback"

    def test_integration_with_full_match(self):
        """模拟真实场景：A股分析"""
        matches = [
            make_match("a-share-analysis", 0.78, agent_names=["a-share-advisor", "stock-researcher"], agent_count=8),
            make_match("investment-masters-team", 0.7, agent_count=22),
        ]
        result = ps.select_path(matches, ["08-FinanceInvestment"], "L3-复杂",
                                available_templates=["a-share-analysis"])
        # L3 复杂度应该走团队路径
        assert result["selected_path"] in ("team_path", "fast_path")
