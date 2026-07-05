"""测试 task-decomposer.py — 第一性原理任务拆解"""
import pytest
import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "scripts"
spec = importlib.util.spec_from_file_location("task_decomposer", str(SCRIPTS_DIR / "task-decomposer.py"))
td = importlib.util.module_from_spec(spec)
spec.loader.exec_module(td)


class TestPITypes:
    @pytest.mark.parametrize("task,expected_pis", [
        ("帮我查一下腾讯的股价", ["信息检索型"]),
        ("分析这只股票的未来走势", ["分析判断型"]),
        ("写一篇AI行业分析报告", ["创作生成型"]),
        ("该不该买腾讯股票", ["决策执行型"]),
    ])
    def test_detect_pi(self, task, expected_pis):
        result = td.decompose(task)
        for ep in expected_pis:
            assert ep in result["pi_types"], f"Expected {ep} in {result['pi_types']}"

    def test_default_pi(self):
        result = td.decompose("hello world")
        assert "分析判断型" in result["pi_types"]


class TestDomains:
    @pytest.mark.parametrize("task,expected_domain", [
        ("帮我分析腾讯股票", "08-FinanceInvestment"),
        ("实现一个登录功能", "02-Engineering"),
        ("写一篇营销文案", "05-MarketingGrowth"),
        ("这个合同有法律风险吗", "11-SecurityCompliance"),
    ])
    def test_detect_domain(self, task, expected_domain):
        result = td.decompose(task)
        assert expected_domain in result["domains"]

    def test_default_domain(self):
        result = td.decompose("hello world")
        assert "12-IndustryConsultant" in result["domains"]


class TestComplexity:
    @pytest.mark.parametrize("task,len_threshold,expect_level", [
        ("分析股票", 1, "L1-简单"),
        ("帮我分析一下腾讯股票的财务数据和市场表现", 2, "L2-中等"),
    ])
    def test_complexity(self, task, len_threshold, expect_level):
        result = td.decompose(task)
        assert result["complexity"] == expect_level


class TestIntegration:
    def test_decompose_returns_required_fields(self):
        result = td.decompose("帮我分析腾讯股票的最新财务数据")
        assert "task" in result
        assert "pi_types" in result
        assert "domains" in result
        assert "complexity" in result
        assert "suggested_experts" in result

    def test_suggested_experts_reasonable(self):
        result = td.decompose("帮我分析腾讯股票")
        assert result["suggested_experts"] >= 1
