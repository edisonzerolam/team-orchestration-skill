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


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Token budget controller")
    ap.add_argument("--limits", required=True, help="JSON: {phase: max_tokens}")
    ap.add_argument("--consume", default="", help="JSON: [phase, tokens]")
    ap.add_argument("--override", action="store_true")
    args = ap.parse_args()
    budget = TokenBudget(json.loads(args.limits))
    if args.consume:
        phase, tokens = json.loads(args.consume)
        res = budget.consume(phase, tokens, override=args.override)
        print(json.dumps(res, ensure_ascii=False))
        if res["blocked"]:
            raise SystemExit(2)
    else:
        print(json.dumps(budget.report(), ensure_ascii=False))


if __name__ == "__main__":
    main()
