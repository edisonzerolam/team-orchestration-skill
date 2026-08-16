#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-shared-refs.py — 共享人设引用校验器（TC-20260816-9 · P2 机制）

校验 agents/*.md 中形如 `_shared/<name>.md` 的引用是否存在（防共享后引用断裂）。
用法：python scripts/check-shared-refs.py   （退出码 0=全部存在 / 1=存在断裂）
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXPERTS = Path(__file__).resolve().parent.parent / "references" / "workbuddy-experts"
SHARED = EXPERTS / "_shared"

REF = re.compile(r"`?_shared/([\w.-]+\.md)`?")

def main():
    missing = []
    refs = 0
    for md in EXPERTS.rglob("agents/*.md"):
        t = md.read_text(encoding="utf-8", errors="replace")
        for m in REF.finditer(t):
            refs += 1
            if not (SHARED / m.group(1)).exists():
                missing.append("%s -> _shared/%s" % (md.relative_to(EXPERTS), m.group(1)))
    print("共享引用 %d 处，_shared 文件 %d 个" % (refs, len(list(SHARED.glob("*.md"))) if SHARED.exists() else 0))
    if missing:
        print("❌ 断裂引用：")
        for x in missing[:20]:
            print("  " + x)
        sys.exit(1)
    print("✅ 全部共享引用存在" if refs else "（当前无共享引用——_shared 为角色定义规范层）")
    sys.exit(0)

if __name__ == "__main__":
    main()
