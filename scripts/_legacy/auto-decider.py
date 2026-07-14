#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto Decider — 自动化错误决策引擎

根据错误类型和重试次数自动决定：retry / skip / abort。

用法:
  python3 auto-decider.py --error "timeout: 连接超时" --retry-count 1
  python3 auto-decider.py --error "SyntaxError: invalid syntax" --json
  python3 auto-decider.py --classify "无法识别命令 $_variable"
"""
import json
import sys
import argparse
import re

# 决策规则表
DECISION_RULES = {
    "timeout": {
        "patterns": [r"超时", r"timeout", r"timed\s*out", r"time\s*out"],
        "action": "retry",
        "reason": "执行超时，增加超时时间后重试",
        "new_timeout": 120,
    },
    "powershell_regex": {
        "patterns": [r"无法识别", r"正则表达式", r"\$\w+", r"非法字符"],
        "action": "retry",
        "reason": "PowerShell 正则/GDK 编码错误，转义后重试",
        "new_timeout": 60,
    },
    "rate_limited": {
        "patterns": [r"429", r"529", r"rate\s*limit", r"too\s*many\s*requests",
                     r"过载", r"high\s*load", r"请稍后重试"],
        "action": "retry",
        "reason": "API 限流/过载，等待后重试",
        "new_timeout": 60,
    },
    "model_not_found": {
        "patterns": [r"model\s*not\s*found", r"unknown\s*model", r"模型不存在",
                     r"not a valid agent", r"not a valid agent type",
                     r"unknown agent"],
        "action": "abort",
        "reason": "模型或 Agent 类型不存在，需检查配置",
    },
    "file_not_found": {
        "patterns": [r"(?<!model\s)not\s*found", r"找不到", r"不存在", r"路径错误",
                     r"No such file", r"FileNotFoundError", r"Cannot find",
                     r"cannot find", r"does not exist"],
        "action": "skip",
        "reason": "文件不存在，跳过该任务",
    },
    "syntax_error": {
        "patterns": [r"SyntaxError", r"语法错误", r"invalid\s*syntax",
                     r"IndentationError", r"ParseError"],
        "action": "abort",
        "reason": "代码语法错误，需人工修复",
    },
    "permission_denied": {
        "patterns": [r"权限", r"permission\s*denied", r"拒绝访问",
                     r"AccessDenied", r"EACCES", r"Unauthorized"],
        "action": "abort",
        "reason": "权限不足或认证失败，需人工介入",
    },
    "insufficient_balance": {
        "patterns": [r"insufficient\s*balance", r"billing", r"余额不足",
                     r"quota\s*exhausted", r"credit"],
        "action": "abort",
        "reason": "API 余额不足或配额耗尽，需充值",
    },
    "unknown": {
        "patterns": [],
        "action": "skip",
        "reason": "未知错误，默认跳过",
    },
}

MAX_RETRIES = 3


def classify_error(error_message: str) -> str:
    """根据错误信息匹配错误类型（不区分大小写）"""
    if not error_message:
        return "unknown"

    msg = error_message.strip()
    for err_type, rule in DECISION_RULES.items():
        for pattern in rule["patterns"]:
            if re.search(pattern, msg, re.IGNORECASE):
                return err_type
    return "unknown"


def decide(error_type: str, error_message: str = "", retry_count: int = 0) -> dict:
    """根据错误类型和重试次数做出决策"""
    if retry_count >= MAX_RETRIES:
        return {
            "action": "abort",
            "reason": f"重试次数超过 {MAX_RETRIES} 次上限，终止",
            "error_type": error_type,
            "retry_count": retry_count,
        }

    if error_type == "auto":
        inferred = classify_error(error_message)
        rule = DECISION_RULES.get(inferred, DECISION_RULES["unknown"])
        return {
            "action": rule["action"],
            "reason": rule["reason"],
            "new_timeout": rule.get("new_timeout"),
            "error_type": inferred,
            "retry_count": retry_count,
        }

    rule = DECISION_RULES.get(error_type, DECISION_RULES["unknown"])
    return {
        "action": rule["action"],
        "reason": rule["reason"],
        "new_timeout": rule.get("new_timeout"),
        "error_type": error_type,
        "retry_count": retry_count,
    }


def main():
    ap = argparse.ArgumentParser(description="Auto Decider — 自动化错误决策引擎")
    ap.add_argument("--error", default="", help="错误信息")
    ap.add_argument("--error-type", default="auto", help="错误类型 (auto=自动推断)")
    ap.add_argument("--retry-count", type=int, default=0, help="已重试次数")
    ap.add_argument("--classify", default="", help="仅分类错误类型，不做决策")
    ap.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = ap.parse_args()

    if args.classify:
        err_type = classify_error(args.classify)
        if args.json:
            print(json.dumps({"error_type": err_type, "error_message": args.classify},
                             ensure_ascii=False))
        else:
            print(f"错误类型: {err_type}")
        return

    decision = decide(args.error_type, args.error, args.retry_count)

    if args.json:
        print(json.dumps(decision, ensure_ascii=False, indent=2))
    else:
        print(f"错误: {args.error[:80] if args.error else 'N/A'}...")
        print(f"类型: {decision['error_type']}")
        print(f"决策: {decision['action']}")
        print(f"原因: {decision['reason']}")
        if decision.get("new_timeout"):
            print(f"新超时: {decision['new_timeout']}s")


if __name__ == "__main__":
    main()
