#!/usr/bin/env python3
"""Post-task evolution: collect self-evolution logs and update expert scores.

Usage:
    python3 post-task-evolve.py
"""
import json, os, re
from pathlib import Path
from datetime import datetime
import sys
import sys
import sys
import sys
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXPERT_DIR = Path(__file__).resolve().parent.parent.parent / "references" / "workbuddy-experts"
# TC-20260816-8 修复：评分文件与消费方对齐——此前写 references/expert-scores.json，
# 而 §5/expert-matcher/orchestrator 读 learning-data/expert_scores.json，自学习写入无人消费
SCORES_FILE = Path(__file__).resolve().parent.parent / "references" / "learning-data" / "expert_scores.json"

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
        # TC-20260816-8 修复：score 此前恒 0.5——按反思条目数递增（0.5 基准 + 0.05/条，封顶 1.0）
        total = scores[name].get("count", 0) + info["entries"]
        scores[name]["count"] = total
        scores[name]["score"] = round(min(0.5 + 0.05 * total, 1.0), 4)
        scores[name]["last_updated"] = datetime.now().isoformat()
    SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
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
