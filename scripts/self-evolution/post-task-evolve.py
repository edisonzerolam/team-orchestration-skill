#!/usr/bin/env python3
"""Post-task evolution: collect self-evolution logs and update expert scores.

Usage:
    python3 post-task-evolve.py
"""
import json, os, re
from pathlib import Path
from datetime import datetime

EXPERT_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "references" / "workbuddy-experts"
SCORES_FILE = EXPERT_DIR.parent / "expert-scores.json"

def collect_logs():
    logs = {}
    if not EXPERT_DIR.exists():
        return logs
    for plugin_dir in EXPERT_DIR.iterdir():
        if not plugin_dir.is_dir():
            continue
        log_file = plugin_dir / "self-evolution-log.md"
        if log_file.exists():
            content = log_file.read_text(encoding="utf-8")
            entries = re.findall(r"## 执行反思.*?(?=##|$)", content, re.DOTALL)
            if entries:
                logs[plugin_dir.name] = {
                    "entries": len(entries),
                    "last_entry": entries[-1][:200] if entries else "",
                }
    return logs

def load_scores():
    if SCORES_FILE.exists():
        return json.loads(SCORES_FILE.read_text(encoding="utf-8"))
    return {}

def update_scores(logs: dict, scores: dict):
    for name, info in logs.items():
        if name not in scores:
            scores[name] = {"score": 0.5, "count": 0}
        scores[name]["count"] += info["entries"]
        scores[name]["last_updated"] = datetime.now().isoformat()
    SCORES_FILE.write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")
    return scores

def main():
    logs = collect_logs()
    scores = load_scores()
    scores = update_scores(logs, scores)
    print(f"已检查 {len(logs)} 个专家的日志")
    print(f"已更新 {len(scores)} 个专家的评分")

if __name__ == "__main__":
    main()
