"""测试 expert-matcher.py — 真实 API 冒烟测试（无 pytest 依赖，可被 run_smoke.py 调用）"""
import importlib.util
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "expert_matcher", str(SKILL / "scripts" / "expert-matcher.py")
)
em = importlib.util.module_from_spec(spec)
spec.loader.exec_module(em)


def test_load_all_experts():
    exp = em.load_all_experts()
    assert isinstance(exp, dict) and len(exp) > 0


def test_match_finance_topk():
    exp = em.load_all_experts()
    res = em.match(exp, ["08-FinanceInvestment"], 3)
    assert isinstance(res, list) and len(res) <= 3
    for score, info in res:
        assert 0.0 <= score <= 1.0
        assert "name" in info
