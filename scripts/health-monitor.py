#!/usr/bin/env python3
"""health-monitor.py - Team/agent health monitoring (P0.11, v2.6 rewrite).

Replaces a structurally-corrupted prior file. Monitors agent liveness via
heartbeat timestamps and reports team health.
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

TEAM_BRAIN_ROOT = Path(__file__).resolve().parent.parent.parent / "shared" / "team-brain"
HEARTBEAT_TIMEOUT = 120  # seconds without heartbeat => considered dead


def load_team_status(team_id):
    status_file = TEAM_BRAIN_ROOT / "teams" / f"{team_id}.json"
    if not status_file.exists():
        return None
    with open(status_file, encoding="utf-8") as f:
        return json.load(f)


def check_agent_health(agent, now=None):
    if now is None:
        now = datetime.now().astimezone()  # TC-20260816-8：aware 基准，防 naive-aware 相减 TypeError
    last_heartbeat = agent.get("last_heartbeat")
    status = agent.get("status", "unknown")
    if last_heartbeat:
        try:
            last = datetime.fromisoformat(last_heartbeat)
            if last.tzinfo is None:
                last = last.astimezone()  # naive 心跳按本地时区解释
            seconds_since = (now - last).total_seconds()
            is_alive = seconds_since < HEARTBEAT_TIMEOUT
            return {
                "id": agent.get("id"),
                "role": agent.get("role"),
                "status": status,
                "last_heartbeat": last_heartbeat,
                "seconds_ago": int(seconds_since),
                "is_alive": is_alive,
                "is_stale": seconds_since > HEARTBEAT_TIMEOUT,
                "is_failed": status in ("failed", "failed_with_error"),
            }
        except Exception:
            pass  # 心跳解析失败：按未知处理（区别于"真死亡"——seconds_ago=None）
    return {
        "id": agent.get("id"),
        "role": agent.get("role"),
        "status": status,
        "last_heartbeat": last_heartbeat,
        "seconds_ago": None,
        "is_alive": False,
        "is_stale": True,
        "is_failed": status in ("failed", "failed_with_error"),
    }


def check_team_health(team_id):
    status = load_team_status(team_id)
    if not status:
        return {"team_id": team_id, "exists": False, "agents": []}
    agents = status.get("agents", status.get("members", []))
    return {
        "team_id": team_id,
        "exists": True,
        "agents": [check_agent_health(a) for a in agents],
    }


def summary():
    teams_dir = TEAM_BRAIN_ROOT / "teams"
    if not teams_dir.exists():
        return {"teams": []}
    out = []
    for f in sorted(teams_dir.glob("*.json")):
        out.append(check_team_health(f.stem))
    return {"teams": out}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Health monitor")
    ap.add_argument("action", choices=["check", "watch", "summary"])
    ap.add_argument("team_id", nargs="?", default=None)
    ap.add_argument("--interval", type=int, default=5, help="watch interval seconds")
    args = ap.parse_args()
    if args.action == "check":
        if not args.team_id:
            print("ERROR: check requires team_id", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(check_team_health(args.team_id), ensure_ascii=False, indent=2))
    elif args.action == "summary":
        print(json.dumps(summary(), ensure_ascii=False, indent=2))
    elif args.action == "watch":
        if not args.team_id:
            print("ERROR: watch requires team_id", file=sys.stderr)
            sys.exit(1)
        try:
            while True:
                print(json.dumps(check_team_health(args.team_id), ensure_ascii=False))
                time.sleep(args.interval)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
