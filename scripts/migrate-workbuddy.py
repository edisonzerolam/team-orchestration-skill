#!/usr/bin/env python3
"""migrate-workbuddy — 专家团索引构建 + 批量导入工具

命令:
  python3 scripts/migrate-workbuddy.py build-index            # 预生成 teams-index.json
  python3 scripts/migrate-workbuddy.py verify-index           # 验证索引完整性
  python3 scripts/migrate-workbuddy.py import-agents <src>    # 从 agency-agents 导入独立专家
  python3 scripts/migrate-workbuddy.py build-manifest         # 生成 manifest-post-s2.json
  python3 scripts/migrate-workbuddy.py undo <manifest>        # 回滚导入
"""
import json
import sys
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration"
EXPERT_DIR = SKILL_DIR / "references" / "workbuddy-experts"
SHARED_DIR = SKILL_DIR / "shared"
MANIFEST_PATH = SHARED_DIR / "manifest-post-s2.json"


# ── 自动分组逻辑 ──────────────────────────────────────────

# 基于 agent 名称和目录路径的关键词 → 虚拟团映射
VIRTUAL_TEAM_RULES = [
    ("game-development", ["game", "unity", "unreal", "roblox", "godot", "blender",
                          "level-designer", "narrative-designer", "technical-artist",
                          "game-audio", "game-designer"]),
    ("industry-consulting", ["strategy", "consult", "analyst", "advisor",
                             "market-research", "industry", "business"]),
    ("tencent-ecosystem", ["tencent", "wechat", "weixin", "qq", "tx",
                           "微信", "腾讯", "企业微信"]),
]


def detect_virtual_team(name: str, full_path: str = "") -> str:
    name_lower = name.lower()
    path_lower = full_path.lower()
    for team_name, keywords in VIRTUAL_TEAM_RULES:
        for kw in keywords:
            if kw.lower() in name_lower or kw.lower() in path_lower:
                return team_name
    return "ungrouped"


# ── 分类 ID 映射 ──────────────────────────────────────────

CATEGORY_MAP = {
    "academic": "01-Academic",
    "design": "02-Design",
    "engineering": "03-Engineering",
    "finance": "04-Finance",
    "game-development": "05-GameDev",
    "gis": "06-GIS",
    "healthcare": "07-Healthcare",
    "integrations": "08-Integrations",
    "marketing": "09-Marketing",
    "paid-media": "10-PaidMedia",
    "product": "11-Product",
    "project-management": "12-ProjectMgmt",
    "sales": "13-Sales",
    "security": "14-Security",
    "spatial-computing": "15-Spatial",
    "specialized": "16-Specialized",
    "strategy": "17-Strategy",
    "support": "18-Support",
    "testing": "19-Testing",
}


# ── 索引构建 ──────────────────────────────────────────


def extract_capabilities_from_desc(desc: dict) -> list:
    words = set()
    for lang in ("en", "zh"):
        text = desc.get(lang, "")
        for sep in ("/", "，", ",", " ", "、"):
            for token in text.split(sep):
                token = token.strip().lower()
                if 2 <= len(token) <= 30:
                    words.add(token)
    return sorted(words)


