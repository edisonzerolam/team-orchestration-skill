#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""expert-fingerprint.py — 人设描述相似度指纹（TC-20260816-9 · P3）

跨团人设 description 相似度全对扫描（字符 3-gram TF-IDF + cosine，去模板停用词），
产出高相似候选表供人工裁决（P2 共享人设池的裁决依据；禁止自动合并）。
v2（审计修正）：n-gram jaccard → TF-IDF cosine + 模板停用词归一化（防"专家/输出/报告"
等模板词虚高相似度；旧法实测最高 0.504、0.6 阈值永不触发）。

用法：
  python scripts/expert-fingerprint.py [--threshold 0.5] [--json] [--top 20] [--stats]
输出：
  references/fingerprint-report.json（全量 pairs 按 score 降序 + 分布统计）
  stdout 人类可读摘要
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_DIR = Path(__file__).resolve().parent.parent
EXPERTS = SKILL_DIR / "references" / "workbuddy-experts"
REPORT_PATH = SKILL_DIR / "references" / "fingerprint-report.json"

# 模板停用词：人设/团队描述高频模板词，不计入相似度（审计 #5 修正）
STOPWORDS = {
    "专家", "团队", "负责", "输出", "报告", "分析", "工作", "流程", "规范", "能力",
    "核心", "专业", "经验", "擅长", "提供", "方案", "结果", "总结", "评估", "研究",
    "the", "and", "for", "with", "from", "that", "this", "expert", "team", "skill",
    "work", "output", "report", "analysis", "provide", "based",
}


def read_desc(md: Path) -> str:
    """块标量安全读取 frontmatter description（|/>/>- 多行展开，防解析假象）。"""
    t = md.read_text(encoding="utf-8", errors="replace")
    lines = t.splitlines()
    for i, ln in enumerate(lines[:60]):
        if ln.startswith("description:"):
            val = ln.split(":", 1)[1].strip()
            if val in ("|", ">", ">-", "|-"):
                block = []
                for nxt in lines[i + 1:]:
                    if nxt.strip() == "":
                        block.append("")
                        continue
                    if nxt.startswith(" ") or nxt.startswith("\t"):
                        block.append(nxt.strip())
                    else:
                        break
                return " ".join(x for x in block if x)[:400]
            return val[:400]
    return t[:120]


def features(s: str, n: int = 3) -> dict:
    """字符 3-gram 特征（去停用词 token 后再切 n-gram）。"""
    toks = [w for w in re.split(r"[^a-z0-9\u4e00-\u9fff]+", s.lower()) if w and w not in STOPWORDS]
    joined = "".join(toks)
    return {joined[i:i + n]: joined.count(joined[i:i + n]) for i in range(len(joined) - n + 1)} \
        if len(joined) >= n else {}


def cosine(a: dict, b: dict, idf: dict = None) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    dot = 0.0
    na = nb = 0.0
    for k in keys:
        w = idf.get(k, 1.0) if idf else 1.0
        va, vb = a.get(k, 0.0) * w, b.get(k, 0.0) * w
        dot += va * vb
        na += va * va
        nb += vb * vb
    if na == 0 or nb == 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def main():
    ap = argparse.ArgumentParser(description="人设描述相似度指纹（TF-IDF cosine）")
    ap.add_argument("--threshold", type=float, default=0.5, help="相似度阈值（缺省 0.5）")
    ap.add_argument("--top", type=int, default=20, help="摘要显示条数")
    ap.add_argument("--json", action="store_true", help="JSON 输出到 REPORT_PATH")
    ap.add_argument("--stats", action="store_true", help="输出相似度分布（阈值校准用）")
    args = ap.parse_args()

    agents = []
    for md in sorted(EXPERTS.rglob("agents/*.md")):
        agents.append({"team": md.parent.parent.name, "id": md.stem,
                       "desc": read_desc(md), "path": str(md)})

    # 全局 IDF（字符 n-gram 的文档频率）
    all_feats = [features(a["desc"]) for a in agents]
    df = {}
    for f in all_feats:
        for k in f:
            df[k] = df.get(k, 0) + 1
    n_docs = max(len(agents), 1)
    idf = {k: math.log((n_docs + 1) / (v + 1)) + 1 for k, v in df.items()}

    pairs = []
    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            if agents[i]["team"] == agents[j]["team"]:
                continue
            s = cosine(all_feats[i], all_feats[j], idf)
            if s >= args.threshold:
                pairs.append({"a_team": agents[i]["team"], "a_id": agents[i]["id"],
                              "b_team": agents[j]["team"], "b_id": agents[j]["id"],
                              "score": round(s, 3)})
    pairs.sort(key=lambda x: -x["score"])

    if args.stats:
        # 相似度分布（0.1 桶）供阈值校准
        buckets = {}
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                if agents[i]["team"] == agents[j]["team"]:
                    continue
                s = cosine(all_feats[i], all_feats[j], idf)
                b = math.floor(s * 10) / 10
                buckets[b] = buckets.get(b, 0) + 1
        print("相似度分布（跨团对）：")
        for b in sorted(buckets, reverse=True):
            print("  %.1f-%.1f: %d" % (b, b + 0.1, buckets[b]))

    if args.json:
        report = {
            "generated_at": "2026-08-16",
            "method": "char3gram-tfidf-cosine",
            "threshold": args.threshold,
            "agents_scanned": len(agents),
            "pair_count": len(pairs),
            "pairs": pairs,
        }
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("✅ 指纹报告已写入: %s (%d 对)" % (REPORT_PATH, len(pairs)))

    print("扫描 %d 人设，阈值 %.2f，命中 %d 对" % (len(agents), args.threshold, len(pairs)))
    for p in pairs[:args.top]:
        print("  %.2f  %s/%s  vs  %s/%s" % (p["score"], p["a_team"], p["a_id"],
                                              p["b_team"], p["b_id"]))


if __name__ == "__main__":
    main()

