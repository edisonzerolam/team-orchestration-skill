#!/usr/bin/env python3
"""模型并发参考数据检查器（v3.9 · TC-20260816-6 补强）。

每任务立案时调用（SKILL.md §3 A 步骤 3）：检测参考数据是否过期（>freshness_days 天）。
- fresh：直接用官方并发（不构成约束时取编排层建议值）
- stale：建议**先派 1 个子代理**查模型提供方官方文档更新（web_search/browser）；
  更新失败/不可用时 → 用「上次更新至今天之间派出的最大数量 + 1」试探（渐进式，防超实际能力）

用法:
  python concurrency_check.py check                        # 检测状态 + 建议值（立案时）
  python concurrency_check.py record --n 6                 # 记录一次实际派出数（每次立案派出后）
  python concurrency_check.py update --official 2500 --source URL   # 子代理更新官方值后写回
"""
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = SKILL_DIR / "references" / "concurrency-data.json"
FRESHNESS_DAYS = 14


def _load() -> dict:
    if not DATA_FILE.exists():
        return {"updated_at": "1970-01-01", "max_spawned": 0,
                "max_spawned_history": [], "models": {}}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"updated_at": "1970-01-01", "max_spawned": 0,
                "max_spawned_history": [], "models": {}}


def _save(data: dict):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def days_since(updated_at: str) -> int:
    try:
        d = datetime.strptime(updated_at[:10], "%Y-%m-%d").date()
        return (date.today() - d).days
    except Exception:
        return 9999


def check() -> dict:
    """立案时检测：返回 {status, days_since, suggested, reason}。
    suggested = 编排层建议派数上界（max_spawned+1 试探或官方并发），供 --concurrency 采用。"""
    data = _load()
    days = days_since(data.get("updated_at", "1970-01-01"))
    max_spawned = data.get("max_spawned", 0)
    models = data.get("models", {})
    official = max((m.get("official_concurrency", 0) for m in models.values()), default=0)
    if days <= FRESHNESS_DAYS:
        # fresh：官方并发远高于编排层时，建议值 = 历史最大+1（渐进，不超过官方）
        suggested = min(max_spawned + 1, official) if official else max_spawned + 1
        return {"status": "fresh", "days_since": days, "suggested": suggested,
                "reason": f"参考数据 {days} 天前更新（≤{FRESHNESS_DAYS}），官方并发={official}，编排层建议 {suggested}"}
    # stale：需更新；若无法更新 → max_spawned+1 试探
    suggested = min(max_spawned + 1, official) if official else max_spawned + 1
    return {"status": "stale", "days_since": days, "suggested": suggested,
            "reason": f"参考数据 {days} 天前更新（>{FRESHNESS_DAYS}）→ 应先派子代理更新官方文档；失败则用 max_spawned({max_spawned})+1={suggested} 试探"}


def record(n: int):
    """记录一次实际派出数（每次立案派出后调用）。"""
    data = _load()
    hist = data.get("max_spawned_history", [])
    hist.append(n)
    data["max_spawned_history"] = hist[-20:]  # 滚动保留 20 条
    data["max_spawned"] = max(hist)
    _save(data)
    return {"recorded": n, "max_spawned": data["max_spawned"], "history": hist[-20:]}


def update(official: int, source: str, notes: str = ""):
    """子代理成功更新官方文档后写回。"""
    data = _load()
    data["updated_at"] = date.today().isoformat()
    data["models"] = {"default_model": {"official_concurrency": official,
                                        "source_url": source, "notes": notes}}
    _save(data)
    return {"updated_at": data["updated_at"], "official_concurrency": official}


def main():
    ap = argparse.ArgumentParser(description="模型并发参考数据检查器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="检测状态 + 建议值（立案时）")
    rp = sub.add_parser("record", help="记录一次实际派出数")
    rp.add_argument("--n", type=int, required=True)
    up = sub.add_parser("update", help="更新官方并发值（子代理查证后）")
    up.add_argument("--official", type=int, required=True)
    up.add_argument("--source", required=True)
    up.add_argument("--notes", default="")
    args = ap.parse_args()
    if args.cmd == "check":
        r = check()
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.cmd == "record":
        print(json.dumps(record(args.n), ensure_ascii=False, indent=2))
    elif args.cmd == "update":
        print(json.dumps(update(args.official, args.source, args.notes), ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
