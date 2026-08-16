#!/usr/bin/env python3
"""cycle_detector.py — Agent call-cycle detector (P0.7).

Detects A->B->A->B style loops in an agent invocation graph so the
orchestrator can block runaway circular delegation.
"""
import sys
import json
from pathlib import Path


class CycleDetector:
    def __init__(self):
        self.graph = {}  # node -> set(callees)

    def add_edge(self, caller, callee):
        self.graph.setdefault(caller, set()).add(callee)

    def load_edges(self, pairs):
        """pairs: list of (caller, callee) in call order."""
        for caller, callee in pairs:
            self.add_edge(caller, callee)

    def detect(self):
        """Return the cycle path (list ending with the start node) or None."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self.graph}
        for callees in self.graph.values():
            for n in callees:
                color.setdefault(n, WHITE)
        stack = []

        def dfs(u):
            color[u] = GRAY
            stack.append(u)
            for v in self.graph.get(u, ()):
                c = color.get(v, WHITE)
                if c == GRAY:
                    idx = stack.index(v)
                    return stack[idx:] + [v]
                if c == WHITE:
                    r = dfs(v)
                    if r:
                        return r
            stack.pop()
            color[u] = BLACK
            return None

        for n in list(color.keys()):
            if color[n] == WHITE:
                r = dfs(n)
                if r:
                    return r
        return None

    def has_cycle(self):
        return self.detect() is not None


def main():
    ap = __import__("argparse").ArgumentParser(description="Agent cycle detector")
    ap.add_argument("--edges", required=True,
                    help="JSON file: list of [caller, callee] pairs")
    args = ap.parse_args()
    # utf-8-sig：容忍 Windows 记事本/编辑器写入的 UTF-8 BOM（v3.8 功能自检发现，TC-20260816-4）
    pairs = json.loads(Path(args.edges).read_text(encoding="utf-8-sig"))
    det = CycleDetector()
    det.load_edges(pairs)
    cyc = det.detect()
    if cyc:
        print("CYCLE DETECTED:", " -> ".join(cyc))
        print("ACTION: block further delegation along this loop")
        sys.exit(1)
    else:
        print("NO CYCLE")
        sys.exit(0)


if __name__ == "__main__":
    main()
