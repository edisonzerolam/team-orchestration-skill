#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthesis Check — 专家共识确认

在执行阶段完成后，收集所有参与专家的共识确认，
检查是否有分歧或问题需要解决。

用法:
  python3 synthesis-check.py <team_id> <final_report_path> [--timeout=300]
"""
import json
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TEAM_BRAIN_ROOT = SKILL_DIR.parent / "shared" / "team-brain"
DEFAULT_TIMEOUT = 300


def load_team(team_id):
    team_file = TEAM_BRAIN_ROOT / "teams" / f"{team_id}.json"
    if not team_file.exists():
        return {}
    with open(team_file, encoding="utf-8") as f:
        return json.load(f)


def load_final_report(path):
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def parse_expert_response(text):
    """解析专家回应，返回 (vote, detail)。vote: agree / concern / object"""
    if not text:
        return "agree", "No response"
    t = text.strip().lower()
    if any(kw in t for kw in ("object", "reject", "不同意", "反对")):
        return "object", t[:200]
    if any(kw in t for kw in ("concern", "担心", "建议修改")):
        return "concern", t[:200]
    return "agree", t[:200]


def collect_consensus(team, report_text, timeout):
    """收集各专家共识（模拟，实际应用需集成 agent 通信）"""
    results = {}
    agents = team.get("agents", [])
    deadline = time.time() + timeout

    for agent in agents:
        aid = agent.get("id", "unknown")
        elapsed = deadline - time.time()
        if elapsed <= 0:
            results[aid] = {"vote": "concern", "detail": "Timeout - no response"}
            continue
        # 模拟等待（实际应通过 task 通信）
        vote, detail = parse_expert_response(agent.get("vote_text", ""))
        results[aid] = {"vote": vote, "detail": detail, "role": agent.get("role", "")}

    return results


def generate_report(team_id, results):
    """生成共识检查报告"""
    votes = [r["vote"] for r in results.values()]
    agree = sum(1 for v in votes if v == "agree")
    concerns = sum(1 for v in votes if v == "concern")
    objects = sum(1 for v in votes if v == "object")
    total = len(votes)

    if objects > 0:
        conclusion = "returned"
    elif concerns > 0:
        conclusion = "delivered_with_concerns"
    else:
        conclusion = "delivered"

    report_dir = SKILL_DIR / "synthesis"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"{team_id}-consensus-check.md"

    lines = [
        f"# Consensus Check: {team_id}",
        f"**Date**: {datetime.now().isoformat()}",
        f"**Experts**: {total}",
        f"**Result**: {conclusion}",
        f"",
        f"## Vote Summary",
        f"| Vote | Count |",
        f"|------|-------|",
        f"| Agree | {agree} |",
        f"| Concern | {concerns} |",
        f"| Object | {objects} |",
        f"",
    ]
    for aid, r in results.items():
        lines.append(f"### {aid} ({r.get('role', 'N/A')})")
        lines.append(f"- Vote: {r['vote']}")
        lines.append(f"- Detail: {r['detail']}")
        lines.append("")

    report_file.write_text("\n".join(lines), encoding="utf-8")
    return conclusion, str(report_file)


def main():
    ap = argparse.ArgumentParser(description="Expert consensus confirmation")
    ap.add_argument("team_id", help="Team ID")
    ap.add_argument("final_report_path", help="Path to final report")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = ap.parse_args()

    team = load_team(args.team_id)
    report_text = load_final_report(args.final_report_path)
    results = collect_consensus(team, report_text, args.timeout)
    conclusion, report_path = generate_report(args.team_id, results)

    print(json.dumps({
        "conclusion": conclusion,
        "team_id": args.team_id,
        "experts": len(results),
        "report_path": report_path,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
