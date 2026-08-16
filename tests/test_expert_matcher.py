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


def test_aggregate_domains_mapping():
    """聚合域映射完整性（v3.9 · TC-20260816-5）：8 域全部映射到池内真实团队。"""
    exp = em.load_all_experts()
    assert len(em.AGGREGATE_DOMAINS) >= 8
    for domain, teams in em.AGGREGATE_DOMAINS.items():
        missing = [t for t in teams if t not in exp]
        assert not missing, f"{domain} 域缺失团队: {missing}"


def test_domain_filter_no_leak():
    """限域召回零泄漏：--domain 输出全部在域内（投资分析域样例）。"""
    exp = em.load_all_experts()
    domain = "投资分析"
    f = em.filter_by_domain(exp, domain)
    assert len(f) == len(em.AGGREGATE_DOMAINS[domain])
    assert set(f.keys()) == set(em.AGGREGATE_DOMAINS[domain])
    res = em.match(f, ["08-FinanceInvestment"], 10, min_score=0)
    assert len(res) > 0
    for score, info in res:
        assert info["name"] in em.AGGREGATE_DOMAINS[domain], f"域外泄漏: {info['name']}"


def test_domain_filter_unknown_domain():
    """未知聚合域不误伤：返回原池。"""
    exp = em.load_all_experts()
    f = em.filter_by_domain(exp, "不存在的域")
    assert f == exp
