#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto-decider.py - Automatic error-decision engine (P0.11, v2.6 rewrite).

Replaces a structurally-corrupted prior file. Maps error types to recovery
actions (retry / skip / abort) and caps retries.
"""
import json
import sys

DECISION_RULES = {
    "powershell_regex": {
        "patterns": ["无法识别", "正则表达", "语法错误", "$变量", "非法字符", "regex"],
        "action": "retry",
        "reason": "PowerShell regex error, retry after escaping",
        "new_timeout": 60,
    },
    "subprocess_timeout": {
        "patterns": ["超时", "timeout", "timed out", "deadline"],
        "action": "retry",
        "reason": "subprocess timeout, increase timeout and retry",
        "new_timeout": 120,
    },
    "file_not_found": {
        "patterns": ["找不到", "not found", "不存在", "路径错误", "no such file"],
        "action": "skip",
        "reason": "file not found, skip this task",
    },
    "syntax_error": {
        "patterns": ["语法错误", "syntax error", "IndentationError", "SyntaxError"],
        "action": "abort",
        "reason": "code syntax error, needs manual fix",
    },
    "permission_denied": {
        "patterns": ["权限", "permission", "拒绝访问", "denied"],
        "action": "abort",
        "reason": "insufficient permission, needs human intervention",
    },
    "unknown": {
        "patterns": [],
        "action": "skip",
        "reason": "unknown error, default skip",
    },
}


def classify_error(error_message):
    msg_lower = (error_message or "").lower()
    for err_type, rule in DECISION_RULES.items():
        for pattern in rule["patterns"]:
            if pattern.lower() in msg_lower:
                return err_type
    return "unknown"


def decide(error_type, error_message, retry_count=0):
    if retry_count >= 3:
        return {"action": "abort", "reason": "retries exceeded 3, stop", "error_type": error_type}
    if error_type == "auto":
        inferred = classify_error(error_message)
        return {
            "action": DECISION_RULES[inferred]["action"],
            "reason": DECISION_RULES[inferred]["reason"],
            "new_timeout": DECISION_RULES[inferred].get("new_timeout"),
            "error_type": inferred,
        }
    rule = DECISION_RULES.get(error_type, DECISION_RULES["unknown"])
    return {
        "action": rule["action"],
        "reason": rule["reason"],
        "new_timeout": rule.get("new_timeout"),
        "error_type": error_type,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Auto decider")
    ap.add_argument("--error-message", required=True)
    ap.add_argument("--error-type", default="auto")
    ap.add_argument("--retry-count", type=int, default=0)
    args = ap.parse_args()
    result = decide(args.error_type, args.error_message, args.retry_count)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
