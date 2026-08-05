#!/usr/bin/env python3
"""self_heal.py - Agent error classification & recovery (P0.10, v2.6 rewrite).

Clean reimplementation: the previous file suffered encoding/structural
corruption. Provides error classification, retry/downgrade guidance, and a
SelfHeal handler that logs and caps retries per error type.
"""
import json
import re
from pathlib import Path

__version__ = "2.6.0"

ERROR_TYPES = {
    "powershell_regex": {
        "severity": "medium", "recoverable": True,
        "fix_actions": ["escape_dollar_sign", "log_and_skip"], "max_retries": 2,
        "description": "PowerShell regex error",
    },
    "timeout": {
        "severity": "high", "recoverable": True,
        "fix_actions": ["retry_with_backoff", "reduce_scope"], "max_retries": 3,
        "description": "Operation timed out",
    },
    "network": {
        "severity": "high", "recoverable": True,
        "fix_actions": ["retry", "fallback_cache"], "max_retries": 3,
        "description": "Network/connection error",
    },
    "parse": {
        "severity": "medium", "recoverable": True,
        "fix_actions": ["log_and_skip", "use_default"], "max_retries": 1,
        "description": "Response parse error",
    },
    "unknown": {
        "severity": "medium", "recoverable": True,
        "fix_actions": ["log_and_skip"], "max_retries": 1,
        "description": "Unknown error",
    },
}

_KW = {
    "timeout": ["timeout", "timed out", "deadline", "时间"],
    "network": ["connection", "network", "refused", "unreachable", "503", "502", "dns", "网络"],
    "powershell_regex": ["regex", "powershell", "正则"],
    "parse": ["json", "parse", "decode", "unexpected", "解析"],
}


def classify_error(error_message):
    em = (error_message or "").lower()
    for etype, kws in _KW.items():
        if any(k in em for k in kws):
            return etype
    return "unknown"


class SelfHeal:
    def __init__(self, team_id, agent_id, workspace=None):
        self.team_id = team_id
        self.agent_id = agent_id
        self.workspace = workspace or (
            Path(__file__).resolve().parent.parent.parent / "shared" / "team-brain")
        self.error_dir = self.workspace / "errors" / str(team_id) / str(agent_id)
        self.error_dir.mkdir(parents=True, exist_ok=True)
        self.retries = {}
        self.fix_stats = {"success": 0, "failed": 0, "skipped": 0}

    def handle_error(self, error_message, error_type=None, context=None):
        if error_type is None:
            error_type = classify_error(error_message)
        info = ERROR_TYPES.get(error_type, ERROR_TYPES["unknown"])
        max_retries = info["max_retries"]
        current = self.retries.get(error_type, 0)
        result = {
            "error_type": error_type,
            "error_message": (error_message or "")[:200],
            "severity": info["severity"],
            "retries": current,
            "max_retries": max_retries,
            "handled": False,
            "fix_success": False,
            "fix_action": None,
            "should_continue": True,
            "error_logged": False,
        }
        if current >= max_retries:
            result["should_continue"] = False
            try:
                (self.error_dir / "unrecoverable.jsonl").open("a", encoding="utf-8").write(
                    json.dumps(result, ensure_ascii=False) + "\n")
                result["error_logged"] = True
            except Exception:
                pass
            return result
        action = info["fix_actions"][0]
        result["fix_action"] = action
        result["fix_success"] = True
        result["handled"] = True
        self.retries[error_type] = current + 1
        try:
            (self.error_dir / "handled.jsonl").open("a", encoding="utf-8").write(
                json.dumps(result, ensure_ascii=False) + "\n")
            result["error_logged"] = True
        except Exception:
            pass
        return result


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Agent self-heal")
    ap.add_argument("--error-message", required=True, help="error text to classify")
    args = ap.parse_args()
    etype = classify_error(args.error_message)
    info = ERROR_TYPES.get(etype, ERROR_TYPES["unknown"])
    out = {
        "error_type": etype,
        "severity": info["severity"],
        "recoverable": info["recoverable"],
        "fix_actions": info["fix_actions"],
        "max_retries": info["max_retries"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
