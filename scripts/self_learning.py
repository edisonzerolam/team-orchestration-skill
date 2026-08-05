#!/usr/bin/env python3
"""self_learning.py - Self-learning pipeline S2-S4 (P0.3).

S1 (trial counting) is handled inside trial-court-orchestrator.py.
This module adds:
  S2 (experience sedimentation): persist structured per-trial experience.
  S3 (pattern induction): aggregate experiences into recurring patterns.
  S4 (strategy evolution): derive routing/matcher preferences from S3.
"""
import json
import datetime
from pathlib import Path


def _learning_dir():
    base = Path(__file__).resolve().parent.parent / "references" / "learning-data"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _now_iso():
    return datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).isoformat()


def process_trial(docket, archive_dir):
    """Run S2-S4 for a completed trial. archive_dir may be Path or str."""
    d = _learning_dir()
    _s2_record_experience(d, docket, archive_dir)
    _s3_induce_patterns(d)
    _s4_evolve_strategy(d)
    return True


def _s2_record_experience(d, docket, archive_dir):
    exp_file = d / "experiences.json"
    exps = []
    if exp_file.exists():
        try:
            exps = json.loads(exp_file.read_text(encoding="utf-8"))
        except Exception:
            exps = []
    rec = {
        "docket_id": docket.get("docket_id"),
        "issue_type": docket.get("issue_type", "Unclassified"),
        "roles": [r.get("name") for r in docket.get("roles", [])],
        "sub_agent_count": docket.get("sub_agent_count", 0),
        "assets": docket.get("assets_resolved", {}),
        "archived_at": str(archive_dir),
        "ts": _now_iso(),
    }
    exps.append(rec)
    exp_file.write_text(json.dumps(exps, ensure_ascii=False, indent=2), encoding="utf-8")


def _s3_induce_patterns(d):
    exp_file = d / "experiences.json"
    if not exp_file.exists():
        return
    exps = json.loads(exp_file.read_text(encoding="utf-8"))
    by_type = {}
    for e in exps:
        it = e.get("issue_type", "Unclassified")
        assets = e.get("assets", {})
        used = [k for k, v in assets.items() if v]
        by_type.setdefault(it, {})
        for u in used:
            by_type[it][u] = by_type[it].get(u, 0) + 1
    patterns = {
        "by_issue_type_assets": by_type,
        "total_experiences": len(exps),
        "ts": _now_iso(),
    }
    (d / "patterns.json").write_text(
        json.dumps(patterns, ensure_ascii=False, indent=2), encoding="utf-8")


def _s4_evolve_strategy(d):
    patterns_file = d / "patterns.json"
    if not patterns_file.exists():
        return
    patterns = json.loads(patterns_file.read_text(encoding="utf-8"))
    by_type = patterns.get("by_issue_type_assets", {})
    strategy = {}
    for it, asset_counts in by_type.items():
        if not asset_counts:
            continue
        top = max(asset_counts.items(), key=lambda kv: kv[1])
        strategy[it] = {"preferred_asset": top[0], "usage": top[1]}
    out = {"strategy": strategy, "ts": _now_iso()}
    (d / "strategy.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def maturity_level():
    """Return self-learning maturity: 1 (S1 only) .. 4 (S1-S4)."""
    d = _learning_dir()
    level = 1
    if (d / "experiences.json").exists():
        level = 2
    if (d / "patterns.json").exists():
        level = 3
    if (d / "strategy.json").exists():
        level = 4
    return level
