#!/usr/bin/env python3
"""token_budget.py — Per-phase token budget control (P0.6).

Tracks token consumption per phase, warns at 80%, blocks (unless override)
past 100%. Implements the v2.6 cost-control acceptance dimension.
"""
import json
from pathlib import Path


class TokenBudget:
    WARN_RATIO = 0.80
    LIMIT_RATIO = 1.00

    def __init__(self, limits, state_file=None):
        # limits: dict phase -> max tokens
        self.limits = dict(limits)
        self.usage = {p: 0 for p in limits}
        self.state_file = Path(state_file) if state_file else None
        if self.state_file and self.state_file.exists():
            try:
                self.usage.update(json.loads(self.state_file.read_text(encoding="utf-8")))
            except Exception:
                pass

    def set_limit(self, phase, limit):
        self.limits[phase] = limit
        self.usage.setdefault(phase, 0)

    def _ratio(self, phase):
        lim = self.limits.get(phase, 0)
        if lim <= 0:
            return 1.0
        return self.usage.get(phase, 0) / lim

    def consume(self, phase, tokens, override=False):
        """Record token usage. Returns dict with status.

        status: 'ok' | 'warn' | 'exceeded'
        Blocked when exceeded and not override.
        """
        self.usage[phase] = self.usage.get(phase, 0) + tokens
        ratio = self._ratio(phase)
        if ratio >= self.LIMIT_RATIO:
            status = "exceeded"
            blocked = not override
        elif ratio >= self.WARN_RATIO:
            status = "warn"
            blocked = False
        else:
            status = "ok"
            blocked = False
        self._persist()
        return {
            "phase": phase,
            "consumed": tokens,
            "total": self.usage[phase],
            "limit": self.limits.get(phase, 0),
            "ratio": round(ratio, 4),
            "status": status,
            "blocked": blocked,
        }

    def can_proceed(self, phase, estimated, override=False):
        lim = self.limits.get(phase, 0)
        projected = self.usage.get(phase, 0) + estimated
        if lim <= 0:
            return True
        if projected > lim and not override:
            return False
        return True

    def report(self):
        return {
            p: {
                "used": self.usage.get(p, 0),
                "limit": self.limits.get(p, 0),
                "ratio": round(self._ratio(p), 4),
            } for p in self.limits
        }

    def _persist(self):
        if self.state_file:
            try:
                self.state_file.write_text(
                    json.dumps(self.usage, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass


# P1-1: effort 分级预算预设（规模门四档：子代理上限 + 各阶段 token 上限）。
# 注：此处 L1-L4 为"token 预算档位"，与 test-workflow B2 的"规模门无 L4 独立档位"不冲突——
# B2 指规模门判据档位，此处指预算档位，二者按维度复用（文档侧注明）。
EFFORT_TIERS = {
    "L1": {"sub_agents": 1, "token_cap": 4000},
    "L2": {"sub_agents": 3, "token_cap": 8000},
    "L3": {"sub_agents": 6, "token_cap": 16000},
    "L4": {"sub_agents": 8, "token_cap": 32000},
}

# 二审终审制六阶段（与 orchestrator 的 archive 阶段目录清单一致）
PHASES = ["立案", "举证", "质证", "一审", "回灌修订", "二审终审"]


def effort_limits(effort):
    """返回某档位的预设预算：{effort, sub_agents, token_cap, limits{阶段: token 上限}}。"""
    tier = EFFORT_TIERS[effort]
    return {
        "effort": effort,
        "sub_agents": tier["sub_agents"],
        "token_cap": tier["token_cap"],
        "limits": {p: tier["token_cap"] for p in PHASES},
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Token budget controller")
    ap.add_argument("--limits", default="",
                    help="JSON: {phase: max_tokens}（与 --effort 二选一；同时给出则按阶段覆盖档位默认）")
    ap.add_argument("--effort", default="", choices=sorted(EFFORT_TIERS),
                    help="effort 档位预设预算（L1-L4：子代理上限 + 各阶段 token 上限，P1-1）")
    ap.add_argument("--consume", default="", help="JSON: [phase, tokens]")
    ap.add_argument("--override", action="store_true")
    args = ap.parse_args()

    if args.effort:
        presets = effort_limits(args.effort)
        limits = dict(presets["limits"])
        if args.limits:
            limits.update(json.loads(args.limits))
        info = {"effort": args.effort,
                "sub_agents": presets["sub_agents"],
                "token_cap": presets["token_cap"]}
    else:
        if not args.limits:
            ap.error("需要 --limits 或 --effort 之一")
        limits = json.loads(args.limits)
        info = None

    budget = TokenBudget(limits)
    if args.consume:
        phase, tokens = json.loads(args.consume)
        res = budget.consume(phase, tokens, override=args.override)
        if info:
            res["effort"] = info["effort"]
            res["sub_agents"] = info["sub_agents"]
        print(json.dumps(res, ensure_ascii=False))
        if res["blocked"]:
            raise SystemExit(2)
    else:
        out = budget.report()
        if info:
            out = {"effort": info, "usage": out}
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
