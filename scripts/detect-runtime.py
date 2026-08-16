#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""detect-runtime.py — 当前客户端/运行时自动检测（TC-20260816-7 · 首次运行适配）

team-orchestration 安装到任意桌面 agent / harness / AI 客户端后，首次触发时运行本脚本
自动判定当前运行环境，配合 references/runtime-adaptation.json 加载对应适配文档。

检测信号（加权）：
- 环境变量锚（权重 2）：DSH_*（DeepSeek Harness 注入）、ZCODE_*、CLAUDE_CODE 等
- 用户目录特征（权重 1）：~/.dsh、~/.zcode、~/.claude、~/.codex、~/.workbuddy、~/.agents
- 输出：{runtime, confidence, evidence[]}；未知时 runtime=unknown，由 main 向用户确认。

用法：
    python scripts/detect-runtime.py            # 人类可读
    python scripts/detect-runtime.py --json     # 机器可读
"""
import argparse
import json
import os
import sys
from pathlib import Path

RUNTIMES = {
    "dsh": {
        "env": ("DSH_",),
        "dirs": (".dsh",),
        "label": "DeepSeek Harness",
        "adaptation_doc": "references/dsh-adaptation.md",
    },
    "zcode": {
        "env": ("ZCODE", "ZCODE_HOME"),
        "dirs": (".zcode",),
        "label": "ZCode",
        "adaptation_doc": "references/zcode-adaptation.md",
    },
    "opencode": {
        "env": ("OPENCODE",),
        "dirs": (".opencode",),
        "label": "OpenCode",
        "adaptation_doc": "references/opencode-adaptation.md",
    },
    "claude-code": {
        "env": ("CLAUDE_CODE", "CLAUDE_CONFIG_DIR"),
        "dirs": (".claude",),
        "label": "Claude Code",
        "adaptation_doc": "references/claude-code-adaptation.md",
    },
    "codex": {
        "env": ("CODEX",),
        "dirs": (".codex",),
        "label": "OpenAI Codex",
        "adaptation_doc": "references/codex-adaptation.md",
    },
    "workbuddy": {
        "env": ("WORKBUDDY",),
        "dirs": (".workbuddy",),
        "label": "WorkBuddy",
        "adaptation_doc": "references/workbuddy-adaptation.md",
    },
}


def detect() -> dict:
    home = Path.home()
    env = os.environ
    evidence = []
    scores = {name: 0 for name in RUNTIMES}
    for name, cfg in RUNTIMES.items():
        for prefix in cfg["env"]:
            if any(k.startswith(prefix) for k in env):
                scores[name] += 2
                evidence.append("env:%s*" % prefix)
                break
        for d in cfg["dirs"]:
            if (home / d).exists():
                scores[name] += 1
                evidence.append("dir:~/%s" % d)
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    top_name, top_score = ranked[0]
    # 二义性：得分相同且 >0 时按证据优先（DSH 环境变量锚最可靠）
    if top_score <= 0:
        runtime = "unknown"
        confidence = 0.2
    else:
        ties = [n for n, s in ranked if s == top_score and s > 0]
        if len(ties) > 1:
            # 环境变量锚优先；仍平则取证据多者；再平取字典序（dsh 在前）
            env_ties = [n for n in ties if any(
                any(k.startswith(p) for k in env) for p in RUNTIMES[n]["env"])]
            if len(env_ties) == 1:
                runtime = env_ties[0]
                confidence = 0.95
            else:
                runtime = sorted(ties)[0]
                confidence = 0.7
        else:
            runtime = top_name
            confidence = 0.9 if scores[top_name] >= 3 else 0.75
    cfg = RUNTIMES.get(runtime, {})
    return {
        "runtime": runtime,
        "label": cfg.get("label", "未知客户端"),
        "adaptation_doc": cfg.get("adaptation_doc", ""),
        "confidence": confidence,
        "evidence": sorted(set(evidence)),
        "scores": scores,
    }


def main():
    ap = argparse.ArgumentParser(description="当前客户端/运行时自动检测")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()
    result = detect()
    if args.json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        print("运行时: %s（%s）" % (result["runtime"], result["label"]))
        print("置信度: %.2f" % result["confidence"])
        print("适配文档: %s" % (result["adaptation_doc"] or "（无——需用户确认客户端类型）"))
        print("证据: %s" % ", ".join(result["evidence"]) or "（无）")
        print("得分: %s" % {k: v for k, v in result["scores"].items() if v > 0})


if __name__ == "__main__":
    main()
