#!/usr/bin/env python3
"""Expert matching engine for team-orchestration.

Matches task decomposition results against the WorkBuddy expert pool.
"""
import json, sys, os, argparse
from pathlib import Path

EXPERT_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "references" / "workbuddy-experts"

def load_all_experts():
    experts = {}
    if not EXPERT_DIR.exists():
        return experts
    for plugin_dir in sorted(EXPERT_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue
        pj = plugin_dir / "plugin.json"
        if not pj.exists():
            continue
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        agents_dir = plugin_dir / "agents"
        agent_count = len(list(agents_dir.glob("*.md"))) if agents_dir.exists() else 0
        experts[data.get("name", plugin_dir.name)] = {
            "name": data.get("name", ""),
            "display_zh": data.get("displayName", {}).get("zh", ""),
            "description_zh": data.get("displayDescription", {}).get("zh", ""),
            "category_id": data.get("categoryId", ""),
            "expert_type": data.get("expertType", ""),
            "lead_name": data.get("members", [{}])[0].get("name", {}).get("zh", "") if data.get("members") else "",
            "agent_count": agent_count,
        }
    return experts

def match(experts: dict, domains: list, top_k: int = 3) -> list:
    scored = []
    for name, info in experts.items():
        score = 0.0
        for domain in domains:
            cat_id = domain.split("-", 1)[-1].lower() if "-" in domain else domain.lower()
            if cat_id in info.get("category_id", "").lower():
                score += 0.6
            if cat_id in info.get("description_zh", "").lower():
                score += 0.3
            if cat_id in info.get("display_zh", "").lower():
                score += 0.1
        score = min(score, 1.0)
        if score > 0.2:
            scored.append((score, info))
    scored.sort(key=lambda x: -x[0])
    return scored[:top_k]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", nargs="+", default=[])
    ap.add_argument("--task", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()
    experts = load_all_experts()
    if args.domains:
        matches = match(experts, args.domains, args.top_k)
    else:
        from task_decomposer import decompose
        result = decompose(args.task)
        matches = match(experts, result["domains"], args.top_k)
    if args.json:
        print(json.dumps([{"score": round(s, 2), **m} for s, m in matches], ensure_ascii=False, indent=2))
    else:
        print(f"专家池: {len(experts)} 个专家团")
        print(f"匹配结果 (Top {len(matches)}):")
        for score, info in matches:
            print(f"  [{info.get('category_id','')}] {info.get('display_zh','')} ({info.get('agent_count',0)} agents) — 匹配度: {score:.0%}")

if __name__ == "__main__":
    main()
