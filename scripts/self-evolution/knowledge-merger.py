#!/usr/bin/env python3
"""Merge approved evolution findings into expert knowledge files.

Usage:
    python3 knowledge-merger.py --expert investment-masters-team --source report.md
    python3 knowledge-merger.py --list-pending
"""
import json, os, sys, argparse, re
from pathlib import Path
from datetime import datetime

EXPERT_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "references" / "workbuddy-experts"
REPORT_DIR = EXPERT_DIR.parent / "evolution-reports"
KNOWLEDGE_DIR = EXPERT_DIR.parent.parent / "knowledge"

def list_pending():
    reports = list(REPORT_DIR.glob("*-evolution-*.md"))
    for r in reports:
        name = r.stem.rsplit("-evolution-", 1)[0]
        print(f"  {name} -> {r}")
    return len(reports)

def merge(expert_name: str, source_path: str):
    source = Path(source_path)
    if not source.exists():
        print(f"错误: 源文件不存在: {source}")
        return False
    content = source.read_text(encoding="utf-8")
    target_dir = KNOWLEDGE_DIR / expert_name
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"evolution-{datetime.now().strftime('%Y%m%d')}.md"
    target_file.write_text(content, encoding="utf-8")
    archived = REPORT_DIR / f"{source.stem}.archived"
    source.rename(archived)
    print(f"合并完成: {target_file}")
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expert", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--list-pending", action="store_true")
    args = ap.parse_args()
    if args.list_pending:
        list_pending()
        return
    if not args.expert or not args.source:
        print("请指定 --expert 和 --source")
        return
    merge(args.expert, args.source)

if __name__ == "__main__":
    main()
