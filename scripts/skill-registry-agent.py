#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill-registry-agent.py — 远程技能清单枚举器（TC-20260816-7 · 跨机器技能发现）

在任何一台机器上运行，输出该机已安装技能的 JSON 清单，供主控机合并进技能注册表
（references/skill-registry.json）。部署方式：整个 team-orchestration 目录拷到目标机
（脚本与 asset-resolver.py 同目录），或单独拷本脚本 + asset-resolver.py。

用法：
    python skill-registry-agent.py                          # 扫描默认双根并输出 JSON
    python skill-registry-agent.py --root ~/.agents/skills  # 只扫指定根
    python skill-registry-agent.py --out ./my-skills.json   # 写入文件（UTF-8）

输出结构：
{
  "agent_version": "1.0.0",
  "host": "<主机名>",
  "generated_at": "ISO8601",
  "roots": ["..."],
  "skills": [{"name","description","triggers","source","path"}]
}
"""
import argparse
import datetime
import importlib.util
import json
import platform
import sys
from pathlib import Path

# Windows GBK 控制台防护（同 asset-resolver）：技能描述含大量 emoji，cp936 下直接 UnicodeEncodeError 崩溃
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _load_discover():
    """优先复用同目录 asset-resolver.py 的发现引擎；缺失时降级内置精简解析。"""
    here = Path(__file__).resolve().parent
    resolver = here / "asset-resolver.py"
    if resolver.exists():
        spec = importlib.util.spec_from_file_location("asset_resolver", resolver)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _builtin_scan(root: Path, source: str) -> list:
    """精简内置扫描（无 asset-resolver 时兜底）：仅顶层 <name>/SKILL.md，解析 name/description/disabled。"""
    skills = []
    if not root.exists():
        return skills
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        md = d / "SKILL.md"
        if not md.exists():
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        name, desc, disabled = "", "", False
        in_fm = False
        for line in text.splitlines()[:40]:
            s = line.strip()
            if s == "---":
                in_fm = not in_fm
                continue
            if in_fm:
                k, _, v = line.partition(":")
                kl = k.strip().lower()
                if kl == "name":
                    name = v.strip().strip("\"'")
                elif kl == "description":
                    desc = v.strip()
                elif kl in ("disabled", "disable-model-invocation"):
                    if v.strip().lower() in ("true", "yes", "1"):
                        disabled = True
        if not disabled:
            skills.append({
                "name": name or d.name,
                "description": desc,
                "triggers": [],
                "source": source,
                "path": str(d),
            })
    return skills


def main():
    ap = argparse.ArgumentParser(description="远程技能清单枚举器")
    ap.add_argument("--root", default="", help="技能根（可多次指定；缺省 = ~/.agents/skills + ~/.workbuddy/skills）")
    ap.add_argument("--out", default="", help="输出文件（缺省 stdout）")
    ap.add_argument("--source", default="agents", help="source 标注（缺省 agents）")
    ap.add_argument("--project-dir", default="", help="附加扫描项目级技能根 <dir>/.dsh/skills、<dir>/.agents/skills")
    args = ap.parse_args()

    mod = _load_discover()
    roots = []
    if args.root:
        roots.append((Path(args.root).expanduser(), args.source))
    else:
        home = Path.home()
        if mod is not None:
            roots = mod.discover_skill_roots(args.project_dir)
        else:
            roots = [(home / ".agents" / "skills", "agents")]
            if (home / ".workbuddy" / "skills").exists():
                roots.append((home / ".workbuddy" / "skills", "workbuddy"))

    skills = []
    if mod is not None:
        for r, src in roots:
            skills.extend(mod.discover_skills_from(r, src))
    else:
        for r, src in roots:
            skills.extend(_builtin_scan(r, src))

    payload = {
        "agent_version": "1.0.0",
        "host": platform.node(),
        "generated_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "roots": [str(r) for r, _ in roots],
        "skills": skills,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print("written: %s (%d skills)" % (args.out, len(skills)))
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    main()
