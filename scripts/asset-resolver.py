#!/usr/bin/env python3
# 资产解析器（现行后端）：按议题类型从 WorkBuddy 资产体系（专家/技能/MCP/连接器）解析可用资产，供审判庭 Phase A 注入
# -*- coding: utf-8 -*-
"""asset-resolver.py — QoderWork 资产解析器

动态发现并匹配 QoderWork 全套资产（技能/插件/MCP工具/连接器/专家团），
按议题类型生成可注入子代理 prompt 的 "可用资源" 块。
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
"""

用法：
    # 全量扫描并生成资产快照
    python asset-resolver.py --snapshot

    # 按议题类型匹配资产
    python asset-resolver.py --match "08-FinanceInvestment"

    # 自动从立案记录中提取议题类型并匹配
    python asset-resolver.py --docket ./docket.json

    # 输出 JSON 机器可读
    python asset-resolver.py --match "11-SecurityCompliance" --json

    # 列出所有已发现的资产分类
    python asset-resolver.py --list-types
"""
import json
import os
import sys
import argparse
import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
WORKBUDDY_HOME = Path.home() / ".workbuddy"

ASSET_SNAPSHOT_PATH = SKILL_DIR / "references" / "last-asset-snapshot.json"
ASSET_MAP_PATH = SKILL_DIR / "references" / "asset-issue-map.md"

# ─── 发现引擎 ────────────────────────────────────────────────

# ─── 1. 技能发现 ───

def discover_skills() -> list[dict]:
    """扫描 ~/.workbuddy/skills/<name>/SKILL.md 的 description"""
    skills = []
    skills_dir = WORKBUDDY_HOME / "skills"
    if not skills_dir.exists():
        return skills

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        # 排除备份/临时/模板目录：.backup 结尾、backup- 前缀、.bak 结尾、.tmp、~ 备份后缀
        name_lower = skill_dir.name.lower()
        if (".backup" in name_lower or name_lower.startswith("backup-")
                or name_lower.endswith(".bak") or name_lower.endswith(".tmp")
                or name_lower.endswith("~") or ".old" in name_lower):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        description = ""
        triggers = []
        disabled = False
        in_frontmatter = False
        try:
            raw_bytes = skill_md.read_bytes()
            text = None
            # 优先 UTF-8；失败则尝试 GB18030（兼容历史 GBK 编码的 SKILL.md），杜绝 U+FFFD 乱码注入
            for enc in ("utf-8", "gb18030"):
                try:
                    text = raw_bytes.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                text = raw_bytes.decode("utf-8", errors="replace")
            lines = text.splitlines()
            # frontmatter 是文件头 `---` 到下一个 `---` 之间的 YAML 块；
            # 状态机：in_fm=False，遇到第 1 个 --- 进入、第 2 个 --- 退出，仅取前 40 行内的边界。
            in_fm = False
            fm_dashes = 0
            for line in lines[:40]:
                stripped = line.strip()
                if stripped == "---":
                    fm_dashes += 1
                    in_fm = fm_dashes % 2 == 1
                    if fm_dashes >= 2 and not in_fm:
                        break
                    continue
                if in_fm:
                    line_lower = line.lower().strip()
                    key, _, val = line.partition(":")
                    key_l = key.strip().lower()
                    val_l = val.strip().lower()
                    if key_l == "disabled":
                        disabled = val_l in ("true", "yes", "1")
                        if disabled:
                            break
                    if key_l == "description":
                        description = val.strip()
                    if line_lower.startswith("triggers:") or line_lower.startswith("当"):
                        triggers.append(line.strip())
        except Exception:
            pass
        if disabled:
            continue

        skills.append({
            "name": skill_dir.name,
            "description": description[:300],
            "triggers": triggers[:5],
            "path": str(skill_dir),
            "type": "skill"
        })
    return skills


# ─── 2. MCP 工具发现 ───

def discover_mcp_tools() -> list[dict]:
    """读取 connector-states 和 mcp.json 发现已连接的 MCP 工具"""
    tools = []

    # 查找 connector-states
    connector_dirs = list(WORKBUDDY_HOME.glob("connectors/*/connector-states*.json"))
    mcp_files = list(WORKBUDDY_HOME.glob("connectors/*/mcp.json"))

    if not connector_dirs or not mcp_files:
        return tools

    # 取最新的状态文件
    state_file = max(connector_dirs, key=lambda p: p.stat().st_mtime)
    mcp_file = max(mcp_files, key=lambda p: p.stat().st_mtime)

    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        mcp_config = json.loads(mcp_file.read_text(encoding="utf-8"))
    except Exception:
        return tools

    enabled = state.get("enabled", state.get("everConnected", []))

    issue_type_map = {
        "tdx-connector": ["08-FinanceInvestment", "A股", "股票", "金融", "财务"],
        "westock-mcp": ["08-FinanceInvestment", "股票", "ETF", "基金", "自选股"],
        "qq-mail": ["通用", "通信", "邮件"],
        "github": ["02-Engineering", "代码", "开发", "Git"],
        "tencent-map": ["通用", "地理", "位置", "地图"],
        "qcc-company": ["11-SecurityCompliance", "工商", "企业信息", "合规"],
        "tmeet": ["通用", "会议", "协作"],
    }

    for connector in enabled:
        config = mcp_config.get("mcpServers", {}).get(f"connector:{connector}", {})
        disabled = config.get("disabled", False)
        url = config.get("url", "")

        # 从连接器 skill SKILL.md 提取能力描述
        connector_skill_dir = WORKBUDDY_HOME / "connectors" / "skills" / f"connector-{connector}"
        capabilities = []
        skill_md = connector_skill_dir / "SKILL.md"
        if skill_md.exists():
            try:
                text = skill_md.read_text(encoding="utf-8", errors="replace")
                # 取前 5 行非空内容作为能力描述
                for line in text.splitlines()[:8]:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith(">"):
                        capabilities.append(line[:200])
            except Exception:
                pass

        tags = issue_type_map.get(connector, ["通用"])

        tools.append({
            "name": connector,
            "display_name": connector.replace("-", " ").title(),
            "url": url,
            "disabled": disabled,
            "capabilities": capabilities[:3],
            "issue_type_tags": tags,
            "type": "mcp_tool",
            "status": "enabled" if not disabled else "disabled"
        })

    return tools


# ─── 3. 连接器发现 ───

def discover_connectors() -> list[dict]:
    """扫描连接器目录，识别已安装的外部服务连接"""
    connectors = []
    conn_skills_dir = WORKBUDDY_HOME / "connectors" / "skills"
    if not conn_skills_dir.exists():
        return connectors

    for conn_dir in sorted(conn_skills_dir.iterdir()):
        if not conn_dir.is_dir():
            continue
        connectors.append({
            "name": conn_dir.name,
            "path": str(conn_dir),
            "type": "connector"
        })
    return connectors


# ─── 4. 专家团发现（复用 workbuddy-experts/ 索引） ───

def discover_expert_teams() -> list[dict]:
    """从 workbuddy-experts 中读取已索引的专家团"""
    teams = []
    expert_dir = SKILL_DIR / "references" / "workbuddy-experts"
    if not expert_dir.exists():
        return teams

    for plugin_dir in sorted(expert_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        pj = plugin_dir / "plugin.json"
        if not pj.exists():
            continue
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
        except Exception:
            continue
        agents_dir = plugin_dir / "agents"
        agent_count = len(list(agents_dir.glob("*.md"))) if agents_dir.exists() else 0

        teams.append({
            "name": data.get("name", plugin_dir.name),
            "display_zh": data.get("displayName", {}).get("zh", ""),
            "description_zh": data.get("displayDescription", {}).get("zh", ""),
            "category_id": data.get("categoryId", ""),
            "expert_type": data.get("expertType", ""),
            "agent_count": agent_count,
            "lead_name": data.get("members", [{}])[0].get("name", {}).get("zh", "") if data.get("members") else "",
            "type": "expert_team"
        })
    return teams


# ─── 5. 插件发现 ───

def discover_plugins() -> list[dict]:
    """扫描插件市场"""
    plugins = []
    marketplaces = [
        WORKBUDDY_HOME / "plugins" / "marketplaces" / "experts" / "plugins",
    ]
    for mp in marketplaces:
        if not mp.exists():
            continue
        for plugin_dir in sorted(mp.iterdir()):
            if not plugin_dir.is_dir():
                continue
            pj = plugin_dir / "plugin.json"
            if not pj.exists():
                continue
            try:
                data = json.loads(pj.read_text(encoding="utf-8"))
            except Exception:
                continue
            agents_dir = plugin_dir / "agents"
            agent_count = len(list(agents_dir.glob("*.md"))) if agents_dir.exists() else 0
            plugins.append({
                "name": data.get("name", plugin_dir.name),
                "display_name": data.get("displayName", {}).get("zh", ""),
                "category": data.get("categoryId", ""),
                "expert_type": data.get("expertType", ""),
                "agent_count": agent_count,
                "type": "plugin"
            })
    return plugins


# ─── 聚合与匹配 ──────────────────────────────────────────────

def resolve_all() -> dict:
    """全量发现所有资产"""
    return {
        "snapshot_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "skills": discover_skills(),
        "mcp_tools": discover_mcp_tools(),
        "connectors": discover_connectors(),
        "expert_teams": discover_expert_teams(),
        "plugins": discover_plugins(),
    }


def match_by_issue_type(issue_type: str, snapshot: dict = None) -> dict:
    """按议题类型匹配资产"""
    if snapshot is None:
        snapshot = resolve_all()

    issue_lower = issue_type.lower()

    matched = {
        "issue_type": issue_type,
        "matched_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "expert_teams": [],
        "mcp_tools": [],
        "skills": [],
        "plugins": [],
        "summary": ""
    }

    # 专家团匹配（按 category_id）
    for team in snapshot.get("expert_teams", []):
        cat_id = team.get("category_id", "").lower()
        if issue_lower in cat_id or any(word in cat_id for word in issue_lower.replace("-", " ").split()):
            matched["expert_teams"].append({
                "name": team["name"],
                "display_zh": team.get("display_zh", ""),
                "agent_count": team.get("agent_count", 0),
                "match_score": 0.9,
                "usage_hint": f"推荐使用专家团「{team.get('display_zh','')}」({team['name']})"
            })

    # MCP 工具匹配（按 issue_type_tags）
    for tool in snapshot.get("mcp_tools", []):
        if tool.get("disabled", False):
            continue
        tags = [t.lower() for t in tool.get("issue_type_tags", [])]
        if issue_lower in tags or "通用" in tags:
            matched["mcp_tools"].append({
                "name": tool["name"],
                "description": tool.get("capabilities", [None])[0] if tool.get("capabilities") else "",
                "status": tool.get("status", "enabled"),
                "usage_hint": f"已连接 MCP：{tool['name']}"
            })

    # 技能匹配（按 description + triggers）
    # 中文增强：CJK 查询词支持按 2-gram 切分（如"宏观经济"→{"宏观","观经","经济"}），
    # 并将中文词长度门槛放宽到 >=2（"宏观""数据"等 2 字词是关键触发词），
    # 使中文 description 技能能被自然语言议题正确召回。
    def _match_tokens(text: str):
        tokens = set(text.replace("-", " ").replace("_", " ").split())
        ascii_tokens = set()
        cjk_tokens = set()
        for t in tokens:
            hits = set()
            if t:  # 去重
                hits.add(t)
            # CJK 2-gram 切分
            cjk_run = "".join(c if "\u4e00" <= c <= "\u9fff" else " " for c in t)
            for part in cjk_run.split():
                if len(part) >= 2:
                    hits.add(part)
                    # 含中文且总长>=2 时，追加每连续 2 字片段
                    if any("\u4e00" <= c <= "\u9fff" for c in t):
                        for i in range(len(part) - 1):
                            hits.add(part[i:i + 2])
            ascii_tokens |= {t for t in hits if not any("\u4e00" <= c <= "\u9fff" for c in t)}
            cjk_tokens |= {t for t in hits if any("\u4e00" <= c <= "\u9fff" for c in t)}
        # 合并：ASCII 词仍需 >2，中文词 >=2
        ascii_tokens = {t for t in ascii_tokens if len(t) > 2}
        return ascii_tokens | cjk_tokens

    query_hits = _match_tokens(issue_lower)
    for skill in snapshot.get("skills", []):
        desc_lower = skill.get("description", "").lower()
        trigger_text = " ".join(skill.get("triggers", [])).lower()
        combined = desc_lower + " " + trigger_text
        if any(qw in combined for qw in query_hits):
            matched["skills"].append({
                "name": skill["name"],
                "description": skill.get("description", "")[:100],
                "usage_hint": f"可用 skill：{skill['name']}"
            })

    # 生成摘要
    parts = []
    if matched["expert_teams"]:
        parts.append(f"👥 专家团: {', '.join(t['name'] for t in matched['expert_teams'])}")
    if matched["mcp_tools"]:
        parts.append(f"🛠 MCP工具: {', '.join(t['name'] for t in matched['mcp_tools'])}")
    if matched["skills"]:
        parts.append(f"📦 技能: {', '.join(s['name'] for s in matched['skills'][:5])}")
    matched["summary"] = " | ".join(parts) if parts else "（当前无自动匹配资产）"

    return matched


# ─── 快照 ────────────────────────────────────────────────────

def generate_snapshot(snapshot: dict):
    """生成资产快照文件（JSON + Markdown 人类可读）"""
    # JSON 快照
    ASSET_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASSET_SNAPSHOT_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 资产快照已写入: {ASSET_SNAPSHOT_PATH}")

    # Markdown 快照
    md_lines = [
        "# 最后资产快照",
        "",
        f"> 生成时间: {snapshot.get('snapshot_at', '?')}",
        "",
        "---",
        "## 📊 资产总览",
        "",
        f"| 类型 | 数量 |",
        f"|------|------|",
        f"| 专家团 (Expert Teams) | {len(snapshot['expert_teams'])} |",
        f"| MCP 工具 (已连接) | {len([t for t in snapshot['mcp_tools'] if not t.get('disabled')])} |",
        f"| 技能 (Skills) | {len(snapshot['skills'])} |",
        f"| 连接器 (Connectors) | {len(snapshot['connectors'])} |",
        f"| 插件 (Plugins) | {len(snapshot['plugins'])} |",
        "",
        "## MCP 工具（已连接）",
        "",
    ]

    for t in snapshot.get("mcp_tools", []):
        if not t.get("disabled"):
            md_lines.append(f"- **{t['name']}** | {', '.join(t.get('capabilities',['']))}")
            md_lines.append(f"  - 适用议题: {', '.join(t.get('issue_type_tags',[]))}")
            md_lines.append("")

    md_lines.extend([
        "## 技能（按需加载节选）",
        "",
    ])
    for s in snapshot.get("skills", [])[:20]:
        md_lines.append(f"- **{s['name']}**: {s.get('description','')[:120]}")

    md_lines.extend([
        "",
        "## 专家团（按分类）",
        "",
    ])
    for t in snapshot.get("expert_teams", []):
        md_lines.append(f"- **{t.get('display_zh','')}** ({t['name']}) | {t.get('category_id','')} | {t.get('agent_count',0)} agents")

    md_lines.extend([
        "",
        "---",
        "*资产快照在每次 `--snapshot` 时刷新*"
    ])

    ASSET_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASSET_MAP_PATH.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"✅ 人类可读快照已写入: {ASSET_MAP_PATH}")


# ─── 类型列表 ────────────────────────────────────────────────

def list_types(snapshot: dict = None):
    """列出所有已发现的资产分类"""
    if snapshot is None:
        snapshot = resolve_all()

    categories = {}

    # 从专家团提取分类
    for t in snapshot.get("expert_teams", []):
        cat = t.get("category_id", "Uncategorized")
        categories.setdefault(cat, {"teams": 0, "agents": 0})
        categories[cat]["teams"] += 1
        categories[cat]["agents"] += t.get("agent_count", 0)

    # MCP 工具标签
    mcp_tags = set()
    for t in snapshot.get("mcp_tools", []):
        for tag in t.get("issue_type_tags", []):
            mcp_tags.add(tag)

    print("📂 资产分类清单")
    print("━━━━━━━━━━━━━━━━━━━")
    print("  【专家团分类】")
    for cat, info in sorted(categories.items()):
        print(f"    {cat}: {info['teams']} 团 / {info['agents']} agents")
    print("  【MCP 标签】")
    for tag in sorted(mcp_tags):
        print(f"    {tag}")
    print("  【技能总数】")
    print(f"    {len(snapshot.get('skills', []))} 个已安装技能")
    print("━━━━━━━━━━━━━━━━━━━")

    return categories


# ─── CLI ─────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="WorkBuddy 资产解析器")
    ap.add_argument("--snapshot", action="store_true", help="全量扫描并生成资产快照")
    ap.add_argument("--match", default="", help="按议题类型匹配资产（如 08-FinanceInvestment）")
    ap.add_argument("--docket", default="", help="从案卷 JSON 中提取议题类型")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--list-types", action="store_true", help="列出所有资产分类")
    args = ap.parse_args()

    if args.snapshot:
        snapshot = resolve_all()
        generate_snapshot(snapshot)
        # 顺便更新类型列表
        list_types(snapshot)

    elif args.match:
        result = match_by_issue_type(args.match)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"📋 议题类型: {args.match}")
            print(f"  摘要: {result['summary']}")
            print(f"  匹配专家团: {len(result['expert_teams'])} 个")
            for t in result['expert_teams']:
                print(f"    - {t['display_zh']} ({t['name']})")
            print(f"  匹配 MCP: {len(result['mcp_tools'])} 个")
            for t in result['mcp_tools']:
                print(f"    - {t['name']}: {t['usage_hint']}")
            print(f"  匹配技能: {len(result['skills'])} 个")
            for s in result['skills'][:5]:
                print(f"    - {s['name']}")

    elif args.docket:
        try:
            docket = json.loads(Path(args.docket).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ 读取案卷失败: {e}", file=sys.stderr)
            sys.exit(1)
        issue_type = docket.get("issue_type", "")
        if not issue_type:
            # 尝试从议题描述提取
            print("⚠️ 案卷中无 issue_type，尝试从描述推断...", file=sys.stderr)
            issue_type = "Unclassified"
        result = match_by_issue_type(issue_type)
        # 写回案卷
        docket["assets_resolved"] = {
            "expert_teams": result["expert_teams"],
            "mcp_tools": result["mcp_tools"],
            "skills": result["skills"][:5],
            "connectors": [],
        }
        Path(args.docket).write_text(
            json.dumps(docket, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 案卷已更新资产信息: {args.docket}")
        print(f"   {result['summary']}")

    elif args.list_types:
        list_types(resolve_all())

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
