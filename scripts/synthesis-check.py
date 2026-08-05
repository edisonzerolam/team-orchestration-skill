"""synthesis-check.py - Expert consensus confirmation before final delivery.

Usage:
    python synthesis-check.py <team_id> <final_report_path> [--timeout=300]

Workflow:
    1. Read team status file to get all expert agents
    2. Collect consensus responses from each expert: agree / concern / object
    3. Timeout unresponding experts after --timeout seconds
    4. Generate consensus report at synthesis/{team_id}-consensus-check.md
    5. Print result JSON: delivered / delivered_with_concerns / returned
"""
import json
import sys
import time
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
TEAM_BRAIN_ROOT = SKILL_DIR.parent / "shared" / "team-brain"
DEFAULT_TIMEOUT = 300  # 5 minutes

AGREE = "agree"
CONCERN = "concern"
OBJECT = "object"


def load_team(team_id: str) -> dict:
    team_file = TEAM_BRAIN_ROOT / "teams" / f"{team_id}.json"
    if not team_file.exists():
        return {}
    with open(team_file, encoding="utf-8") as f:
        return json.load(f)


def load_final_report(final_report_path: str) -> str:
    p = Path(final_report_path)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def parse_response(text: str) -> tuple:
    """Parse expert response. Returns (vote, detail)."""
    text = text.strip()
    low = text.lower()
    if text.startswith("agree") or "agree" in low or "approve" in low:
        return AGREE, text
    elif text.startswith("object") or "object" in low or "reject" in low:
        lines = text.split("\n", 1)
        reason = lines[1].strip() if len(lines) > 1 else "No reason provided"
        return OBJECT, reason
    elif text.startswith("concern") or "concern" in low or "with concerns" in low:
        lines = text.split("\n", 1)
        concern = lines[1].strip() if len(lines) > 1 else "Concern stated"
        return CONCERN, concern
    else:
        return AGREE, "No details"


