"""测试 S0: 三阶层次化加载基础设施"""
import json
import os
import time
import shutil
import pytest
import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "scripts"
SHARED_DIR = SCRIPTS_DIR.parent / "shared"

spec_em = importlib.util.spec_from_file_location("expert_matcher", str(SCRIPTS_DIR / "expert_matcher.py"))
em = importlib.util.module_from_spec(spec_em)
spec_em.loader.exec_module(em)

spec_bc = importlib.util.spec_from_file_location("budget_controller", str(SCRIPTS_DIR / "budget-controller.py"))
bc = importlib.util.module_from_spec(spec_bc)
spec_bc.loader.exec_module(bc)

TEAMS_INDEX = SHARED_DIR / "teams-index.json"


class TestTier1:
    def test_tier1_load_returns_index(self):
        em._TIER_CACHE["l1"] = {}
        result = em.load_experts_light()
        assert isinstance(result, dict)
        assert len(result) > 0
        first = list(result.values())[0]
        assert "name" in first
        assert "category_id" in first
        assert "agent_count" in first

    def test_tier1_has_key_teams(self):
        em._TIER_CACHE["l1"] = {}
        result = em.load_experts_light()
        assert "investment-masters-team" in result
        assert "a-share-analysis" in result

    def test_tier1_no_agent_md_read(self):
        em._TIER_CACHE["l1"] = {}
        result = em.load_experts_light()
        team = result["a-share-analysis"]
        assert team["agent_count"] == 8
        assert "agent_names" not in team


class TestTier2:
    def test_tier2_load_single_team(self):
        em._cache_clear_tier2()
        result = em.load_experts_detail(["a-share-analysis"])
        assert "a-share-analysis" in result
        team = result["a-share-analysis"]
        assert team["name"] == "a-share-analysis"
        assert len(team["agent_names"]) == 8
        assert team["category_id"] == "08-FinanceInvestment"

    def test_tier2_load_multiple(self):
        em._cache_clear_tier2()
        result = em.load_experts_detail(["a-share-analysis", "trading-agent"])
        assert len(result) == 2

    def test_tier2_empty_input(self):
        assert em.load_experts_detail([]) == {}

    def test_tier2_nonexistent_team(self):
        assert em.load_experts_detail(["nonexistent-team"]) == {}


class TestTier3:
    def test_tier3_load_agents(self):
        agents = em.load_agents_lazy("a-share-analysis")
        assert len(agents) == 8
        for aid, info in agents.items():
            assert "agent_id" in info
            assert "content_length" in info
            assert info["content_length"] > 0
            assert "token_estimate" in info

    def test_tier3_nonexistent_team(self):
        assert em.load_agents_lazy("nonexistent") == {}

    def test_tier3_encoding_fallback(self):
        agents = em.load_agents_lazy("a-share-analysis")
        assert len(agents) > 0


class TestTeamTier:
    def test_new_team_is_cold(self):
        assert em.is_cold_team("never-used-before")

    def test_after_use_is_hot(self):
        em._update_team_tier_state("test-hot", "used")
        assert em.get_team_tier("test-hot") == "hot"
        # cleanup
        state = em._load_team_tier_state()
        state.pop("test-hot", None)
        em._save_team_tier_state(state)

    def test_old_team_is_cold(self):
        now = time.time()
        state = em._load_team_tier_state()
        state["test-cold"] = {"last_used": now - 86400 * 60, "use_count": 1}
        em._save_team_tier_state(state)
        assert em.is_cold_team("test-cold")
        state.pop("test-cold", None)
        em._save_team_tier_state(state)


class TestTier1Fallback:
    def setup_method(self):
        backup = SHARED_DIR / "teams-index.json.tmpbak"
        if TEAMS_INDEX.exists() and not backup.exists():
            shutil.copy2(str(TEAMS_INDEX), str(backup))
            TEAMS_INDEX.unlink()

    def teardown_method(self):
        backup = SHARED_DIR / "teams-index.json.tmpbak"
        if backup.exists():
            if TEAMS_INDEX.exists():
                TEAMS_INDEX.unlink()
            shutil.move(str(backup), str(TEAMS_INDEX))
        em._TIER_CACHE["l1"] = {}

    def test_fallback_when_index_missing(self):
        em._TIER_CACHE["l1"] = {}
        result = em.load_experts_light()
        assert len(result) > 0
        assert "a-share-analysis" in result


class TestBudgetDowngrade:
    @pytest.fixture
    def high_usage(self):
        backup = None
        tb = SHARED_DIR / "token-budget.json"
        if tb.exists():
            backup = tb.read_text(encoding="utf-8")
        data = {"total_budget": 100000, "used": 86000, "history": []}
        tb.write_text(json.dumps(data), encoding="utf-8")
        yield
        if backup:
            tb.write_text(backup, encoding="utf-8")

    @pytest.fixture
    def normal_usage(self):
        backup = None
        tb = SHARED_DIR / "token-budget.json"
        if tb.exists():
            backup = tb.read_text(encoding="utf-8")
        data = {"total_budget": 100000, "used": 50000, "history": []}
        tb.write_text(json.dumps(data), encoding="utf-8")
        yield
        if backup:
            tb.write_text(backup, encoding="utf-8")

    def test_downgrade_economy(self, high_usage):
        ctrl = bc.BudgetController()
        verdict = ctrl.check_budget(agent_count=8)
        assert verdict.mode == "economy"
        assert verdict.max_agents_per_team == 5
        assert verdict.load_agent_content is False

    def test_standard_mode(self, normal_usage):
        ctrl = bc.BudgetController()
        verdict = ctrl.check_budget(agent_count=8)
        assert verdict.mode == "standard"
        assert verdict.load_agent_content is True
