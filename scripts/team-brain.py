"""ClawTeam Team Brain - Multi-agent orchestration script.

Usage:
    python team-brain.py plan <task> <description>
    python team-brain.py launch <topic> <description> [max_agents] [--full-discussion]
    python team-brain.py status [team_id]
    python team-brain.py synthesis <team_id>
    python team-brain.py synthesis-check <team_id> <final_report_path> [--timeout=300]
"""
import json
import sys
import time
import importlib.util
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TEAM_BRAIN_ROOT = SKILL_DIR.parent / "shared" / "team-brain"
DEFAULT_MAX_AGENTS = 5
DEFAULT_TIMEOUT_PER_AGENT = 600
__version__ = "3.4.1"

# Import self-heal after SCRIPT_DIR is defined
spec = importlib.util.spec_from_file_location("self_heal", str(SCRIPT_DIR / "self_heal.py"))
self_heal_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(self_heal_module)
SelfHeal = self_heal_module.SelfHeal


def ensure_dirs():
    root = TEAM_BRAIN_ROOT
    for sub in ["teams", "plans", "findings", "debates", "synthesis", "errors"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def load_team(team_id: str) -> dict:
    team_file = TEAM_BRAIN_ROOT / "teams" / f"{team_id}.json"
    if not team_file.exists():
        return {}
    with open(team_file, encoding="utf-8") as f:
        return json.load(f)


def save_team(team_id: str, data: dict):
    team_file = TEAM_BRAIN_ROOT / "teams" / f"{team_id}.json"
    with open(team_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cmd_plan(task: str, description: str):
    ensure_dirs()
    plan_id = f"plan-{int(time.time())}"
    plan = {
        "plan_id": plan_id,
        "task": task,
        "description": description,
        "created_at": time.time(),
        "status": "planned"
    }
    plan_file = TEAM_BRAIN_ROOT / "plans" / f"{plan_id}.json"
    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return plan


def cmd_launch(topic: str, description: str, max_agents: int = DEFAULT_MAX_AGENTS, full_discussion: bool = False):
    ensure_dirs()
    team_id = f"team-{int(time.time())}"
    team = {
        "team_id": team_id,
        "topic": topic,
        "description": description,
        "max_agents": max_agents,
        "full_discussion": full_discussion,
        "agents": [],
        "phase": "launched",
        "created_at": time.time()
    }
    save_team(team_id, team)
    print(json.dumps(team, ensure_ascii=False, indent=2))
    return team


def cmd_status(team_id: str = None):
    ensure_dirs()
    if team_id:
        team = load_team(team_id)
        if not team:
            print(json.dumps({"error": f"Team {team_id} not found"}, ensure_ascii=False))
            return
        print(json.dumps(team, ensure_ascii=False, indent=2))
    else:
        teams_dir = TEAM_BRAIN_ROOT / "teams"
        teams = [f.stem for f in teams_dir.glob("*.json")] if teams_dir.exists() else []
        print(json.dumps({"teams": teams}, ensure_ascii=False, indent=2))


def cmd_synthesis(team_id: str):
    ensure_dirs()
    team = load_team(team_id)
    if not team:
        print(json.dumps({"error": f"Team {team_id} not found"}, ensure_ascii=False))
        return
    try:
        spec = importlib.util.spec_from_file_location("auto_decider", str(SCRIPT_DIR / "auto_decider.py"))
        auto_decider = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auto_decider)
        result = auto_decider.run(team_id=team_id) if hasattr(auto_decider, "run") else {"status": "synthesis_triggered"}
    except Exception as e:
        result = {"status": "synthesis_triggered", "note": str(e)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_synthesis_check(team_id: str, final_report_path: str, timeout: int = 300):
    ensure_dirs()
    spec = importlib.util.spec_from_file_location("synthesis_check", str(SCRIPT_DIR / "synthesis-check.py"))
    synthesis_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(synthesis_check)
    result = synthesis_check.collect_expert_consensus(team_id, final_report_path, timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == "plan":
        if len(args) < 2:
            print("Usage: python team-brain.py plan <task> <description>")
            sys.exit(1)
        cmd_plan(args[0], " ".join(args[1:]))
    elif cmd == "launch":
        if len(args) < 2:
            print("Usage: python team-brain.py launch <topic> <description> [max_agents] [--full-discussion]")
            sys.exit(1)
        max_agents = DEFAULT_MAX_AGENTS
        full_discussion = False
        topic = args[0]
        desc_parts = []
        for a in args[1:]:
            if a == "--full-discussion":
                full_discussion = True
            elif a.isdigit():
                max_agents = int(a)
            else:
                desc_parts.append(a)
        cmd_launch(topic, " ".join(desc_parts), max_agents, full_discussion)
    elif cmd == "status":
        team_id = args[0] if args else None
        cmd_status(team_id)
    elif cmd == "synthesis":
        if not args:
            print("Usage: python team-brain.py synthesis <team_id>")
            sys.exit(1)
        cmd_synthesis(args[0])
    elif cmd == "synthesis-check":
        if len(args) < 2:
            print("Usage: python team-brain.py synthesis-check <team_id> <final_report_path> [--timeout=300]")
            sys.exit(1)
        team_id = args[0]
        final_report_path = args[1]
        timeout = 300
        for a in args[2:]:
            if a.startswith("--timeout="):
                timeout = int(a.split("=", 1)[1])
        cmd_synthesis_check(team_id, final_report_path, timeout)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