def collect_expert_consensus(team_id: str, final_report_path: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Collect consensus from all experts in the team."""
    team = load_team(team_id)
    if not team:
        return {"error": f"Team {team_id} not found", "team_id": team_id}
    agents = team.get("agents", [])
    if not agents:
        return {"error": "No agents in team", "team_id": team_id}
    final_report = load_final_report(final_report_path)
    if not final_report:
        return {"error": f"Final report not found: {final_report_path}", "team_id": team_id}

    consensus_dir = TEAM_BRAIN_ROOT / "synthesis" / team_id
    consensus_dir.mkdir(parents=True, exist_ok=True)

    request_file = consensus_dir / f"{team_id}-consensus-request.md"
    agent_lines = "\n".join(f"- {a['id']} ({a.get('role', 'unknown')})" for a in agents)
    request_content = f"""# Consensus Check Request - Team {team_id}

## Final Report
Path: {final_report_path}

## Please Confirm
Read the final report and respond with one of:
- **Agree** - Report is ready for delivery
- **Concern** - Agree with concerns (state your concern below)
- **Object** - Object to delivery (state your objection below)

## Your Response
Save your response to: {consensus_dir}/{{your_agent_id}}-response.md
Format:
[Agree/Concern/Object] - {{your_reason_here}}

## Experts to Respond
{agent_lines}
"""
    request_file.write_text(request_content, encoding="utf-8")

    votes = {}
    start_time = time.time()
    for agent in agents:
        agent_id = agent["id"]
        response_file = consensus_dir / f"{agent_id}-response.md"
        if response_file.exists():
            text = response_file.read_text(encoding="utf-8")
            vote, detail = parse_response(text)
            votes[agent_id] = {"vote": vote, "detail": detail, "responded": True, "elapsed": "pre-existing"}
        else:
            votes[agent_id] = {"vote": None, "detail": None, "responded": False}

    while time.time() - start_time < timeout:
        all_responded = all(v.get("responded") for v in votes.values())
        if all_responded:
            break
        time.sleep(5)
        for agent in agents:
            agent_id = agent["id"]
            if not votes[agent_id]["responded"]:
                response_file = consensus_dir / f"{agent_id}-response.md"
                if response_file.exists():
                    text = response_file.read_text(encoding="utf-8")
                    vote, detail = parse_response(text)
                    votes[agent_id] = {
                        "vote": vote,
                        "detail": detail,
                        "responded": True,
                        "elapsed": f"{int(time.time() - start_time)}s"
                    }

    for agent_id, vote_data in votes.items():
        if not vote_data["responded"]:
            vote_data["vote"] = AGREE
            vote_data["detail"] = "Timeout - treated as no objection"
            vote_data["responded"] = False
            vote_data["elapsed"] = f"timeout_after_{timeout}s"

    has_objection = any(v["vote"] == OBJECT for v in votes.values())
    has_concern = any(v["vote"] == CONCERN for v in votes.values())
    if has_objection:
        status = "returned"
    elif has_concern:
        status = "delivered_with_concerns"
    else:
        status = "delivered"

    report_path = consensus_dir / f"{team_id}-consensus-check.md"
    report_lines = [
        f"# Consensus Check Report - Team {team_id}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Final Report:** `{final_report_path}`",
        f"**Status:** `{status}`",
        "",
        "## Vote Summary",
        ""
    ]
    for agent in agents:
        agent_id = agent["id"]
        v = votes.get(agent_id, {})
        vote = v.get("vote", OBJECT)
        detail = v.get("detail", "No response")
        responded = v.get("responded", False)
        elapsed = v.get("elapsed", "unknown")
        marker = "OK" if responded else "TIMEOUT"
        report_lines.append(f"{marker} **{agent_id}** ({agent.get('role', '')}): {vote}")
        report_lines.append(f"    Detail: {detail}")
        report_lines.append(f"    Responded: {responded} ({elapsed})")
        report_lines.append("")

    if has_objection:
        report_lines.append("## Objections (Blocking)")
        for agent_id, v in votes.items():
            if v["vote"] == OBJECT:
                report_lines.append(f"- **{agent_id}**: {v['detail']}")
        report_lines.append("")
        report_lines.append("**Action:** Returned to Builder for revision.")
    if has_concern:
        report_lines.append("## Concerns (Non-blocking)")
        for agent_id, v in votes.items():
            if v["vote"] == CONCERN:
                report_lines.append(f"- **{agent_id}**: {v['detail']}")
        report_lines.append("")
        report_lines.append("**Action:** Delivered with attached concerns.")
    if status == "delivered":
        report_lines.append("**Action:** All experts agree. Report delivered.")

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    result = {
        "team_id": team_id,
        "final_report_path": final_report_path,
        "consensus_report_path": str(report_path),
        "status": status,
        "votes": {aid: v["vote"] for aid, v in votes.items()},
        "details": {aid: v["detail"] for aid, v in votes.items()},
        "responded_count": sum(1 for v in votes.values() if v["responded"]),
        "total_experts": len(agents),
        "elapsed_seconds": int(time.time() - start_time)
    }

    team_file = TEAM_BRAIN_ROOT / "teams" / f"{team_id}.json"
    if team_file.exists():
        with open(team_file, encoding="utf-8") as f:
            team_data = json.load(f)
        team_data["phase"] = "consensus_check"
        team_data["consensus_status"] = status
        team_file.write_text(json.dumps(team_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python synthesis-check.py <team_id> <final_report_path> [--timeout=300]")
        sys.exit(1)
    team_id = None
    final_report_path = None
    timeout = DEFAULT_TIMEOUT
    args = sys.argv[1:]
    for arg in args:
        if arg.startswith("--timeout="):
            timeout = int(arg.split("=", 1)[1])
        elif not arg.startswith("--") and not arg.startswith("-"):
            if team_id is None:
                team_id = arg
            elif final_report_path is None:
                final_report_path = arg
    if not team_id or not final_report_path:
        print("Usage: python synthesis-check.py <team_id> <final_report_path> [--timeout=300]")
        sys.exit(1)
    result = collect_expert_consensus(team_id, final_report_path, timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
