#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Health Monitor v2.0 — Agent 健康检查 + 自愈集成

检测 Agent 是否存活、超时、失败，自动触发自愈管道。

用法:
  python3 health-monitor.py check <team_id>       # 检查团队健康
  python3 health-monitor.py check <team_id> --auto-heal  # 检查+自愈
  python3 health-monitor.py watch <team_id>        # 持续监控(每5s)
  python3 health-monitor.py summary                # 所有团队汇总
"""
import json, sys, time, argparse
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TEAM_BRAIN_ROOT = SKILL_DIR / "shared" / "team-brain"
HEARTBEAT_TIMEOUT = 120


def load_team_status(team_id):
    status_file = TEAM_BRAIN_ROOT / "teams" / f"{team_id}.json"
    if not status_file.exists():
        return None
    with open(status_file, encoding="utf-8") as f:
        return json.load(f)


def check_agent_health(agent, now=None):
    now = now or datetime.now(timezone.utc)
    last_heartbeat = agent.get("last_heartbeat")
    status = agent.get("status", "unknown")
    result = {
        "id": agent.get("id", "unknown"),
        "role": agent.get("role", ""),
        "status": status,
        "last_heartbeat": last_heartbeat,
        "is_alive": False,
        "is_stale": True,
        "is_failed": status in ("failed", "failed_with_error"),
    }
    if last_heartbeat:
        try:
            last = datetime.fromisoformat(last_heartbeat)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            seconds_since = (now - last).total_seconds()
            result["is_alive"] = seconds_since < HEARTBEAT_TIMEOUT
            result["is_stale"] = seconds_since >= HEARTBEAT_TIMEOUT
            result["seconds_ago"] = int(seconds_since)
        except (ValueError, TypeError):
            result["seconds_ago"] = None
    return result


def check_team_health(team_id):
    status = load_team_status(team_id)
    if not status:
        return {"team_id": team_id, "error": "not_found", "agents": []}
    now = datetime.now(timezone.utc)
    agents = [check_agent_health(a, now) for a in status.get("agents", [])]
    alive = sum(1 for a in agents if a["is_alive"])
    stale = sum(1 for a in agents if a["is_stale"])
    failed = sum(1 for a in agents if a["is_failed"])
    return {
        "team_id": team_id,
        "phase": status.get("phase", ""),
        "total_agents": len(agents),
        "alive": alive,
        "stale": stale,
        "failed": failed,
        "healthy": stale == 0 and failed == 0,
        "agents": agents,
        "checked_at": now.isoformat(),
    }


def trigger_self_heal(team_id, agent_id, error_context=""):
    """触发自愈管道"""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from self_heal import SelfHealPipeline
        pipeline = SelfHealPipeline(team_id, agent_id)
        ctx = {"agent_id": agent_id, "error": error_context or "heartbeat_timeout",
               "last_heartbeat": None, "elapsed_ms": HEARTBEAT_TIMEOUT * 1000,
               "timeout_ms": HEARTBEAT_TIMEOUT * 1000}
        result = pipeline.run(ctx)
        return result
    except Exception as e:
        return {"status": "heal_failed", "error": str(e)}


def watch_team(team_id, interval=5, auto_heal=False):
    """持续监控团队健康状态，可选择自动自愈"""
    while True:
        result = check_team_health(team_id)
        if result.get("error"):
            print(f"[{datetime.now(timezone.utc).isoformat()}] {team_id}: ERROR {result['error']}")
            time.sleep(interval)
            continue
        status = "HEALTHY" if result["healthy"] else f"ISSUES (stale={result['stale']}, failed={result['failed']})"
        print(f"[{result['checked_at']}] {team_id}: {status}")
        if not result["healthy"] and auto_heal:
            for a in result["agents"]:
                if not a["is_alive"]:
                    heal_r = trigger_self_heal(team_id, a["id"], f"heartbeat_timeout:{a.get('seconds_ago','?')}s")
                    print(f"  → self-heal {a['id']}: {heal_r.get('status','unknown')}")
        sys.stdout.flush()
        time.sleep(interval)


def summarize():
    teams_dir = TEAM_BRAIN_ROOT / "teams"
    if not teams_dir.exists():
        print(json.dumps({"teams": [], "error": "no_teams_dir"}, ensure_ascii=False))
        return
    results = [check_team_health(f.stem) for f in sorted(teams_dir.glob("*.json"))]
    healthy = sum(1 for r in results if r.get("healthy"))
    print(json.dumps({
        "total_teams": len(results),
        "healthy_teams": healthy,
        "unhealthy_teams": len(results) - healthy,
        "teams": results,
    }, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Health Monitor v2.0")
    ap.add_argument("command", choices=["check", "watch", "summary"])
    ap.add_argument("team_id", nargs="?", default="")
    ap.add_argument("--interval", type=int, default=5)
    ap.add_argument("--auto-heal", action="store_true", help="自动触发自愈")
    args = ap.parse_args()

    if args.command == "summary":
        summarize()
    elif args.command == "check":
        if not args.team_id:
            print("Error: team_id required")
            sys.exit(1)
        result = check_team_health(args.team_id)
        if not result.get("agents"):
            print(json.dumps({"error": f"Team '{args.team_id}' not found"}, ensure_ascii=False))
            sys.exit(1)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["healthy"] and args.auto_heal:
            for a in result["agents"]:
                if not a["is_alive"]:
                    heal_r = trigger_self_heal(args.team_id, a["id"], f"heartbeat_timeout:{a.get('seconds_ago','?')}s")
                    print(f"  → self-heal {a['id']}: {heal_r.get('status','unknown')}")
    elif args.command == "watch":
        if not args.team_id:
            print("Error: team_id required")
            sys.exit(1)
        watch_team(args.team_id, args.interval, args.auto_heal)


if __name__ == "__main__":
    main()