def build_teams_index() -> list:
    teams = []
    if not EXPERT_DIR.exists():
        print(f"[WARN] {EXPERT_DIR} 不存在", file=sys.stderr)
        return teams

    failed = 0
    for plugin_dir in sorted(EXPERT_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue
        pj = plugin_dir / "plugin.json"
        if not pj.exists():
            continue
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            agents_dir = plugin_dir / "agents"
            agent_count = len(list(agents_dir.glob("*.md"))) if agents_dir.exists() else 0
            entry = {
                "n": plugin_dir.name,
                "dN": data.get("displayName", {}).get("zh", ""),
                "dD": data.get("displayDescription", {}).get("zh", ""),
                "cId": data.get("categoryId", ""),
                "eT": data.get("expertType", ""),
                "lN": data.get("members", [{}])[0].get("name", {}).get("zh", "") if data.get("members") else "",
                "aC": agent_count,
            }
            teams.append(entry)
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
            failed += 1
            print(f"[WARN] 跳过 {plugin_dir.name}: {e}", file=sys.stderr)
            continue

    teams.sort(key=lambda x: x["n"])
    print(f"构建索引完成: {len(teams)} 团, {failed} 跳过", file=sys.stderr)
    return teams


def write_index(teams: list):
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    path = SHARED_DIR / "teams-index.json"
    payload = {
        "version": "1.0",
        "generated": None,
        "teams": teams,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_kb = len(path.read_bytes()) / 1024
    print(f"已写入 {path} ({len(teams)} 团, {size_kb:.1f}KB)", file=sys.stderr)


def verify_index():
    path = SHARED_DIR / "teams-index.json"
    if not path.exists():
        print(f"[FAIL] teams-index.json 不存在", file=sys.stderr)
        return False

    data = json.loads(path.read_text(encoding="utf-8"))
    teams = data.get("teams", [])
    print(f"索引版本: {data.get('version')}", file=sys.stderr)
    print(f"团数量: {len(teams)}", file=sys.stderr)

    issues = 0
    for t in teams:
        name = t.get("n", "?")
        if not t.get("cId"):
            print(f"  [WARN] {name}: categoryId 为空", file=sys.stderr)
            issues += 1
        if t.get("aC", 0) == 0:
            print(f"  [WARN] {name}: agentCount 为 0", file=sys.stderr)
            issues += 1

    actual_dirs = set(d.name for d in EXPERT_DIR.iterdir() if d.is_dir())
    indexed = set(t["n"] for t in teams)
    missing = actual_dirs - indexed
    extra = indexed - actual_dirs
    if missing:
        print(f"  [WARN] 未索引的目录: {missing}", file=sys.stderr)
    if extra:
        print(f"  [WARN] 索引中存在但文件系统缺失: {extra}", file=sys.stderr)

    if issues:
        print(f"[CONDITIONAL] {issues} 个团有警告", file=sys.stderr)
    else:
        print("[OK] 索引验证通过", file=sys.stderr)
    return issues == 0


# ── 独立专家导入 ──────────────────────────────────────────


def make_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")


def import_individual_agents(source_dir: Path, dry_run: bool = False) -> list:
    if not source_dir.exists():
        print(f"[FAIL] 源目录不存在: {source_dir}", file=sys.stderr)
        return []

    manifest = []
    imported = 0
    skipped = 0
    exclude_categories = {".", ".github", "examples", "scripts"}

    for category_dir in sorted(source_dir.iterdir()):
        if not category_dir.is_dir() or category_dir.name in exclude_categories or category_dir.name.startswith("."):
            continue
        category = category_dir.name
        category_id = CATEGORY_MAP.get(category, f"99-{category.capitalize()}")

        md_files = sorted(category_dir.rglob("*.md"))
        for md_path in md_files:
            if "README" in md_path.name.upper():
                continue

            stem = md_path.stem
            agent_slug = make_slug(stem)
            target_dir_name = f"{category}-{agent_slug}"
            target_dir = EXPERT_DIR / target_dir_name

            if target_dir.exists():
                skipped += 1
                continue

            agent_text = md_path.read_text(encoding="utf-8", errors="replace")
            virtual_team = detect_virtual_team(target_dir_name, str(md_path))

            entry = {
                "source": str(md_path),
                "target_dir": str(target_dir),
                "agent_name": stem,
                "agent_slug": agent_slug,
                "category": category,
                "category_id": category_id,
                "virtual_team": virtual_team,
            }

            if not dry_run:
                agents_subdir = target_dir / "agents"
                agents_subdir.mkdir(parents=True, exist_ok=True)

                pj_data = {
                    "name": target_dir_name,
                    "version": "1.0.0",
                    "description": f"Individual expert: {stem}",
                    "author": {"name": "Expert Marketplace"},
                    "license": "MIT",
                    "expertType": "individual",
                    "agentName": "expert",
                    "displayName": {"en": stem, "zh": stem},
                    "displayDescription": {"en": f"Individual expert from {category}", "zh": f"来自 {category} 的独立专家"},
                    "categoryId": category_id,
                    "avatar": "",
                    "members": [{"name": {"en": stem, "zh": stem}, "role": "expert"}],
                    "agents": ["./agents/expert.md"],
                }
                (target_dir / "plugin.json").write_text(
                    json.dumps(pj_data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                shutil.copy2(str(md_path), str(agents_subdir / "expert.md"))

            manifest.append(entry)
            imported += 1

    print(f"导入完成: {imported} 个专家导入, {skipped} 个跳过 (已存在)", file=sys.stderr)
    return manifest


# ── Manifest 管理 ──────────────────────────────────────────


def build_manifest(manifest_entries: list = None):
    path = MANIFEST_PATH
    if manifest_entries is None:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data
        return {"version": "2.0", "generated": None, "files": []}

    payload = {
        "version": "2.0",
        "generated": datetime.now(timezone.utc).isoformat(),
        "files": manifest_entries,
    }
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"清单已写入: {path} ({len(manifest_entries)} 条目)", file=sys.stderr)
    return payload


def undo_import(manifest_path: str):
    path = Path(manifest_path)
    if not path.exists():
        print(f"[FAIL] 清单不存在: {path}", file=sys.stderr)
        return False

    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("files", [])
    removed = 0
    failed = 0

    for entry in entries:
        target_dir = Path(entry["target_dir"])
        if target_dir.exists():
            try:
                shutil.rmtree(target_dir)
                removed += 1
            except OSError as e:
                print(f"  [FAIL] 删除失败 {target_dir}: {e}", file=sys.stderr)
                failed += 1

    print(f"回滚完成: 删除 {removed} 个目录, {failed} 个失败", file=sys.stderr)
    return failed == 0


# ── 入口 ──────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 migrate-workbuddy.py <command> [args...]", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  build-index             预生成 teams-index.json", file=sys.stderr)
        print("  verify-index            验证索引完整性", file=sys.stderr)
        print("  import-agents <src>     从 agency-agents 导入独立专家", file=sys.stderr)
        print("  import-agents --dry-run <src>  试运行 (不写文件)", file=sys.stderr)
        print("  build-manifest          生成 manifest-post-s2.json", file=sys.stderr)
        print("  undo <manifest>         回滚导入 (删除所有文件)", file=sys.stderr)
        return 1

    cmd = sys.argv[1]

    if cmd == "build-index":
        teams = build_teams_index()
        write_index(teams)

    elif cmd == "verify-index":
        ok = verify_index()
        return 0 if ok else 1

    elif cmd == "import-agents":
        dry_run = False
        src_arg = None
        if len(sys.argv) >= 3 and sys.argv[2] == "--dry-run":
            dry_run = True
            src_arg = sys.argv[3] if len(sys.argv) >= 4 else None
        else:
            src_arg = sys.argv[2] if len(sys.argv) >= 3 else None

        if not src_arg:
            print("[FAIL] 需要指定源目录路径", file=sys.stderr)
            return 1

        source_dir = Path(src_arg)
        if not source_dir.exists():
            print(f"[FAIL] 源目录不存在: {source_dir}", file=sys.stderr)
            return 1

        manifest = import_individual_agents(source_dir, dry_run=dry_run)
        if manifest and not dry_run:
            build_manifest(manifest)

        if dry_run:
            print(f"[DRY RUN] 试运行: 将导入 {len(manifest)} 个专家", file=sys.stderr)

    elif cmd == "build-manifest":
        build_manifest()

    elif cmd == "undo":
        manifest_path = sys.argv[2] if len(sys.argv) >= 3 else str(MANIFEST_PATH)
        ok = undo_import(manifest_path)
        return 0 if ok else 1

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
