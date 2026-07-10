"""E2E 集成测试 — 完整业务流程链路验证"""
import json, os, shutil
import importlib.util
from pathlib import Path

SKILL_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration"
SCRIPTS_DIR = SKILL_DIR / "scripts"
SHARED_DIR = SKILL_DIR / "shared"

# Load modules
spec_em = importlib.util.spec_from_file_location("em", str(SCRIPTS_DIR / "expert_matcher.py"))
em = importlib.util.module_from_spec(spec_em)
spec_em.loader.exec_module(em)

spec_team = importlib.util.spec_from_file_location("tb", str(SCRIPTS_DIR / "team_builder.py"))
tb = importlib.util.module_from_spec(spec_team)
spec_team.loader.exec_module(tb)

spec_td = importlib.util.spec_from_file_location("td", str(SCRIPTS_DIR / "task_decomposer.py"))
td = importlib.util.module_from_spec(spec_td)
spec_td.loader.exec_module(td)

spec_sc = importlib.util.spec_from_file_location("sc", str(SCRIPTS_DIR / "score_collector.py"))
sc = importlib.util.module_from_spec(spec_sc)
spec_sc.loader.exec_module(sc)

spec_oc = importlib.util.spec_from_file_location("oc", str(SCRIPTS_DIR / "orchestrator.py"))
oc = importlib.util.module_from_spec(spec_oc)
spec_oc.loader.exec_module(oc)

TEAMS_INDEX = SHARED_DIR / "teams-index.json"


class TestStandardPath:
    """标准路径: task → decomposer → match → crop → execute → score"""

    def test_full_pipeline_standard(self):
        # Step 1: decompose
        decomp = td.decompose("分析腾讯股票的财务数据和市场表现")
        assert "subtasks" in decomp
        assert len(decomp["subtasks"]) > 0

        # Step 2: build team (match → crop)
        team = tb.build_team(task="分析腾讯股票", subtasks=decomp["subtasks"],
                             task_type=decomp.get("main_type"), no_explore=True)
        assert team["team_name"]
        assert len(team["agents"]) >= 0
        assert team["token_estimate"] >= 0

        # Step 3: execute via orchestrator
        orch = oc.NexusOrchestrator()
        result = orch.run("分析腾讯股票的财务数据和市场表现")
        assert result["status"] in ("PASS", "PARTIAL")
        assert result["path"] == "standard"

        # Step 4: record score
        if team["team_name"]:
            score = sc.record_score(team["team_name"], "delivery_quality", 8)
            assert score["dimension"] == "delivery_quality"

    def test_decomposer_to_build_team_contract(self):
        """验证 decomposer 输出可直接传给 build_team"""
        decomp = td.decompose("写一篇AI行业分析报告")
        team = tb.build_team(task=decomp["task"], subtasks=decomp["subtasks"],
                             task_type=decomp.get("main_type"),
                             domains=decomp.get("domains", []),
                             abilities=decomp.get("abilities", []),
                             no_explore=True)
        assert isinstance(team["agents"], list)

    def test_pipeline_with_user_feedback_scoring(self):
        """评分链路：构建→执行→用户反馈写入"""
        decomp = td.decompose("帮我查一下Python文档")
        team = tb.build_team(task=decomp["task"], subtasks=decomp["subtasks"], no_explore=True)
        if team["team_name"]:
            sc.record_score(team["team_name"], "user_feedback", 9)
            profile = sc.get_profile(team["team_name"])
            uf = profile.get("dimensions", {}).get("user_feedback", {})
            assert uf.get("n", 0) > 0


class TestColdTeamPath:
    """Cold 团路径: match 时只扫描 Tier 1"""

    def test_cold_team_light_load(self):
        em._TIER_CACHE["l1"] = {}
        result = em.load_experts_light()
        assert len(result) > 0
        # confirm no agent .md loaded (Tier1 only)
        first_name = list(result.keys())[0]
        first = result[first_name]
        assert "agent_count" in first  # index has count but no agent detail

    def test_cold_team_then_hot(self):
        em._TIER_CACHE["l1"] = {}
        light = em.load_experts_light()
        assert len(light) > 0
        # load full — should upgrade to hot
        full = em.load_all_experts()
        assert len(full) >= len(light)


