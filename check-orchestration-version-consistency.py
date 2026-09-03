#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双副本一致性检查脚本（P0-2 漂移治理补充，v2.0）

用途：校验各平台 team-orchestration 副本的 _meta.json 版本与 ZCode 权威副本对齐。
- ZCode 权威副本：~/.agents/skills/agent-ops/skills/team-orchestration
- 非权威副本（如 WorkBuddy）的 SKILL.md 协议内容可能 intentional 保留旧版，
  因此一致性检查以 _meta.json version 与权威副本版本对齐为准。

用法：
    python check-orchestration-version-consistency.py
退出码：0 = 全部一致；1 = 存在漂移
"""
import json
import re
import sys
from pathlib import Path


def get_skills_md_frontmatter(md_path: Path):
    """解析 SKILL.md frontmatter 的 version 字段（兼容 CRLF/BOM）。"""
    if not md_path.exists():
        return None
    try:
        text = md_path.read_text(encoding="utf-8-sig")
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")

        fm_start = None
        for i, line in enumerate(lines):
            if line.strip() == "---":
                fm_start = i
                break
        if fm_start is None:
            return None

        fm_lines = lines[fm_start + 1:]
        end_idx = None
        for j in range(len(fm_lines)):
            if fm_lines[j].strip() == "---":
                end_idx = j
                break
        if end_idx is None:
            return None

        content = "\n".join(lines[fm_start + 1: fm_start + 1 + end_idx])
        v_match = re.search(r'"version"\s*:\s*"([^"]+)"|version\s*:\s*([^\s]+)', content)
        if v_match:
            return v_match.group(1) if v_match.group(1) else v_match.group(2)
        return None
    except Exception:
        return None


def check_platform(team_dir: Path, authoritative_version: str) -> dict:
    """检查单个平台副本的 _meta.json 版本是否与权威版本对齐。

    非权威副本的 SKILL.md 协议内容可能 intentional 保留旧版，
    因此仅校验 _meta.json version，不要求 SKILL.md frontmatter 一致。
    """
    meta_path = team_dir / "_meta.json"
    if not meta_path.exists():
        return {
            "platform": str(team_dir),
            "status": "missing_meta",
            "issues": [{"type": "missing_meta", "severity": "P0", "message": f"{team_dir} 缺少 _meta.json"}],
        }
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {
            "platform": str(team_dir),
            "status": "invalid_meta",
            "issues": [{"type": "invalid_meta", "severity": "P0", "message": f"{team_dir} _meta.json 解析失败"}],
        }

    meta_version = meta.get("version")
    if meta_version != authoritative_version:
        return {
            "platform": str(team_dir),
            "status": "mismatched",
            "issues": [{
                "type": "version_mismatch",
                "severity": "P0",
                "message": f"{team_dir} _meta.json version({meta_version}) 与权威副本 version({authoritative_version}) 不一致",
            }],
        }
    return {"platform": str(team_dir), "status": "consistent", "version": meta_version}


def main():
    home = Path.home()
    authoritative = home / ".agents" / "skills" / "agent-ops" / "skills" / "team-orchestration"

    # Step 1: 权威副本自身一致性检查（_meta.json version == SKILL.md frontmatter version）
    if not authoritative.exists():
        print(f"[错误] 权威副本不存在: {authoritative}")
        sys.exit(1)

    meta_a = json.loads((authoritative / "_meta.json").read_text(encoding="utf-8-sig"))
    md_a_version = get_skills_md_frontmatter(authoritative / "SKILL.md")
    meta_a_version = meta_a.get("version")

    print(f"[检查] 权威副本 {authoritative}")
    print(f"  _meta.json version: {meta_a_version}")
    print(f"  SKILL.md frontmatter version: {md_a_version}")

    if meta_a_version != md_a_version:
        print(f"[失败] 权威副本自身版本不一致，跳过其余检查")
        sys.exit(1)
    print(f"[通过] 权威副本自身一致")

    # Step 2: 检测已知平台副本
    known_platforms = [
        home / ".workbuddy" / "skills" / "team-orchestration",
        home / ".claude" / "skills" / "team-orchestration",
        home / ".codex" / "skills" / "team-orchestration",
    ]
    found_platforms = [p for p in known_platforms if p.exists() and (p / "_meta.json").exists()]
    print(f"\n[扫描] 发现 {len(found_platforms)} 个非权威平台副本")

    # Step 3: 逐平台校验
    has_issue = False
    for p in found_platforms:
        result = check_platform(p, meta_a_version)
        if result["status"] == "consistent":
            print(f"  [一致] {p}: version={result['version']}")
        else:
            has_issue = True
            for issue in result.get("issues", []):
                print(f"  [{issue['severity']}] {result['platform']}: {issue['message']}")

    # Step 4: 结论
    print(f"\n[权威版本] v{meta_a_version}")
    if has_issue:
        print("[结论] 存在双副本漂移，退出码 1（需治理）")
        sys.exit(1)
    else:
        print("[结论] 全部副本版本一致，退出码 0")
        sys.exit(0)


if __name__ == "__main__":
    main()
