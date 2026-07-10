"""团队构建器 — 封装 match→crop 链路

用法:
  from team_builder import build_team
  result = build_team(task="分析腾讯股票", subtasks=[...], task_type="analysis_judgment")

B3/F1 修复: 替代 orchestrator 中未调用的 match_experts 引用。
"""

import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

# 加载 expert_matcher
from scripts.expert_matcher import match, load_all_experts

# 加载 template_cropper
from scripts.template_cropper import crop_team


def build_team(task: str = "", subtasks: list = None,
               task_type: str = None, domains: list = None,
               abilities: list = None, force_team: str = None,
               no_explore: bool = False) -> dict:
    """构建团队: 匹配 → 裁剪 → 输出裁剪后的团队

    Args:
        task: 任务描述
        subtasks: 子任务列表 (含 type 字段)
        task_type: 任务类型 (如 analysis_judgment)
        domains: 知识域列表
        abilities: 能力列表
        force_team: 强制指定团队
        no_explore: 关闭 ε-greedy 探索

    Returns:
        {"agents": [...], "token_estimate": N, "mode": "...",
         "team_name": "...", "subtask_types": [...]}
    """
    domains = domains or []
    abilities = abilities or []
    subtasks = subtasks or []

    subtask_types = list(set(
        s.get("type", "general") for s in subtasks
    ))

    # 匹配专家
    matches = match(domains, abilities, top_k=5,
                    task_type=task_type,
                    force_team=force_team,
                    no_explore=no_explore)

    if not matches:
        return {"agents": [], "token_estimate": 0, "mode": "no_match",
                "team_name": "", "subtask_types": subtask_types}

    top_match = matches[0]
    team_name = top_match.get("name", top_match.get("id", ""))

    # 裁剪
    if subtask_types:
        cropped = crop_team(team_name, subtask_types)
    else:
        cropped = crop_team(team_name, [task_type or "general"])

    agent_count = cropped.get("cropped", 0)
    token_estimate = agent_count * 4000

    return {
        "agents": cropped.get("agents", []),
        "token_estimate": token_estimate,
        "mode": cropped.get("mode", "no_crop"),
        "team_name": team_name,
        "team_zh": top_match.get("display_zh", team_name),
        "match_score": top_match.get("score", 0),
        "subtask_types": subtask_types,
        "total_available": cropped.get("total", 0),
    }


def build_team_from_spec(spec: dict) -> dict:
    """从 orchestrator 的 task_spec 构建团队

    Args:
        spec: 包含 task, subtasks, task_type 等字段的字典

    Returns:
        TeamBuildResult
    """
    return build_team(
        task=spec.get("task", ""),
        subtasks=spec.get("subtasks", []),
        task_type=spec.get("task_type"),
        domains=spec.get("domains", []),
        abilities=spec.get("abilities", []),
        force_team=spec.get("force_team"),
        no_explore=spec.get("no_explore", False),
    )


def build_and_run(task: str, decomposition: dict,
                  force_team: str = None,
                  no_explore: bool = False) -> dict:
    """B3: 封装 匹配→裁剪→执行计划 全链路

    从 task_decomposer 的输出中提取 domains/pi_types，
    调用 build_team 进行匹配+裁剪，返回带执行计划的完整结果。

    Args:
        task: 原始任务描述
        decomposition: task_decomposer.decompose() 的输出
        force_team: 强制指定团队
        no_explore: 关闭 ε-greedy 探索

    Returns:
        build_team 的结果 + execution_plan 字段
    """
    subtasks = decomposition.get("subtasks", [])
    domains = decomposition.get("domains", [])
    pi_types = decomposition.get("pi_types", [])
    task_type = decomposition.get("main_type")

    team_result = build_team(
        task=task,
        subtasks=subtasks,
        task_type=task_type,
        domains=domains,
        abilities=pi_types,           # match() 内部自动中文→英文转换
        force_team=force_team,
        no_explore=no_explore,
    )

    # 构建执行计划（同 phase 可并行执行的 agent IDs）
    execution_plan = []
    if team_result.get("agents"):
        execution_plan = [a.get("id", "") for a in team_result["agents"]]

    team_result["execution_plan"] = execution_plan
    team_result["subtask_count"] = len(subtasks)
    team_result["task_type"] = task_type or "unknown"
    return team_result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="团队构建器")
    parser.add_argument("--task", default="分析任务", help="任务描述")
    parser.add_argument("--task-type", default=None, help="任务类型")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    matches = match([], [], top_k=3, task_type=args.task_type)
    subtask_types = [args.task_type] if args.task_type else ["general"]
    result = build_team(args.task, [{"type": t} for t in subtask_types],
                        task_type=args.task_type)

    if args.json:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"团队: {result.get('team_zh', result['team_name'])} ({result['team_name']})")
        print(f"匹配度: {result.get('match_score', 0):.1%}")
        print(f"可用: {result['total_available']} → 裁剪后: {len(result['agents'])}")
        print(f"模式: {result['mode']}")
        print(f"Token 预估: {result['token_estimate']}")
        if result['agents']:
            print(f"角色: {', '.join(a['id'] for a in result['agents'][:5])}...")


if __name__ == "__main__":
    main()
