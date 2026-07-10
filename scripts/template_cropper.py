"""模板动态裁剪 — 按子任务类型裁剪团队

用法:
  from template_cropper import crop_team, CroppingConfig

  cropped = crop_team("investment-masters-team", subtasks)
"""

import json
import math
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SHARED_DIR = SKILL_DIR / "shared"
EXPERT_DIR = SKILL_DIR / "references" / "workbuddy-experts"
CROPPING_CONFIG_PATH = SHARED_DIR / "cropping-config.json"

# 子任务类型 → 所需角色关键词
SUBTASK_ROLE_MAP = {
    "information_retrieval": ["researcher", "analyst", "data", "search", "research"],
    "analysis_judgment": ["analyst", "strategist", "evaluator", "assessor", "researcher", "valuation"],
    "creation_generation": ["writer", "designer", "creator", "artist", "developer", "creative"],
    "decision_execution": ["lead", "manager", "executor", "implementer", "operator"],
    "collaboration_discussion": ["lead", "moderator", "reviewer", "sceptic", "debater"],
    "quality_verification": ["reviewer", "tester", "auditor", "inspector", "qa"],
}

_SUBTASK_TYPE_ALIASES = {
    "quality_validation": "quality_verification",
    "collaboration_discussion": "collaboration_discussion",
}


def _normalize_type(t: str) -> str:
    return _SUBTASK_TYPE_ALIASES.get(t, t)


def _load_cropping_config() -> dict:
    if CROPPING_CONFIG_PATH.exists():
        try:
            data = json.loads(CROPPING_CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("teams", data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return {}


def _get_agents_for_team(team_name: str) -> list:
    team_dir = EXPERT_DIR / team_name
    agents_dir = team_dir / "agents"
    if not agents_dir.exists():
        return []
    agents = []
    for f in sorted(agents_dir.glob("*.md")):
        stem = f.stem
        content = f.read_text(encoding="utf-8", errors="replace")[:2000]
        agents.append({
            "id": stem,
            "file": str(f),
            "description": content[:300],
        })
    return agents


def _score_agent(agent: dict, needed_roles: set) -> float:
    desc = agent.get("description", "").lower()
    score = 0.0
    for kw in needed_roles:
        if kw.lower() in desc or kw.lower() in agent["id"].lower():
            score += 1.0
    return score


def crop_team(team_name: str, subtask_types: list,
              config_override: dict = None) -> dict:
    """裁剪团队

    Args:
        team_name: 团队目录名
        subtask_types: 子任务类型列表 (如 ["analysis_judgment", "creation_generation"])
        config_override: 可选覆盖 cropping-config.json 中的配置

    Returns:
        {"agents": [...], "total": N, "cropped": N, "mode": "standard"|"economy"|"no_crop"}
    """
    configs = _load_cropping_config()
    team_config = config_override or configs.get(team_name, {})

    agents = _get_agents_for_team(team_name)
    agent_count = len(agents)

    if agent_count <= 3 or not team_config:
        return {
            "agents": agents,
            "total": agent_count,
            "cropped": agent_count,
            "mode": "no_crop",
        }

    base_size = team_config.get("base_size", 5)
    min_size = team_config.get("min_size", 3)
    elastic_ratio = team_config.get("elastic_ratio", 0.2)
    role_priority = team_config.get("role_priority", [])

    base_size = max(min_size, min(base_size, agent_count))

    normalized_types = [_normalize_type(t) for t in subtask_types]
    needed_roles = set()
    for t in normalized_types:
        needed_roles.update(SUBTASK_ROLE_MAP.get(t, []))

    if not needed_roles:
        needed_roles = set(role_priority)

    scored = []
    for agent in agents:
        s = _score_agent(agent, needed_roles)
        for i, rp in enumerate(role_priority):
            if rp.lower() in agent["id"].lower():
                s += (len(role_priority) - i) * 0.1
        scored.append((s, agent))

    scored.sort(key=lambda x: -x[0])
    elastic_slots = max(0, math.ceil(base_size * elastic_ratio))
    target = min(base_size + elastic_slots, agent_count)
    target = max(target, min_size)
    selected = [a for _, a in scored[:target]]

    mode = "economy" if target <= base_size else "standard"
    return {
        "agents": selected,
        "total": agent_count,
        "cropped": target,
        "mode": mode,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="模板动态裁剪")
    parser.add_argument("team_name", help="团队名")
    parser.add_argument("--subtask-types", nargs="+",
                        default=["analysis_judgment"],
                        help="子任务类型列表")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    result = crop_team(args.team_name, args.subtask_types)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"团队: {args.team_name}")
        print(f"子任务类型: {args.subtask_types}")
        print(f"总数: {result['total']} → 裁剪后: {result['cropped']}")
        print(f"模式: {result['mode']}")
        for a in result["agents"]:
            print(f"  - {a['id']}")


if __name__ == "__main__":
    main()
