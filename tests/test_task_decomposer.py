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
    # v3.9 修复：实现为 "L4-深度"（test-workflow B2：规模门仅 L1/L2/L3+，L4-深度为 cross-validation 深度档标签）
    assert r["complexity"] in ("L1-简单", "L2-中等", "L3-复杂", "L4-深度")


def test_suggested_experts_positive():
    r = td.decompose("帮我分析腾讯股票")
    assert r["suggested_experts"] >= 1


def test_suggested_subagents_required_fields():
    """动态派数输出契约（v3.9 · TC-20260816-6）：{value, range, rationale}。"""
    r = td.decompose("帮我分析腾讯股票的基本面和估值，给出投资建议，涉及行业对比与风险评估")
    sa = r["suggested_subagents"]
    assert set(sa.keys()) == {"value", "range", "rationale"}
    assert len(sa["range"]) == 2
    assert sa["rationale"]


def test_dynamic_dispatch_table():
    """取值表断言（终审裁决）：L1→0 / L2→1 直行信号 / L3+ clamp[2,min(并发,档位)]。"""
    assert td.suggest_subagents("L1-简单", ["08-FinanceInvestment"])["value"] == 0
    assert td.suggest_subagents("L2-中等", ["08-FinanceInvestment"])["value"] == 1
    assert td.suggest_subagents("L3-复杂", ["08-FinanceInvestment"])["value"] == 4      # L3×D1
    assert td.suggest_subagents("L3-复杂", ["a", "b"])["value"] == 5                   # L3×D2
    assert td.suggest_subagents("L3-复杂", ["a", "b", "c"])["value"] == 6              # L3×D3 封顶
    assert td.suggest_subagents("L4-深度", ["a", "b", "c", "d"])["value"] == 6         # L4 并发截断


def test_concurrency_cap():
    """--concurrency 仅调 MAX_CONCURRENT，仍受 tier_cap 截断。"""
    assert td.suggest_subagents("L3-复杂", ["a", "b", "c"], concurrency=4)["value"] == 4
    # 默认并发 6：L4×D4 raw=8 → cap=min(6,8)=6 → value=6（并发截断）
    assert td.suggest_subagents("L4-深度", ["a", "b", "c", "d"])["value"] == 6
    # 显式并发 8：cap=min(8, tier_cap 8)=8 → value=8（档位上限可达）
    r = td.suggest_subagents("L4-深度", ["a", "b", "c", "d"], concurrency=8)
    assert r["value"] == 8
    assert r["range"][1] == 8
