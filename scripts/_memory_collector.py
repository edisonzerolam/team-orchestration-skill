#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Memory Bridge v1.0 — team-orchestration → Engram 持久化记忆桥接

收集 orchestration 执行结果、自愈事件、专家匹配记录，输出结构化 JSON，
供 AI agent 调用 engram_mem_save 写入持久化记忆。

用法:
  python3 scripts/memory-bridge.py collect-last        # 收集最近一次执行
  python3 scripts/memory-bridge.py collect-heals       # 收集自愈事件
  python3 scripts/memory-bridge.py collect-matches     # 收集专家匹配记录
  python3 scripts/memory-bridge.py session-summary     # 会话摘要
  python3 scripts/memory-bridge.py resume-context      # 恢复上下文（最近状态）
"""
import json, datetime, collections, time
from pathlib import Path
from typing import Optional

SKILL_DIR = Path(__file__).parent.parent
STATE_DIR = SKILL_DIR / "shared" / "team-brain"
CB_DIR = STATE_DIR / "circuit-breakers"
REPAIR_DIR = STATE_DIR / "repair-records"
TEAMS_DIR = STATE_DIR / "teams"
SCORES_FILE = SKILL_DIR / "shared" / "expert-scores.json"


def _safe_ts(record: dict, key: str = "timestamp") -> str:
    ts = record.get(key, record.get("created_at", ""))
    if isinstance(ts, (int, float)):
        return datetime.datetime.fromtimestamp(ts).isoformat()
    return str(ts) if ts else ""


def collect_self_heal_events(limit: int = 20) -> list[dict]:
    """读取最近 N 条自愈事件"""
    events = []
    if not REPAIR_DIR.exists():
        return events
    for f in sorted(REPAIR_DIR.glob("*.json"), reverse=True):
        try:
            records = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(records, list):
                for r in records[-limit:]:
                    events.append({
                        "type": "self_heal",
                        "fault_type": r.get("fault_type", ""),
                        "action": r.get("action", ""),
                        "target": r.get("target", ""),
                        "success": r.get("success", False),
                        "timestamp": _safe_ts(r),
                        "source": f.name,
                    })
        except Exception:
            pass
    return events[-limit:]


def collect_circuit_breaker_states() -> list[dict]:
    """收集所有熔断器状态"""
    states = []
    if not CB_DIR.exists():
        return states
    for f in sorted(CB_DIR.glob("*.json")):
        try:
            cb = json.loads(f.read_text(encoding="utf-8"))
            states.append({
                "type": "circuit_breaker",
                "name": cb.get("name", f.stem),
                "state": cb.get("state", "UNKNOWN"),
                "failure_count": cb.get("failure_count", 0),
                "success_count": cb.get("success_count", 0),
                "timestamp": _safe_ts(cb),
            })
        except Exception:
            pass
    return states


def collect_team_health() -> list[dict]:
    """收集团队健康状态"""
    health = []
    if not TEAMS_DIR.exists():
        return health
    for f in sorted(TEAMS_DIR.glob("*.json")):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
            agents = t.get("agents", [])
            health.append({
                "type": "team_health",
                "team": t.get("name", f.stem),
                "total_agents": len(agents),
                "alive": sum(1 for a in agents if a.get("status") != "dead"),
                "dead": sum(1 for a in agents if a.get("status") == "dead"),
                "timestamp": _safe_ts(t),
            })
        except Exception:
            pass
    return health


def collect_expert_scores(top_n: int = 10) -> list[dict]:
    """收集评分最高的专家"""
    if not SCORES_FILE.exists():
        return []
    try:
        scores = json.loads(SCORES_FILE.read_text(encoding="utf-8"))
        if isinstance(scores, dict):
            sorted_scores = sorted(scores.items(), key=lambda x: x[1].get("composite", 0) if isinstance(x[1], dict) else 0, reverse=True)
            return [{
                "type": "expert_score",
                "expert": name,
                "composite_score": data.get("composite", 0) if isinstance(data, dict) else data,
            } for name, data in sorted_scores[:top_n]]
    except Exception:
        pass
    return []


_summary_cache = None
_summary_cache_ts = 0
_SUMMARY_CACHE_TTL = 600


def make_session_summary(force_refresh: bool = False) -> dict:
    """生成当前完整会话摘要（L0 缓存 600s + 并行 collector）"""
    global _summary_cache, _summary_cache_ts
    now = time.time()
    if not force_refresh and _summary_cache and (now - _summary_cache_ts) < _SUMMARY_CACHE_TTL:
        return _summary_cache

    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {
            pool.submit(collect_self_heal_events, 5): "heals",
            pool.submit(collect_circuit_breaker_states): "cbs",
            pool.submit(collect_team_health): "health",
            pool.submit(collect_expert_scores, 5): "scores",
        }
        results = {}
        for fut in as_completed(futs):
            key = futs[fut]
            results[key] = fut.result()

    cbs = results.get("cbs", [])
    health = results.get("health", [])
    summary = {
        "type": "session_summary",
        "total_teams": len(health),
        "total_agents": sum(h["total_agents"] for h in health),
        "alive_agents": sum(h["alive"] for h in health),
        "dead_agents": sum(h["dead"] for h in health),
        "open_circuit_breakers": len([cb for cb in cbs if cb["state"] == "OPEN"]),
        "recent_heal_events": len(results.get("heals", [])),
        "top_experts": results.get("scores", []),
        "timestamp": datetime.datetime.now().isoformat(),
    }

    _summary_cache = summary
    _summary_cache_ts = now
    return summary


def collect_last_orchestration() -> Optional[dict]:
    """从 orchestrator 最后执行记录收集数据"""
    ledger_file = SKILL_DIR / "shared" / "token-ledger.json"
    if not ledger_file.exists():
        return None
    try:
        ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
        if isinstance(ledger, list) and ledger:
            last = ledger[-1]
            return {
                "type": "orchestration",
                "task": last.get("task", ""),
                "total_tokens": last.get("tokens_used", 0),
                "subtasks": last.get("subtask_count", 0),
                "status": last.get("status", ""),
                "timestamp": _safe_ts(last),
            }
    except Exception:
        pass
    return None


def make_resume_context() -> dict:
    """生成恢复上下文（用于新会话启动时恢复工作状态）"""
    summary = make_session_summary()
    last_orch = collect_last_orchestration()
    result = {
        "summary": summary,
        "last_orchestration": last_orch,
    }
    if summary["open_circuit_breakers"] > 0:
        result["attention"] = f"有 {summary['open_circuit_breakers']} 个熔断器 OPEN，建议优先排查"
    if summary["dead_agents"] > 0:
        result["attention"] = result.get("attention", "") + \
            f"有 {summary['dead_agents']} 个 Agent 死亡"
    return result


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Memory Bridge v1.0")
    ap.add_argument("mode", choices=["collect-last", "collect-heals", "collect-matches",
                                     "session-summary", "resume-context"])
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    if args.mode == "collect-last":
        r = collect_last_orchestration()
        result = r or {"error": "无执行记录"}
    elif args.mode == "collect-heals":
        result = {"events": collect_self_heal_events(args.limit)}
    elif args.mode == "collect-matches":
        result = {"experts": collect_expert_scores(args.limit)}
    elif args.mode == "session-summary":
        result = make_session_summary()
    elif args.mode == "resume-context":
        result = make_resume_context()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
