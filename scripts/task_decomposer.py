#!/usr/bin/env python3
"""First-principles task decomposer for team-orchestration.
v2.5 — 新增依赖排序的子任务输出，确保 research 先于 analysis

Usage:
    python3 task-decomposer.py --task "帮我分析腾讯股票"
    python3 task-decomposer.py --task "写一篇AI行业分析报告" --json
"""
import json, sys, argparse, re
from collections import deque

PI_TYPES = {
    "p1": {"name": "信息检索型", "keywords": ["查","找","搜索","查询","获取","搜","看","调研","收集"]},
    "p2": {"name": "分析判断型", "keywords": ["分析","评估","判断","预测","诊断","研究","怎么看","对比"]},
    "p3": {"name": "创作生成型", "keywords": ["写","生成","设计","制作","创建","创作","做","开发"]},
    "p4": {"name": "决策执行型", "keywords": ["该不该","决策","执行","部署","买不买","卖不卖"]},
    "p5": {"name": "协作讨论型", "keywords": ["讨论","协作","头脑风暴","brainstorm","review","会"]},
    "p6": {"name": "质量验证型", "keywords": ["验证","测试","质检","审查","审计","检查","审核"]},
}

CATEGORIES = {
    "金融": "08-FinanceInvestment", "股票": "08-FinanceInvestment",
    "投资": "08-FinanceInvestment", "交易": "08-FinanceInvestment",
    "设计": "01-ProductDesign", "UI": "01-ProductDesign",
    "产品": "01-ProductDesign", "代码": "02-Engineering",
    "开发": "02-Engineering", "架构": "02-Engineering",
    "登录": "02-Engineering", "功能": "02-Engineering",
    "数据": "04-DataAI", "量化": "04-DataAI", "AI": "04-DataAI",
    "营销": "05-MarketingGrowth", "SEO": "05-MarketingGrowth",
    "内容": "06-ContentCreative", "文案": "06-ContentCreative",
    "法律": "11-SecurityCompliance", "法务": "11-SecurityCompliance",
    "合规": "11-SecurityCompliance", "税务": "11-SecurityCompliance",
    "HR": "09-OperationsHR", "运营": "09-OperationsHR",
    "销售": "07-SalesCommerce", "项目": "10-ProjectQuality",
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
    words = len(task); dc = len(domains)
    if words < 15 and dc <= 1: return "L1-简单"
    elif words < 40 and dc <= 2: return "L2-中等"
    elif words < 80 or dc <= 3: return "L3-复杂"
    else: return "L4-深度"

def build_subtasks(task: str, pi_types: list, domains: list, complexity: str) -> list:
    """生成依赖排序的子任务列表
    规则: research 优先 -> analysis 依赖 research -> creation/decision 最后
    """
    needs_research = "信息检索型" in pi_types or "分析判断型" in pi_types
    needs_analysis = "分析判断型" in pi_types or "创作生成型" in pi_types
    needs_creation = "创作生成型" in pi_types
    needs_discussion = "协作讨论型" in pi_types
    needs_validation = "质量验证型" in pi_types
    needs_decision = "决策执行型" in pi_types

    subtasks = []
    sid = 0

    # Phase 1: 调研任务（无依赖，最先执行）
    if needs_research:
        subtasks.append({
            "id": f"ST-{sid:03d}", "phase": 1,
            "name": f"互联网调研: {task[:40]}",
            "type": "information_retrieval",
            "estimated_duration": "long",
            "dependency_ids": [],
            "output_fields": ["raw_data", "sources", "key_findings"],
        })
        sid += 1

    # Phase 2: 对每个知识域的分析任务（依赖调研）
    if needs_analysis:
        for i, domain in enumerate(domains):
            deps = [subtasks[0]["id"]] if needs_research else []
            subtasks.append({
                "id": f"ST-{sid:03d}", "phase": 2,
                "name": f"分析: {domain}",
                "type": "analysis_judgment",
                "estimated_duration": "medium",
                "dependency_ids": deps,
                "output_fields": ["analysis", "conclusions"],
            })
            sid += 1

    # Phase 2.5: 协作讨论（依赖分析结果）
    if needs_discussion:
        discussion_deps = [s["id"] for s in subtasks if s["phase"] in (1, 2)]
        subtasks.append({
            "id": f"ST-{sid:03d}", "phase": 3,
            "name": f"讨论: {task[:40]}",
            "type": "collaboration_discussion",
            "estimated_duration": "short",
            "dependency_ids": discussion_deps,
            "output_fields": ["discussion_summary", "consensus"],
        })
        sid += 1

    # Phase 3: 创作生成（依赖分析/讨论）
    if needs_creation:
        creation_deps = [s["id"] for s in subtasks if s["phase"] in (2, 3)]
        subtasks.append({
            "id": f"ST-{sid:03d}", "phase": 4,
            "name": f"生成: {task[:40]}",
            "type": "creation_generation",
            "estimated_duration": "medium",
            "dependency_ids": creation_deps,
            "output_fields": ["output"],
        })
        sid += 1

    # Phase 3.5: 质量验证（依赖生成/分析结果）
    if needs_validation:
        validation_deps = [s["id"] for s in subtasks if s["phase"] in (2, 3, 4)]
        subtasks.append({
            "id": f"ST-{sid:03d}", "phase": 5,
            "name": f"验证: {task[:40]}",
            "type": "quality_validation",
            "estimated_duration": "medium",
            "dependency_ids": validation_deps,
            "output_fields": ["validation_report", "issues"],
        })
        sid += 1

    # Phase 4: 决策（依赖所有前置）
    if needs_decision:
        all_prev = [s["id"] for s in subtasks]
        subtasks.append({
            "id": f"ST-{sid:03d}", "phase": 4,
            "name": f"决策: {task[:40]}",
            "type": "decision_execution",
            "estimated_duration": "short",
            "dependency_ids": all_prev,
            "output_fields": ["decision", "rationale"],
        })

    return subtasks

def topological_sort(subtasks: list) -> list:
    """Kahn 拓扑排序: 按执行顺序返回子任务 ID，同 phase 可并行"""
    graph = {}; indegree = {}
    for s in subtasks:
        graph[s["id"]] = []
        indegree[s["id"]] = 0
    for s in subtasks:
        for dep in s.get("dependency_ids", []):
            if dep in graph:
                graph[dep].append(s["id"])
                indegree[s["id"]] += 1

    queue = deque([n for n, d in indegree.items() if d == 0])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)
    return order

def decompose(task: str) -> dict:
    pi = detect_pi(task)
    domains = detect_domains(task)
    complexity = estimate_complexity(task, domains)
    subtasks = build_subtasks(task, pi, domains, complexity)
    exec_order = topological_sort(subtasks)

    result = {
        "task": task,
        "pi_types": pi,
        "domains": domains,
        "complexity": complexity,
        "suggested_experts": max(len(domains), 1) + (2 if complexity in ["L3-复杂","L4-深度"] else 0),
        "subtasks": subtasks,
        "execution_order": exec_order,
        "total_phases": max(s["phase"] for s in subtasks) if subtasks else 1,
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
        print(f"总阶段数: {result['total_phases']}")
        print(f"子任务数: {len(result['subtasks'])}")
        print(f"执行顺序: {' → '.join(result['execution_order'])}")
        for s in result['subtasks']:
            deps = f" (依赖: {s['dependency_ids']})" if s['dependency_ids'] else ""
            print(f"  [{s['id']}] Phase{s['phase']} {s['type']}: {s['name']}{deps}")

if __name__ == "__main__":
    main()