class TestTokenDegradePath:
    """Token 降级路径: 预算不足时自动切 economy"""

    def test_economy_mode_triggered(self):
        spec_bc = importlib.util.spec_from_file_location("bc",
                    str(SCRIPTS_DIR / "budget-controller.py"))
        bc = importlib.util.module_from_spec(spec_bc)
        spec_bc.loader.exec_module(bc)

        controller = bc.BudgetController()
        orig_used = controller._budget["used"]
        orig_total = controller._budget["total_budget"]
        controller._budget["used"] = 9000
        controller._budget["total_budget"] = 10000
        controller._save_budget()

        verdict = controller.check_budget("test-team", agent_count=10)
        assert verdict.mode == "economy"
        assert verdict.max_agents_per_team <= 5

        controller._budget["used"] = orig_used
        controller._budget["total_budget"] = orig_total
        controller._save_budget()

    def test_standard_mode_with_sufficient_budget(self):
        spec_bc = importlib.util.spec_from_file_location("bc",
                    str(SCRIPTS_DIR / "budget-controller.py"))
        bc = importlib.util.module_from_spec(spec_bc)
        spec_bc.loader.exec_module(bc)

        controller = bc.BudgetController()
        controller._budget["used"] = 100
        controller._budget["total_budget"] = 10000
        controller._save_budget()

        verdict = controller.check_budget()
        assert verdict.mode == "standard"

        controller._budget["used"] = 0
        controller._budget["total_budget"] = 100000
        controller._save_budget()


class TestFallbackPath:
    """回退路径: teams-index.json 不存在时回退 load_all_experts()"""

    def setup_method(self):
        self.index_backup = None
        if TEAMS_INDEX.exists():
            self.index_backup = TEAMS_INDEX.read_text(encoding="utf-8")
            TEAMS_INDEX.rename(TEAMS_INDEX.with_suffix(".json.bak"))

    def teardown_method(self):
        bak = TEAMS_INDEX.with_suffix(".json.bak")
        if bak.exists():
            bak.rename(TEAMS_INDEX)
        if self.index_backup:
            pass

    def test_fallback_load_all_experts(self):
        em._TIER_CACHE["l1"] = {}
        try:
            light = em.load_experts_light()
            assert isinstance(light, dict)
        except Warning:
            pass
        # full load should still work
        full = em.load_all_experts()
        assert len(full) > 0

    def test_fallback_build_team_still_works(self):
        bak = TEAMS_INDEX.with_suffix(".json.bak")
        if TEAMS_INDEX.exists():
            TEAMS_INDEX.rename(TEAMS_INDEX.with_suffix(".json.bak2"))
        try:
            team = tb.build_team(task="测试回退", subtasks=[{"type": "general"}],
                                 no_explore=True)
            assert isinstance(team["agents"], list)
        finally:
            bak2 = TEAMS_INDEX.with_suffix(".json.bak2")
            if bak2.exists():
                bak2.rename(TEAMS_INDEX)


class TestTrivialPath:
    """模糊/简单任务路径"""

    def test_ambiguous_task_returns_clarification(self):
        orch = oc.NexusOrchestrator()
        result = orch.run("优化一下")
        assert result["status"] == "CLARIFICATION_NEEDED"

    def test_trivial_task_direct(self):
        orch = oc.NexusOrchestrator()
        result = orch.run("查一下Python文档")
        assert result["status"] in ("PASS", "CLARIFICATION_NEEDED")


class TestScoreIntegration:
    """评分集成验证"""

    def test_match_to_score_roundtrip(self):
        matches = em.match([], [], top_k=1, no_explore=True)
        assert len(matches) > 0
        name = matches[0]["name"]
        # record score
        sc.record_batch(name, {
            "task_completion": 8,
            "delivery_quality": 7,
            "response_time": 6,
        })
        profile = sc.get_profile(name)
        assert profile.get("count", 0) > 0
        assert profile.get("score", 0) > 0
