#!/usr/bin/env python3
"""First-principles task decomposer for team-orchestration.

Usage:
    python3 task-decomposer.py --task "帮我分析腾讯股票"
    python3 task-decomposer.py --task "写一篇AI行业分析报告" --json
"""
import json, sys, argparse, re

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
    return list(domains) if domains else ["12-IndustryConsultant"]

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

def decompose(task: str) -> dict:
    pi = detect_pi(task)
    domains = detect_domains(task)
    complexity = estimate_complexity(task, domains)
    result = {
        "task": task,
        "pi_types": pi,
        "domains": domains,
        "complexity": complexity,
        "suggested_experts": len(domains) + (2 if complexity in ["L3-复杂","L4-深度"] else 0),
    }
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = decompose(args.task)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"任务: {result['task']}")
        print(f"本质类型: {', '.join(result['pi_types'])}")
        print(f"知识域: {', '.join(result['domains'])}")
        print(f"复杂度: {result['complexity']}")
        print(f"建议专家数: {result['suggested_experts']}")

if __name__ == "__main__":
    main()
