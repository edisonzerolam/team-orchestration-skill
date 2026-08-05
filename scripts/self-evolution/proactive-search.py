#!/usr/bin/env python3
"""Proactive internet-based knowledge enhancement for experts.

For each expert, generates search queries based on their domain,
fetches results, and produces an evolution report for user review.

Usage:
    python3 proactive-search.py --experts all
    python3 proactive-search.py --experts investment-masters-team
    python3 proactive-search.py --report-only
"""
import json, os, sys, argparse, subprocess, tempfile
from pathlib import Path
from datetime import datetime
import sys
import sys
import sys
import sys
import sys
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXPERT_DIR = Path(__file__).resolve().parent.parent.parent / "references" / "workbuddy-experts"
REPORT_DIR = EXPERT_DIR.parent / "evolution-reports"

def get_expert_domains(name: str) -> list:
    pj = EXPERT_DIR / name / "plugin.json"
    if not pj.exists():
        return []
    try:
        data = json.loads(pj.read_text(encoding="utf-8"))
    except:
        return []
    cat = data.get("categoryId", "")
    desc = data.get("displayDescription", {}).get("zh", "")
    return [cat, desc[:100]] if desc else [cat]

def build_search_queries(domains: list) -> list:
    queries = []
    for d in domains:
        if not d:
            continue
        for prefix in ["最新趋势", "2026年", "新技术"]:
            queries.append(f"{d} {prefix}")
    return queries[:5]

def search_web(query: str) -> str:
    # 环境未提供 web 搜索工具（web_search_stub.py 缺失，且无 python3 命令）
    import logging
    logging.getLogger(__name__).warning("联网搜索不可用，跳过: %s", query)
    return "（联网搜索不可用：环境未提供 web 搜索工具）"

def generate_report(name: str, queries: list, results: list) -> str:
    report = f"""# 进化报告: {name}

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## 搜索发现

"""
    for q, r in zip(queries, results):
        report += f"### {q}\n{r}\n\n"
    report += "---\n**审核**: 请审核上述发现, 确认是否合并到 knowledge 文件。\n"
    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experts", nargs="+", default=["all"])
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if args.experts == ["all"]:
        experts = [d.name for d in EXPERT_DIR.iterdir() if d.is_dir()]
    else:
        experts = [e for e in args.experts if (EXPERT_DIR / e).exists()]
    for name in experts:
        domains = get_expert_domains(name)
        queries = build_search_queries(domains)
        results = []
        if not args.report_only:
            for q in queries:
                print(f"  搜索: {q}")
                results.append(search_web(q))
        else:
            results = ["（报告模式：跳过在线搜索）"] * len(queries)
        report = generate_report(name, queries, results)
        report_file = REPORT_DIR / f"{name}-evolution-{datetime.now().strftime('%Y%m%d')}.md"
        report_file.write_text(report, encoding="utf-8")
        print(f"  报告已生成: {report_file}")
    print("done")

if __name__ == "__main__":
    main()
