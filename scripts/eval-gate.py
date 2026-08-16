#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eval-gate.py — 专家合并回归门禁（TC-20260816-9 · P7）

跑 eval-suite.json 全部样例 → expert-matcher top-3 → 命中率（预期团队出现在 top-3 的比例）。
用法：
  python scripts/eval-gate.py --baseline        # 记录基线到 tests/eval-baseline.json
  python scripts/eval-gate.py --after           # 与基线对比，下降 > threshold_drop_pct 即退出码 1
  python scripts/eval-gate.py                   # 只跑现状
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"
SUITE = SKILL_DIR / "tests" / "eval-suite.json"
BASELINE = SKILL_DIR / "tests" / "eval-baseline.json"
TOP_K = 3


def run_matcher(task: str, domain: str = "") -> tuple:
    cmd = [sys.executable, str(SCRIPTS / "expert-matcher.py"),
           "--task", task, "--top-k", str(TOP_K), "--json"]
    if domain:
        # 域限域模式（TC-20260816-9 · P7 修正）：域内召回，避开通用团霸榜
        cmd += ["--domain", domain]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=60)
    try:
        data = json.loads(r.stdout)
        return [x.get("name", "") for x in data[:TOP_K]], [x.get("score", 0) for x in data[:TOP_K]]
    except Exception:
        return [], []


NEGATIVE_MIN_SCORE = 0.35  # 负例判定：全局 top-3 最高分低于此 = 正确拒绝


def evaluate() -> dict:
    suite = json.loads(SUITE.read_text(encoding="utf-8"))
    results = []
    hit = 0
    neg_ok = 0
    neg_total = 0
    for c in suite["cases"]:
        domain = c.get("domain", "")
        top3, scores = run_matcher(c["task"], domain)
        expected = set(c.get("expected_teams", []))
        if not expected:
            # 负例：全局 top-3 最高分 < 阈值 = 正确拒绝（低置信）
            neg_total += 1
            ok = (max(scores) if scores else 0) < NEGATIVE_MIN_SCORE
            neg_ok += ok
        else:
            ok = bool(expected & set(top3))
            hit += ok
        results.append({"task": c["task"], "domain": domain, "top3": top3,
                        "scores": scores, "expected": sorted(expected), "hit": ok})
    total = len(results) - neg_total
    return {"hit": hit, "total": total, "hit_rate": round(hit * 100.0 / total, 1) if total else 0.0,
            "negative_ok": neg_ok, "negative_total": neg_total,
            "cases": results}


def main():
    ap = argparse.ArgumentParser(description="专家合并回归门禁")
    ap.add_argument("--baseline", action="store_true", help="记录基线")
    ap.add_argument("--after", action="store_true", help="对比基线并裁决")
    args = ap.parse_args()

    cur = evaluate()
    neg_note = "（负例 %d/%d 正确拒绝）" % (cur["negative_ok"], cur["negative_total"])
    if args.baseline:
        BASELINE.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
        print("✅ 基线已记录: %d/%d (%.1f%%) %s -> %s" % (
            cur["hit"], cur["total"], cur["hit_rate"], neg_note, BASELINE))
        sys.exit(0)
    if not BASELINE.exists():
        print("❌ 无基线（先跑 --baseline）", file=sys.stderr)
        sys.exit(2)
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    drop = base["hit_rate"] - cur["hit_rate"]
    print("基线: %d/%d (%.1f%%)" % (base["hit"], base["total"], base["hit_rate"]))
    print("现状: %d/%d (%.1f%%) %s 下降 %.1f%%" % (
        cur["hit"], cur["total"], cur["hit_rate"], neg_note, drop))
    if args.after and drop > 5.0:
        print("❌ 命中率下降 >5% —— 合并应撤销")
        sys.exit(1)
    print("✅ 门禁通过" if drop <= 5.0 else "⚠️ 现状无基线对比，仅报告")


if __name__ == "__main__":
    main()
