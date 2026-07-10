#!/usr/bin/env python3
"""去除 UTF-8 BOM，将 UTF-8-SIG 文件转为纯 UTF-8。同时报告真正损坏的文件。"""
import os
from pathlib import Path

SKILL_DIR = Path(r"C:\Users\林昌\.config\opencode\skills\team-orchestration")

TARGETS = [
    "references/ANALYSIS-DATA.md",
    "references/workbuddy-experts/_index.md",
    "references/team-templates/index.md",
    "references/expert-matching.md",
    "references/cross-validation.md",
    "references/communication.md",
    "references/patterns.md",
    "SKILL.md",
    "references/data/summary/stats.json",
]

# 自动发现 knowledge/ 下的 .md 文件
knowledge_dir = SKILL_DIR / "references" / "knowledge"
if knowledge_dir.is_dir():
    for f in sorted(knowledge_dir.iterdir()):
        if f.suffix == ".md":
            TARGETS.append(str(f.relative_to(SKILL_DIR)))

BOM = b'\xef\xbb\xbf'
fixed = 0
missing = []
broken = []

for rel in TARGETS:
    path = SKILL_DIR / rel
    if not path.exists():
        missing.append(rel)
        continue
    raw = path.read_bytes()
    # 检查 BOM
    if raw.startswith(BOM):
        path.write_bytes(raw[len(BOM):])
        print(f"  [FIXED] 去除 BOM: {rel}")
        fixed += 1
    else:
        # 验证能否用 utf-8 解码
        try:
            raw.decode('utf-8')
        except UnicodeDecodeError:
            # 尝试 GBK
            try:
                gbk_text = raw.decode('gbk')
                path.write_bytes(gbk_text.encode('utf-8'))
                print(f"  [FIXED] GBK->UTF-8 转码: {rel}")
                fixed += 1
            except UnicodeDecodeError:
                broken.append(rel)

if missing:
    print(f"\n[WARN] {len(missing)} 个文件不存在:")
    for m in missing:
        print(f"  - {m}")
if broken:
    print(f"\n[ERROR] {len(broken)} 个文件编码完全损坏:")
    for b in broken:
        print(f"  - {b}")
if fixed == 0 and not missing and not broken:
    print("[OK] 所有文件编码正确，无需修复")
else:
    print(f"\n总计: 修复 {fixed} 个, 缺失 {len(missing)} 个, 损坏 {len(broken)} 个")
