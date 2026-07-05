"""测试 expert-matcher.py v2 — 4维度加权匹配引擎"""
import json
import pytest
import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "scripts"
spec = importlib.util.spec_from_file_location("expert_matcher", str(SCRIPTS_DIR / "expert-matcher.py"))
em = importlib.util.module_from_spec(spec)
spec.loader.exec_module(em)


class TestLoadExperts:
    def test_load_all_experts_returns_dict(self):
        experts = em.load_all_experts()
        assert isinstance(experts, dict)
        assert len(experts) > 0

    def test_contains_key_teams(self):
        experts = em.load_all_experts()
        assert "investment-masters-team" in experts
        assert "a-share-analysis" in experts
        assert "software-company" in experts

    def test_expert_has_required_fields(self):
        experts = em.load_all_experts()
        exp = experts["investment-masters-team"]
        assert "category_id" in exp
        assert "agent_count" in exp
        assert "agent_names" in exp and len(exp["agent_names"]) > 0
        assert "capabilities" in exp

    def test_expert_has_agent_files(self):
        experts = em.load_all_experts()
        for name, exp in experts.items():
            if exp["agent_count"] == 0:
                continue
            assert len(exp["agent_names"]) == exp["agent_count"]


class TestWeights:
    def test_weights_sum_to_one(self):
        total = em.WEIGHTS["domain"] + em.WEIGHTS["capability"] + em.WEIGHTS["performance"] + em.WEIGHTS["load"]
        assert abs(total - 1.0) < 0.01

    def test_weights_positive(self):
        for k, v in em.WEIGHTS.items():
            assert v > 0, f"Weight {k} must be positive"


class TestThresholds:
    def test_direct_call_threshold(self):
        assert em.THRESHOLDS["direct_call"] > em.THRESHOLDS["team_recommend"]

    def test_thresholds_in_range(self):
        for k, v in em.THRESHOLDS.items():
            assert 0 < v <= 1, f"Threshold {k}={v} out of range"


class TestDomainMatch:
    def test_exact_match(self):
        score = em.domain_match(["08-FinanceInvestment"],
                                {"category_id": "08-FinanceInvestment",
                                 "description_zh": "股票分析", "display_zh": "A股"})
        assert score >= 0.5

    def test_no_match(self):
        score = em.domain_match(["02-Engineering"],
                                {"category_id": "08-FinanceInvestment",
                                 "description_zh": "股票", "display_zh": "A股"})
        assert score == 0.0

    def test_partial_match(self):
        score = em.domain_match(["08-FinanceInvestment", "04-DataAI"],
                                {"category_id": "08-FinanceInvestment",
                                 "description_zh": "股票分析", "display_zh": "A股"})
        assert 0 < score < 1.0

    def test_empty_domains(self):
        score = em.domain_match([], {"category_id": "x", "description_zh": "", "display_zh": ""})
        assert score == 0.0


class TestCapabilityMatch:
    def test_exact_match(self):
        score = em.capability_match(["分析"],
                                    {"capabilities": ["深度分析", "股票研究"], "agent_names": ["analyst"]})
        assert score > 0

    def test_no_match(self):
        score = em.capability_match(["量子计算"],
                                    {"capabilities": ["股票分析"], "agent_names": ["analyst"]})
        assert score == 0.0

    def test_empty_abilities_default(self):
        score = em.capability_match([], {"capabilities": ["股票分析"], "agent_names": ["analyst"]})
        assert score == 0.5


class TestPerformanceScore:
    def test_new_expert(self):
        score = em.performance_score("new-team", {})
        assert score == 0.5

    def test_tracked_expert(self):
        score = em.performance_score("known-team", {"known-team": {"score": 0.8}})
        assert score == 0.8

    def test_score_capped(self):
        score = em.performance_score("high", {"high": {"score": 1.5}})
        assert score <= 1.0


class TestLoadPenalty:
    def test_no_load(self):
        assert em.current_load("test", []) == 0.0

    def test_low_load_no_penalty(self):
        assert em.current_load("test", ["test", "test", "test"]) == 0.0

    def test_high_load_penalty(self):
        penalty = em.current_load("test", ["test"] * 5)
        assert penalty > 0.0

    def test_penalty_capped_at_1(self):
        penalty = em.current_load("test", ["test"] * 10)
        assert penalty <= 1.0


class TestMatch:
    def test_match_returns_top_k(self):
        result = em.match(["08-FinanceInvestment"], top_k=3)
        assert len(result) <= 3
        assert len(result) > 0

    def test_match_sorted_by_score(self):
        result = em.match(["08-FinanceInvestment"], top_k=5)
        scores = [m["score"] for m in result]
        assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    def test_match_has_strategy(self):
        result = em.match(["08-FinanceInvestment"], top_k=1)
        assert result[0]["strategy"] in ("direct_call", "team_recommend", "fallback")

    def test_high_score_direct(self):
        result = em.match(["08-FinanceInvestment", "04-DataAI", "02-Engineering"], top_k=1)
        assert len(result) > 0

    def test_task_decomposer_integration(self):
        td_path = SCRIPTS_DIR / "task-decomposer.py"
        td = importlib.util.module_from_spec(
            importlib.util.spec_from_file_location("task_decomposer", str(td_path)))
        td = importlib.util.module_from_spec(
            importlib.util.spec_from_file_location("task_decomposer", str(td_path)))
        spec = importlib.util.spec_from_file_location("task_decomposer", str(td_path))
        td = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(td)

        task = "帮我分析腾讯股票"
        decomp = td.decompose(task)
        result = em.match(decomp["domains"], decomp["pi_types"], top_k=2)
        assert len(result) > 0
        assert result[0]["score"] > 0


class TestStrategyRecommendation:
    def test_direct_call(self):
        assert em._recommend_strategy(0.9) == "direct_call"

    def test_team_recommend(self):
        assert em._recommend_strategy(0.7) == "team_recommend"

    def test_fallback(self):
        assert em._recommend_strategy(0.3) == "fallback"
