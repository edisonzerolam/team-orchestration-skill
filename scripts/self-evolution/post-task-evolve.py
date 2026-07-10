#!/usr/bin/env python3
"""Post-task evolution: collect self-evolution logs and update expert scores.

支持两种模式:
  1. 日志采集模式: python3 post-task-evolve.py
  2. 评分采集模式: python3 post-task-evolve.py --score --expert foo --dim delivery_quality --value 8

Usage:
    python3 post-task-evolve.py
    python3 post-task-evolve.py --score --expert foo --batch '{"delivery_quality":7,"user_feedback":9}'
"""
import json, os, re, sys, argparse
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import score_collector as sc

EXPERT_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "references" / "workbuddy-experts"
SCORES_FILE = EXPERT_DIR.parent.parent / "shared" / "expert-scores.json"

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

def score_subtask(expert_name: str, dimension: str, value: float) -> dict:
    """子任务完成后采集单维评分（供 orchestrator 回调使用）"""
    return sc.record_score(expert_name, dimension, value)

def score_subtask_batch(expert_name: str, scores: dict) -> dict:
    """子任务完成后批量采集多维评分"""
    return sc.record_batch(expert_name, scores)

def main():
    ap = argparse.ArgumentParser(description="后任务进化引擎")
    ap.add_argument("--score", action="store_true", help="评分采集模式")
    ap.add_argument("--expert", default=None, help="专家名称")
    ap.add_argument("--dim", default=None, choices=sc.DIMENSIONS, help="评分维度")
    ap.add_argument("--value", type=float, default=None, help="评分值 (0-10)")
    ap.add_argument("--batch", default=None, help='批量评分 JSON')
    args = ap.parse_args()

    if args.score:
        if args.batch and args.expert:
            result = score_subtask_batch(args.expert, json.loads(args.batch))
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.dim and args.value is not None and args.expert:
            result = score_subtask(args.expert, args.dim, args.value)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("评分模式需 --expert + (--dim --value 或 --batch)")
        return

    # 默认模式：日志采集
    logs = collect_logs()
    scores = load_scores()
    scores = update_scores(logs, scores)
    print(f"已检查 {len(logs)} 个专家的日志")
    print(f"已更新 {len(scores)} 个专家的评分")

if __name__ == "__main__":
    main()
