"""测试 task-decomposer.py — 仅断言已核实的真实行为（无 pytest 依赖）"""
import importlib.util
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "task_decomposer", str(SKILL / "scripts" / "task-decomposer.py")
)
td = importlib.util.module_from_spec(spec)
spec.loader.exec_module(td)


def test_required_keys():
    r = td.decompose("帮我分析腾讯股票的最新财务数据")
    for k in ("task", "pi_types", "domains", "complexity", "suggested_experts"):
        assert k in r, f"缺少字段 {k}"


def test_finance_domain():
    r = td.decompose("帮我分析腾讯股票")
    assert "08-FinanceInvestment" in r["domains"]


def test_analysis_pi():
    r = td.decompose("分析这只股票的未来走势")
    assert "分析判断型" in r["pi_types"]


def test_complexity_in_valid_set():
    r = td.decompose("分析股票")
    assert r["complexity"] in ("L1-简单", "L2-中等", "L3-复杂", "L4-极复杂")


def test_suggested_experts_positive():
    r = td.decompose("帮我分析腾讯股票")
    assert r["suggested_experts"] >= 1
