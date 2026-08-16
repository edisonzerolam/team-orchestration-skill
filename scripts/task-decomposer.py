#!/usr/bin/env python3
"""First-principles task decomposer for team-orchestration.

Usage:
    python3 task-decomposer.py --task "帮我分析腾讯股票"
    python3 task-decomposer.py --task "写一篇AI行业分析报告" --json
"""
import json, sys, argparse, re
import sys
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PI_TYPES = {
    "p1": {"name": "信息检索型", "keywords": ["查","找","搜索","查询","获取","搜","看"]},
    "p2": {"name": "分析判断型", "keywords": ["分析","评估","判断","预测","诊断","研究","怎么看"]},
    "p3": {"name": "创作生成型", "keywords": ["写","生成","设计","制作","创建","创作","做"]},
    "p4": {"name": "决策执行型", "keywords": ["该不该","决策","执行","部署","买不买","卖不卖"]},
}

CATEGORIES = {
    "金融": "08-FinanceInvestment",
    "股票": "08-FinanceInvestment",
    "投资": "08-FinanceInvestment",
    "交易": "08-FinanceInvestment",
    "基本面": "08-FinanceInvestment",
    "估值": "08-FinanceInvestment",
    "财报": "08-FinanceInvestment",
    "个股": "08-FinanceInvestment",
    "上市": "08-FinanceInvestment",
    "基金": "08-FinanceInvestment",
    "板块": "08-FinanceInvestment",
    "设计": "01-ProductDesign",
    "UI": "01-ProductDesign",
    "产品": "01-ProductDesign",
    "代码": "02-Engineering",
    "开发": "02-Engineering",
    "架构": "02-Engineering",
    "数据": "04-DataAI",
    "量化": "04-DataAI",
    "AI": "04-DataAI",
    "营销": "05-MarketingGrowth",
    "SEO": "05-MarketingGrowth",
    "内容": "06-ContentCreative",
    "文案": "06-ContentCreative",
    "法律": "11-SecurityCompliance",
    "法务": "11-SecurityCompliance",
    "合规": "11-SecurityCompliance",
    "税务": "11-SecurityCompliance",
    "HR": "09-OperationsHR",
    "运营": "09-OperationsHR",
    "销售": "07-SalesCommerce",
    "项目": "10-ProjectQuality",
}

def detect_pi(task: str) -> list:
    matched = []
    for pid, info in PI_TYPES.items():
        for kw in info["keywords"]:
            if kw in task:
                matched.append(info["name"])
                break
    return matched if matched else ["分析判断型"]

def detect_domains(task: str) -> list:
    domains = set()
    for kw, cat in CATEGORIES.items():
        if kw in task:
            domains.add(cat)
    # TC-20260816-9 修正：无关键词匹配不再回退 12-IndustryConsultant（曾致 opc/tech 在
    # 无关任务中霸榜）；无域信号 = 空（复杂度判 L1，域路由走通用兜底）
    return list(domains)

def estimate_complexity(task: str, domains: list) -> str:
    words = len(task)
    domain_count = len(domains)
    if words < 15 and domain_count <= 1:
        return "L1-简单"
    elif words < 40 and domain_count <= 2:
        return "L2-中等"
    elif words < 80 or domain_count <= 3:
        return "L3-复杂"
    else:
        return "L4-深度"


# token_budget 档位子代理上限（L3/L4；L1/L2 直行不走并行举证）
_TIER_CAP = {"L3": 6, "L4": 8}
_BASE = {"L3": 4, "L4": 6}
# 编排层稳定并发（TC-20260816-6 实测：DSH 子代理 6 并行稳定）。
# 注：模型官方并发上限远高于此（deepseek-v4-flash=2500，账号粒度，见
# api-docs.deepseek.com/quick_start/rate_limit）——不构成实际约束；
# 真实瓶颈为编排层调度 + 上下文 + 预算。--concurrency 可调。
_DEFAULT_CONCURRENCY = 6


def suggest_subagents(complexity: str, domains: list, concurrency: int = None) -> dict:
    """动态派数（v3.9 · TC-20260816-6 二审终审）：
    N = 0(L1直行) | 1(L2直行信号) | clamp(base+bonus, 2, min(MAX_CONCURRENT, tier_cap)) (L3+)

    输入：复杂度 L 档 + 去重专业域数 D + 模型并发上限（--concurrency，默认 6，实测稳定值）。
    输出：{value, range[lo,hi], rationale}——推荐值非强制，main 可覆写。
    """
    c = concurrency or _DEFAULT_CONCURRENCY
    d = len(set(domains))
    level = complexity.split("-")[0]
    if level == "L1":
        return {"value": 0, "range": [0, 0],
                "rationale": "L1 简单直行（§2 规模门），单 agent 自我批判"}
    if level == "L2":
        return {"value": 1, "range": [1, 1],
                "rationale": "L2 中等直行信号（§2 规模门）；main 依 §6 可手动 2 视角（正/反）——手动派数须过 C(N,q) 预算校验"}
    # L3/L4：base + 分工加成（D=1→0 / D=2→+1 / D≥3→+2，封顶 D+2≤6）
    bonus = 0 if d == 1 else (1 if d == 2 else 2)
    base = _BASE.get(level, 4)
    raw = base + bonus
    cap = min(c, _TIER_CAP.get(level, 6))
    value = max(2, min(raw, cap))
    cuts = []
    if raw > cap:
        cuts.append(f"并发/档位截断 min({c},{_TIER_CAP.get(level, 6)})")
    if raw < 2:
        cuts.append("下限 2（正/反对抗）")
    lo, hi = 2, cap
    return {
        "value": value,
        "range": [lo, hi],
        "rationale": f"{level}×D{d}: base={base}+bonus={bonus}→{raw}；{('截断: '+'; '.join(cuts)) if cuts else '未截断'}"
    }


def decompose(task: str, concurrency: int = None) -> dict:
    pi = detect_pi(task)
    domains = detect_domains(task)
    complexity = estimate_complexity(task, domains)
    sa = suggest_subagents(complexity, domains, concurrency)
    result = {
        "task": task,
        "pi_types": pi,
        "domains": domains,
        "complexity": complexity,
        "suggested_experts": len(domains) + (2 if complexity in ["L3-复杂","L4-深度"] else 0),
        "suggested_subagents": sa,
    }
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--concurrency", type=int, default=None,
                    help="模型并发上限（默认 6，实测稳定值；仅调 MAX_CONCURRENT，仍受 tier_cap 截断）")
    args = ap.parse_args()
    result = decompose(args.task, args.concurrency)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"任务: {result['task']}")
        print(f"本质类型: {', '.join(result['pi_types'])}")
        print(f"知识域: {', '.join(result['domains'])}")
        print(f"复杂度: {result['complexity']}")
        print(f"建议专家数: {result['suggested_experts']}")
        sa = result['suggested_subagents']
        print(f"建议子代理数: {sa['value']}（区间 {sa['range'][0]}-{sa['range'][1]}）")
        print(f"  依据: {sa['rationale']}")

if __name__ == "__main__":
    main()
