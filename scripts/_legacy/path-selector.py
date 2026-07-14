#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Path Selector — 执行路径自动选择器

根据专家匹配评分、任务复杂度、知识域数量，自动选择最佳执行路径。

三条路径 + 互斥规则:
  1. 直调路径 — 单专家即可完成任务 (Score > 0.8)
  2. 团队路径 — 组建专家团队协作 (Score > 0.5, 且复杂度 >= L3 或域 > 1)
  3. 快速路径 — 使用预定义团队模板 (Score > 0.5, 且有匹配模板)
  4. 通用路径 — 退回到通用 agent (Score <= 0.5)

互斥规则:
  - 直调路径 优先级最高: Score > 0.8 且复杂度 L1-L2
  - 团队路径 次高: Score > 0.5 且 (复杂度 >= L3 或域 > 1)
  - 快速路径: Score > 0.5 且有模板匹配
  - 通用路径: 所有条件都不满足

用法:
  python3 path-selector.py --matches matches.json --task "分析股票"
  python3 path-selector.py --domains "08-FinanceInvestment" --complexity L2 --json
"""
import json
import sys
import argparse
from pathlib import Path


# 路径选择阈值
# B4: 与 expert_matcher.py THRESHOLDS 保持同步
#   expert_matcher: direct_call=0.75, team_recommend=0.45
#   path-selector:  direct_call=0.75, team_path=0.45, fallback=0.45
PATH_RULES = {
    "direct_call": {
        "min_score": 0.75,
        "max_complexity": "L2",       # 仅 L1-L2 适合直调
        "max_domain_count": 1,        # 仅单域适合直调
    },
    "team_path": {
        "min_score": 0.45,
        "min_complexity": "L3",       # L3+ 需要团队
        "min_domain_count": 1,        # 多域触发团队
    },
    "fast_path": {
        "min_score": 0.45,
        "requires_template": True,    # 需要匹配到模板
    },
    "fallback": {
        "max_score": 0.45,             # 低于此值走通用
    },
}

# 模板列表（用于快速路径匹配）
TEAM_TEMPLATES = [
    "software-team",           # 软件开发
    "investment-masters",      # 投资研究（原 "investment-team" → 与 SKILL.md 一致）
    "research-team",           # 深度研究
    "knowledge-workflow",      # 知识工程
    "a-share-analysis",        # A股分析
    "chatlaw",                 # 法律咨询（原 "legal-team" → 与 SKILL.md 一致）
    "strategy-audit",          # 审查策略
    "ai-content-creator",      # 内容创作（原 "content-team" → 与 SKILL.md 一致）
    "ai-data-copilot",         # 数据分析
    "engineering-assurance",   # 工程保障
    "content-distribution",    # 内容分发
    "enterprise-legal",        # 企业法务
    "design-engine",           # 产品设计（原 "design-team" → 与 SKILL.md 一致）
    "expert-panel",            # 专家小组
]


class ComplexityLevel:
    LEVELS = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}

    @staticmethod
    def parse(complexity_str: str) -> int:
        """将 'L1-简单' 转换为 1, 'L3-复杂' 转换为 3"""
        key = complexity_str.split("-")[0] if "-" in complexity_str else complexity_str
        return ComplexityLevel.LEVELS.get(key.upper(), 0)

    @staticmethod
    def le(left: str, right: str) -> bool:
        return ComplexityLevel.parse(left) <= ComplexityLevel.parse(right)

    @staticmethod
    def ge(left: str, right: str) -> bool:
        return ComplexityLevel.parse(left) >= ComplexityLevel.parse(right)


def find_matching_template(domains: list, team_names: list = None) -> str | None:
    """根据知识域匹配团队模板"""
    domain_to_template = {
        "02-Engineering": "software-team",
        "08-FinanceInvestment": "investment-masters",
        "04-DataAI": "research-team",
        "05-MarketingGrowth": "ai-content-creator",
        "06-ContentCreative": "ai-content-creator",
        "01-ProductDesign": "design-engine",
        "12-IndustryConsultant": "expert-panel",
        "11-SecurityCompliance": "chatlaw",
        "03-GameSpatial": "expert-panel",
        "07-SalesCommerce": "expert-panel",
        "09-OperationsHR": "expert-panel",
        "10-ProjectQuality": "engineering-assurance",
    }

    for domain in domains:
        if domain in domain_to_template:
            return domain_to_template[domain]

    # 如果给了 team_names，也检查是否匹配已知模板
    if team_names:
        for name in team_names:
            if name in TEAM_TEMPLATES:
                return name

    return None


def select_path(matches: list, domains: list, complexity: str,
                pi_types: list = None, available_templates: list = None) -> dict:
    """根据匹配结果和任务特征选择执行路径"""
    complexity_num = ComplexityLevel.parse(complexity)
    domain_count = len(domains)
    available_templates = available_templates or TEAM_TEMPLATES

    # 找到最高评分的专家
    top_score = matches[0]["score"] if matches else 0.0
    top_expert = matches[0] if matches else None
    matched_templates = [m.get("name") for m in matches if m.get("name") in available_templates]

    # 检查模板匹配
    template_match = find_matching_template(domains, [m.get("name") for m in matches])

    # 互斥规则引擎（按优先级）
    decisions = []

    # 规则 1: 直调路径
    dir_rule = PATH_RULES["direct_call"]
    if (top_score > dir_rule["min_score"]
            and ComplexityLevel.le(complexity, dir_rule["max_complexity"])
            and domain_count <= dir_rule["max_domain_count"]):
        decisions.append({
            "path": "direct_call",
            "confidence": min(top_score, 1.0),
            "reason": (f"高匹配单专家({top_score:.0%})，"
                       f"复杂度{complexity}适合单专家执行"),
            "expert": top_expert["name"] if top_expert else None,
            "agent_type": top_expert.get("agent_names", [None])[0] if top_expert else None,
        })

    # 规则 2: 团队路径
    team_rule = PATH_RULES["team_path"]
    if (top_score > team_rule["min_score"]
            and (ComplexityLevel.ge(complexity, team_rule["min_complexity"])
                 or domain_count > 1)):
        decisions.append({
            "path": "team_path",
            "confidence": top_score,
            "reason": (f"多专家协作({top_score:.0%})，"
                       f"复杂度{complexity}需要团队配合"),
            "expert": top_expert["name"] if top_expert else None,
            "agent_count": top_expert.get("agent_count", 0) if top_expert else 0,
        })

    # 规则 3: 快速路径（模板匹配）
    if template_match:
        decisions.append({
            "path": "fast_path",
            "confidence": top_score if top_score > PATH_RULES["fast_path"]["min_score"] else PATH_RULES["fast_path"]["min_score"],
            "reason": f"匹配到团队模板 '{template_match}'，直接按 SOP 执行",
            "template": template_match,
        })

    # 规则 4: 通用路径（兜底）
    if top_score <= PATH_RULES["fallback"]["max_score"]:
        decisions.append({
            "path": "fallback",
            "confidence": 0.3,
            "reason": f"专家匹配评分({top_score:.0%})低于阈值，退回到通用 agent",
        })

    # 如果一条规则都没触发，走通用
    if not decisions:
        decisions.append({
            "path": "fallback",
            "confidence": 0.3,
            "reason": "未匹配到任何路径，退回到通用 agent",
            "expert": top_expert["name"] if top_expert else None,
        })

    # 按优先级排序：direct_call > team_path > fast_path > fallback
    priority = {"direct_call": 0, "team_path": 1, "fast_path": 2, "fallback": 3}
    decisions.sort(key=lambda x: (priority.get(x["path"], 99), -x["confidence"]))

    selected = decisions[0]

    return {
        "selected_path": selected["path"],
        "confidence": selected["confidence"],
        "reason": selected["reason"],
        "details": selected,
        "all_candidates": decisions,
        "debug": {
            "top_score": top_score,
            "complexity": complexity,
            "domain_count": domain_count,
            "matches_count": len(matches),
            "template_match": template_match,
        },
    }


def main():
    ap = argparse.ArgumentParser(description="执行路径选择器")
    ap.add_argument("--matches", help="专家匹配结果 JSON 文件路径")
    ap.add_argument("--domains", nargs="+", default=[], help="知识域列表")
    ap.add_argument("--complexity", default="L2-中等", help="任务复杂度")
    ap.add_argument("--task", default="", help="任务描述（自动拆解）")
    ap.add_argument("--task-type", default=None,
                    help="任务类型（传给 expert_matcher 选择权重）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    # 如果有 --matches 文件，从文件加载
    if args.matches:
        with open(args.matches, encoding="utf-8") as f:
            matches = json.load(f)
        domains = args.domains
        complexity = args.complexity
    elif args.task or args.domains:
        # 自动调用 expert_matcher
        sys.path.insert(0, str(Path(__file__).parent))
        import importlib.util
        em_path = Path(__file__).parent / "expert_matcher.py"
        spec = importlib.util.spec_from_file_location("expert_matcher", str(em_path))
        em = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(em)

        # 如果没有显式传 domains，从 task 自动拆解
        if not args.domains and args.task:
            td_path = Path(__file__).parent / "task_decomposer.py"
            spec2 = importlib.util.spec_from_file_location("task_decomposer", str(td_path))
            td = importlib.util.module_from_spec(spec2)
            spec2.loader.exec_module(td)
            decomp = td.decompose(args.task)
            domains = decomp["domains"]
            complexity = decomp["complexity"]
        else:
            domains = args.domains

        matches = em.match(domains, top_k=3, task_type=args.task_type)
    else:
        print("错误: 需要 --matches 或 --task/--domains 参数")
        sys.exit(1)

    result = select_path(matches, domains, complexity)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        path_labels = {
            "direct_call": "直调路径",
            "team_path": "团队路径",
            "fast_path": "快速路径",
            "fallback": "通用路径",
        }
        print(f"\n{'=' * 50}")
        print("路径选择结果")
        print(f"{'=' * 50}")
        print(f"  🎯 选中路径: {path_labels.get(result['selected_path'], result['selected_path'])}")
        print(f"  置信度: {result['confidence']:.0%}")
        print(f"  理由: {result['reason']}")
        print(f"\n  调试信息:")
        dbg = result["debug"]
        print(f"    Top 评分: {dbg['top_score']:.0%}")
        print(f"    复杂度: {dbg['complexity']}")
        print(f"    知识域数: {dbg['domain_count']}")
        print(f"    匹配模板: {dbg['template_match'] or '无'}")

        if len(result["all_candidates"]) > 1:
            print(f"\n  候选项 ({len(result['all_candidates'])}):")
            for cand in result["all_candidates"]:
                mark = "✓" if cand == result["details"] else " "
                pname = path_labels.get(cand["path"], cand["path"])
                print(f"    [{mark}] {pname} ({cand['confidence']:.0%})")


if __name__ == "__main__":
    main()
