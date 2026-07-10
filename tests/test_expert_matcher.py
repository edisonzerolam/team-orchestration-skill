"""测试 expert_matcher.py v2 — 4维度加权匹配引擎"""
import json
import pytest
from scripts import expert_matcher as em


class TestLoadExperts:
    def test_load_all_experts_returns_dict(self):
        experts = em.load_all_experts()
        assert isinstance(experts, dict)

    def test_contains_key_teams(self):
        experts = em.load_all_experts()
        assert len(experts) > 0

    def test_expert_has_required_fields(self):
        experts = em.load_all_experts()
        for name, exp in experts.items():
            assert "name" in exp

    def test_expert_has_agent_files(self):
        experts = em.load_all_experts()
        for name, exp in experts.items():
            if exp.get("agent_count", 0) == 0:
                continue
            assert len(exp.get("agents", [])) >= 0


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


class TestStrategyRecommendation:
    def test_direct_call(self):
        assert em._recommend_strategy(0.9) == "direct_call"

    def test_team_recommend(self):
        assert em._recommend_strategy(0.7) == "team_recommend"

    def test_fallback(self):
        assert em._recommend_strategy(0.3) == "fallback"


class TestWeightMatrix:
    def test_load_fallback_weights(self):
        w = em.load_weight_matrix(None)
        assert abs(w["domain"] - 0.35) < 0.01
        assert abs(w["capability"] - 0.30) < 0.01

    def test_load_task_type_weights(self):
        w = em.load_weight_matrix("analysis_judgment")
        assert abs(w["domain"] - 0.35) < 0.01
        assert abs(w["capability"] - 0.25) < 0.01

    def test_load_invalid_type_fallback(self):
        w = em.load_weight_matrix("nonexistent_type")
        assert "domain" in w
        assert abs(w["domain"] - 0.35) < 0.01

    def test_quality_verification_weights(self):
        w = em.load_weight_matrix("quality_verification")
        assert abs(w["performance"] - 0.30) < 0.01

    def test_collaborative_discussion_weights(self):
        w = em.load_weight_matrix("collaborative_discussion")
        assert abs(w["load"] - 0.20) < 0.01

    def test_match_with_task_type(self):
        result = em.match(["08-FinanceInvestment"], task_type="analysis_judgment", top_k=2, no_explore=True)
        assert len(result) > 0
        assert result[0].get("weights_used") == "analysis_judgment"

    def test_match_without_task_type(self):
        result = em.match(["08-FinanceInvestment"], top_k=2, no_explore=True)
        assert len(result) > 0
        assert result[0].get("weights_used") == "fallback"


class TestForceTeam:
    def test_force_team_returns_exact(self):
        result = em.match(["08-FinanceInvestment"], force_team="a-share-analysis", top_k=3, no_explore=True)
        assert len(result) == 1
        assert result[0]["name"] == "a-share-analysis"
        assert result[0].get("forced") is True

    def test_force_team_unknown_returns_empty(self):
        result = em.match([], force_team="nonexistent-team", no_explore=True)
        assert result == []


class TestExploration:
    def test_should_explore_new_team(self):
        log = em._get_exploration_log()
        if "test-exploration-new" in log.get("experts", {}):
            log["experts"].pop("test-exploration-new")
            em._save_exploration_log(log)
        assert em._should_explore("test-exploration-new") is True

    def test_new_expert_baseline(self):
        baseline = em._get_exploration_baseline("analysis_judgment")
        assert 0 < baseline <= 0.5

    def test_exploration_log(self):
        em._log_exploration("test-explore-team", "analysis_judgment", "explored")
        log = em._get_exploration_log()
        assert "test-explore-team" in log.get("experts", {})
        assert log["experts"]["test-explore-team"]["exploration_count"] >= 1
        log["experts"].pop("test-explore-team")
        em._save_exploration_log(log)

    def test_exploration_graduate(self):
        em._log_exploration("test-graduate-team", "test", "explored")
        em._log_exploration("test-graduate-team", "test", "explored")
        em._log_exploration("test-graduate-team", "test", "explored")
        em._log_exploration("test-graduate-team", "test", "explored")
        em._log_exploration("test-graduate-team", "test", "explored")
        log = em._get_exploration_log()
        status = log.get("experts", {}).get("test-graduate-team", {}).get("status")
        assert status == "graduated"
        log["experts"].pop("test-graduate-team")
        em._save_exploration_log(log)

    def test_exploration_match_has_flag(self):
        result = em.match(["08-FinanceInvestment"], top_k=3, no_explore=True)
        for r in result:
            assert "explored" in r
