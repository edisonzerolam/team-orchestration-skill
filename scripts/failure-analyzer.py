#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Failure Analyzer v1.0 — 失败模式聚合报表

从 repair-records 中读取历史修复记录，按故障类型/动作/Agent/时序聚合，
输出结构化报告供 dashboard 或 CLI 使用。

用法:
  python3 failure-analyzer.py summary              # 综合报表
  python3 failure-analyzer.py by-type              # 按故障类型
  python3 failure-analyzer.py by-agent             # 按 Agent
  python3 failure-analyzer.py timeline             # 时序热力图
"""
import json, collections, datetime
from pathlib import Path

from scripts._paths import REPAIR_DIR as _REPAIR_DIR
from scripts._fault_types import FAULT_TYPES as _FAULT_TYPES

REPAIR_DIR = _REPAIR_DIR


def load_all() -> list[dict]:
    result = []
    if not REPAIR_DIR.exists():
        return result
    for f in sorted(REPAIR_DIR.glob("*.json")):
        try:
            records = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(records, list):
                for r in records:
                    r["_source"] = f.stem
                    r["_source_file"] = f.name
                result.extend(records)
        except Exception:
            pass
    return result


def _safe_ts(record: dict) -> float:
    ts = record.get("timestamp", record.get("created_at", 0))
    if isinstance(ts, (int, float)):
        return ts
    if isinstance(ts, str):
        try:
            dt = datetime.datetime.fromisoformat(ts)
            return dt.timestamp()
        except (ValueError, TypeError):
            return 0
    return 0


def _get_fault_type_info(ft: str) -> dict:
    info = _FAULT_TYPES.get(ft, {})
    return {"name": info.get("name", ft),
            "recoverable": info.get("recoverable", False),
            "severity": info.get("severity", 0)}


def _report_by_type(records: list[dict]) -> dict:
    by_type = collections.Counter(r.get("fault_type", "unknown") for r in records)
    by_type_recoverable = {}
    for ft in by_type:
        by_type_recoverable[ft] = _get_fault_type_info(ft)
    total = len(records)
    return {
        "total": total,
        "types": sorted([
            {"code": ft, "name": by_type_recoverable.get(ft, {}).get("name", ft),
             "count": cnt, "pct": round(cnt / total * 100, 1) if total else 0,
             "recoverable": by_type_recoverable.get(ft, {}).get("recoverable", False),
             "severity": by_type_recoverable.get(ft, {}).get("severity", 0)}
            for ft, cnt in by_type.most_common()
        ], key=lambda x: x["count"], reverse=True),
    }


def _report_by_agent(records: list[dict]) -> dict:
    by_agent = collections.Counter(r.get("target", "unknown") for r in records)
    by_agent_detail = {}
    for r in records:
        agent = r.get("target", "unknown")
        if agent not in by_agent_detail:
            by_agent_detail[agent] = {"total": 0, "types": collections.Counter()}
        by_agent_detail[agent]["total"] += 1
        by_agent_detail[agent]["types"][r.get("fault_type", "unknown")] += 1
    total = len(records)
    agents = []
    for agent, cnt in by_agent.most_common(20):
        detail = by_agent_detail.get(agent, {})
        agents.append({
            "agent": agent,
            "total_failures": cnt,
            "pct": round(cnt / total * 100, 1) if total else 0,
            "top_types": [{"type": ft, "count": c}
                          for ft, c in detail.get("types", collections.Counter()).most_common(3)],
        })
    return {"total": total, "agents": agents}


def _report_timeline(records: list[dict]) -> dict:
    if not records:
        return {"total": 0, "daily": []}
    daily = collections.Counter()
    for r in records:
        ts = _safe_ts(r)
        if ts:
            dt = datetime.datetime.fromtimestamp(ts)
            key = dt.strftime("%Y-%m-%d")
            daily[key] += 1
    sorted_days = sorted(daily.items())
    return {
        "total": len(records),
        "daily": [{"date": d, "count": c} for d, c in sorted_days],
        "avg_per_day": round(len(records) / max(len(sorted_days), 1), 1),
    }


def summary():
    records = load_all()
    result = {
        "total_records": len(records),
        "by_type": _report_by_type(records),
        "by_agent": _report_by_agent(records),
        "timeline": _report_timeline(records),
        "generated_at": datetime.datetime.now().isoformat(),
    }
    return result


def main():
    ap = argparse.ArgumentParser(description="Failure Analyzer v1.0")
    ap.add_argument("mode", nargs="?", default="summary",
                    choices=["summary", "by-type", "by-agent", "timeline"])
    args = ap.parse_args()
    records = load_all()
    if args.mode == "summary":
        result = summary()
    elif args.mode == "by-type":
        result = _report_by_type(records)
    elif args.mode == "by-agent":
        result = _report_by_agent(records)
    elif args.mode == "timeline":
        result = _report_timeline(records)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import argparse
    main()
