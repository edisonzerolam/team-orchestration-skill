#!/usr/bin/env python3
"""Expert score collector v1 — 五维评分采集与聚合

评分维度（外部输入 0-10，内部归一化为 0.0-1.0）:
  - task_completion: 任务完成度
  - delivery_quality: 交付质量
  - response_time: 响应速度
  - user_feedback: 用户反馈
  - collaboration: 协作配合度

Usage:
  python3 score_collector.py --expert foo --dim task_completion --value 8
  python3 score_collector.py --expert foo --batch '{"delivery_quality":7,"user_feedback":9}'
"""
import json, sys, argparse
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration"
SCORES_FILE = SKILL_DIR / "shared" / "expert-scores.json"

DIMENSIONS = ["task_completion", "delivery_quality", "response_time",
              "user_feedback", "collaboration"]


def _load() -> dict:
    if SCORES_FILE.exists():
        try:
            return json.loads(SCORES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return {}


def _save(data: dict):
    from scripts.file_utils import atomic_write
    atomic_write(SCORES_FILE, data)


def _ensure_expert(data: dict, expert_name: str) -> dict:
    if expert_name not in data:
        data[expert_name] = {
            "score": 0.5,
            "count": 0,
            "last_updated": datetime.now().isoformat(),
            "dimensions": {d: {"avg": 0.0, "n": 0} for d in DIMENSIONS},
        }
    if "dimensions" not in data[expert_name]:
        data[expert_name]["dimensions"] = {d: {"avg": 0.0, "n": 0} for d in DIMENSIONS}
    for d in DIMENSIONS:
        if d not in data[expert_name]["dimensions"]:
            data[expert_name]["dimensions"][d] = {"avg": 0.0, "n": 0}
    return data[expert_name]


def record_score(expert_name: str, dimension: str, value: float) -> dict:
    """记录单维评分。value 为 0-10 原始值，内部归一化为 0.0-1.0。"""
    if dimension not in DIMENSIONS:
        raise ValueError(f"Unknown dimension: {dimension}. Valid: {DIMENSIONS}")
    norm = max(0.0, min(1.0, value / 10.0))

    data = _load()
    expert = _ensure_expert(data, expert_name)
    dim = expert["dimensions"][dimension]
    old_avg = dim["avg"]
    old_n = dim["n"]
    dim["n"] = old_n + 1
    dim["avg"] = round((old_avg * old_n + norm) / dim["n"], 4)
    expert["count"] += 1
    _recompute_aggregate(expert)
    expert["last_updated"] = datetime.now().isoformat()
    _save(data)
    return {"expert": expert_name, "dimension": dimension,
            "recorded_value": norm, "new_avg": dim["avg"], "total_count": dim["n"]}


def record_batch(expert_name: str, scores: dict) -> dict:
    """批量记录多维评分。scores: {dimension: value_0_10, ...}"""
    results = {}
    data = _load()
    expert = _ensure_expert(data, expert_name)
    for dim, raw_val in scores.items():
        if dim not in DIMENSIONS:
            continue
        norm = max(0.0, min(1.0, raw_val / 10.0))
        d = expert["dimensions"][dim]
        old_avg = d["avg"]
        old_n = d["n"]
        d["n"] = old_n + 1
        d["avg"] = round((old_avg * old_n + norm) / d["n"], 4)
        expert["count"] += 1
        results[dim] = {"recorded": norm, "new_avg": d["avg"]}
    _recompute_aggregate(expert)
    expert["last_updated"] = datetime.now().isoformat()
    _save(data)
    return {"expert": expert_name, "results": results}


def _recompute_aggregate(expert: dict):
    """从五维均值计算综合分（等权平均）"""
    dims = expert.get("dimensions", {})
    valid = [d["avg"] for d in dims.values() if d["n"] > 0]
    if valid:
        expert["score"] = round(sum(valid) / len(valid), 4)
    else:
        expert["score"] = 0.5


def get_profile(expert_name: str) -> dict:
    """查询某专家的完整评分档案"""
    data = _load()
    return data.get(expert_name, {})


def get_dimension_avg(expert_name: str, dimension: str) -> float:
    """查询某维度的均值"""
    profile = get_profile(expert_name)
    dim = profile.get("dimensions", {}).get(dimension, {})
    return dim.get("avg", 0.5)


def get_all_scores() -> dict:
    """返回所有专家的综合分映射"""
    data = _load()
    return {k: {"score": v.get("score", 0.5), "count": v.get("count", 0)}
            for k, v in data.items()}


def main():
    ap = argparse.ArgumentParser(description="专家评分采集器 v1")
    ap.add_argument("--expert", required=True, help="专家名称")
    ap.add_argument("--dim", default=None, choices=DIMENSIONS, help="评分维度")
    ap.add_argument("--value", type=float, default=None, help="评分值 (0-10)")
    ap.add_argument("--batch", default=None, help='批量评分 JSON: {"dim": val}')
    ap.add_argument("--query", action="store_true", help="查询专家档案")
    args = ap.parse_args()

    if args.query:
        profile = get_profile(args.expert)
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    elif args.batch:
        scores = json.loads(args.batch)
        result = record_batch(args.expert, scores)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.dim and args.value is not None:
        result = record_score(args.expert, args.dim, args.value)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
