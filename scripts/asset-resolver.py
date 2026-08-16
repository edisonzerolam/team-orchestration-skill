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
import re
import sys
import argparse
import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
WORKBUDDY_HOME = Path.home() / ".workbuddy"

ASSET_SNAPSHOT_PATH = SKILL_DIR / "references" / "last-asset-snapshot.json"
ASSET_MAP_PATH = SKILL_DIR / "references" / "asset-issue-map.md"
# 多机技能注册表（TC-20260816-7 · 跨机器技能发现）：远程主机经 skill-registry-agent 枚举后合并于此
REGISTRY_PATH = SKILL_DIR / "references" / "skill-registry.json"
REGISTRY_FRESH_DAYS = 7  # 远程清单保鲜期：超过则立案时提示/自动刷新

# ─── 发现引擎 ────────────────────────────────────────────────

# ─── 1. 技能发现 ───

# 技能根：多客户端动态收集（TC-20260816-7 · 换机即用）——
# 本技能安装到任意桌面 agent/harness/AI 客户端后，asset-resolver 扫"当前机器"的
# 全部客户端技能根（按存在性收集），使路由注入本机实际已装技能。
HOME_SKILL_ROOTS = [
    (Path.home() / ".agents" / "skills", "agents"),
    (Path.home() / ".dsh" / "skills", "dsh"),
    (Path.home() / ".workbuddy" / "skills", "workbuddy"),
    (Path.home() / ".claude" / "skills", "claude"),
    (Path.home() / ".codex" / "skills", "codex"),
]
# 对齐 DSH 注入面：跳过测试夹具/构建产物/嵌套仓库元数据
SKIP_PATH_PARTS = {"tests", "fixtures", "dist", "__pycache__", "node_modules", ".git"}


def discover_skill_roots(project_dir: str = "") -> list:
    """收集当前机器存在的技能根（home 级 + 可选项目级 .dsh/skills、.agents/skills）。"""
    roots = [(r, s) for r, s in HOME_SKILL_ROOTS if r.exists()]
    if project_dir:
        pd = Path(project_dir).expanduser()
        for sub, src in ((".dsh", "dsh"), (".agents", "agents")):
            r = pd / sub / "skills"
            if r.exists() and (r, src) not in roots:
                roots.append((r, src))
    return roots


def _is_skip_dir(name: str) -> bool:
    """跳过隐藏目录、备份/临时目录、测试/构建目录"""
    name_lower = name.lower()
    if name.startswith("."):
        return True
    if name_lower in SKIP_PATH_PARTS:
        return True
    return (".backup" in name_lower or name_lower.startswith("backup-")
            or name_lower.endswith(".bak") or name_lower.endswith(".tmp")
            or name_lower.endswith("~") or ".old" in name_lower)


def _parse_skill_frontmatter(skill_md: Path) -> dict:
    """解析 SKILL.md frontmatter：name/description/triggers/disabled。

    - 编码：UTF-8 优先，GB18030 兼容（历史 GBK 文件），杜绝 U+FFFD 乱码注入
    - 门禁对齐 DSH：`disable-model-invocation: true` 视为 disabled（TC-20260816-2 实证）
    - 触发词：frontmatter `triggers:`/「当…」行 + description 内「触发词：/触发方式：」段
      （TC-20260816-2 精修约定：中文触发词写入 description）
    """
    info = {"name": "", "description": "", "triggers": [], "disabled": False}
    try:
        raw_bytes = skill_md.read_bytes()
        text = None
        for enc in ("utf-8", "gb18030"):
            try:
                text = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = raw_bytes.decode("utf-8", errors="replace")
        lines = text.splitlines()
        in_fm = False
        fm_dashes = 0
        for idx, line in enumerate(lines[:80]):
            stripped = line.strip()
            if stripped == "---":
                fm_dashes += 1
                in_fm = fm_dashes % 2 == 1
                if fm_dashes >= 2 and not in_fm:
                    break
                continue
            if not in_fm:
                continue
            key, _, val = line.partition(":")
            key_l = key.strip().lower()
            val_l = val.strip().lower()
            if key_l in ("disabled", "disable-model-invocation"):
                if val_l in ("true", "yes", "1"):
                    info["disabled"] = True
                    break
            elif key_l == "name":
                info["name"] = val.strip().strip("\"'")
            elif key_l == "description":
                raw_val = val.strip()
                if raw_val in ("|", ">"):
                    # YAML 块标量（wewrite/story-studio 等多行 description）：收集后续缩进行
                    block = []
                    for j in range(idx + 1, len(lines)):
                        nxt = lines[j]
                        if nxt.strip() == "":
                            block.append("")
                            continue
                        if nxt.startswith(" ") or nxt.startswith("\t"):
                            block.append(nxt.strip())
                        else:
                            break
                    raw_val = " ".join(x for x in block if x).strip()
                info["description"] = raw_val
                # 提取 description 内「触发词：」段（TC-20260816-2 精修约定；wewrite 用「触发关键词：」）
                for marker in ("触发词：", "触发词:", "触发方式：", "触发方式:", "触发关键词：", "触发关键词:"):
                    idx_m = info["description"].find(marker)
                    if idx_m >= 0:
                        seg = info["description"][idx_m + len(marker):].split("。")[0]
                        for tok in re.split(r"[、，,;；/|]", seg):
                            tok = tok.strip().strip("\"' ")
                            if tok and tok not in info["triggers"]:
                                info["triggers"].append(tok)
                        break
            elif line.lower().startswith("triggers:") or line.lower().startswith("当"):
                info["triggers"].append(line.strip())
    except Exception:
        pass
    return info


def discover_skills_from(root: Path, source: str, max_depth: int = 4) -> list[dict]:
    """递归扫描技能根下的 SKILL.md（对齐 DSH 注入面：顶层 + 技能族嵌套，跳过 tests/fixtures 等）"""
    skills = []
    if not root.exists():
        return skills
    stack = [(root, 0)]
    while stack:
        cur, depth = stack.pop()
        if depth >= max_depth:
            continue
        try:
            entries = sorted(cur.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if _is_skip_dir(entry.name):
                    continue
                stack.append((entry, depth + 1))
                continue
            if entry.name.lower() != "skill.md":
                continue
            info = _parse_skill_frontmatter(entry)
            if info["disabled"]:
                continue
            skills.append({
                "name": info["name"] or entry.parent.name,
                "description": info["description"],  # 完整描述（匹配用；快照体积可控，显示侧自行截断）
                "triggers": info["triggers"][:5],
                "path": str(entry.parent),
                "type": "skill",
                "source": source,
            })
    skills.sort(key=lambda s: s["name"])
    return skills


def discover_skills(project_dir: str = "") -> list[dict]:
    """多根聚合：当前机器全部客户端技能根（DSH/WorkBuddy/Claude Code/Codex + 可选项目级）。

    同名冲突时 agents 优先（DSH 注入面优先）；返回按 name 字典序。
    """
    skills = []
    for root, source in discover_skill_roots(project_dir):
        skills.extend(discover_skills_from(root, source))
    seen = {}
    for s in skills:
        key = s["name"]
        if key not in seen or s["source"] == "agents":
            seen[key] = s
    return list(seen.values())


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

def resolve_all(project_dir: str = "") -> dict:
    """全量发现所有资产（含多机注册表远程技能）"""
    return {
        "snapshot_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "skills": discover_skills(project_dir),
        "remote_skills": load_registry().get("remote_skills", []),
        "mcp_tools": discover_mcp_tools(),
        "connectors": discover_connectors(),
        "expert_teams": discover_expert_teams(),
        "plugins": discover_plugins(),
    }


def match_by_issue_type(issue_type: str, snapshot: dict = None, project_dir: str = "") -> dict:
    """按议题类型匹配资产"""
    if snapshot is None:
        snapshot = resolve_all(project_dir)

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
    # TC-20260816-8 修复：纯 ASCII ≤2 字符（如 --match AI）token 化后为空集 → 零召回；
    # 退化为原始查询子串匹配（"ai" 直接匹配含 "ai" 的技能）
    if not query_hits and issue_lower.strip():
        query_hits = {issue_lower.strip()}
    all_skills = list(snapshot.get("skills", []))
    # 并入多机注册表远程技能（source=remote:<host>，标注主机）
    all_skills += snapshot.get("remote_skills", [])
    scored = []
    for skill in all_skills:
        desc_lower = skill.get("description", "").lower()
        trigger_text = " ".join(skill.get("triggers", [])).lower()
        # 3+ 字中文触发词展开 2-gram（"公众号"→"公众,众号"），对齐 query 侧 2-gram 切分，防 3 字触发词失配
        trig_ngrams = set()
        for tg in skill.get("triggers", []):
            cjk = "".join(c if "\u4e00" <= c <= "\u9fff" else " " for c in tg)
            for part in cjk.split():
                if len(part) >= 3:
                    for i in range(len(part) - 1):
                        trig_ngrams.add(part[i:i + 2])
        combined = desc_lower + " " + trigger_text + " " + " ".join(sorted(trig_ngrams))
        if not any(qw in combined for qw in query_hits):
            continue
        # 相关性计分：触发词精确命中 > 触发词 2-gram > 描述命中（防 name 字典序把噪声排前）
        trigs = [t.lower() for t in skill.get("triggers", [])]
        score = 0
        for qw in query_hits:
            if any(qw == tg or (len(qw) >= 2 and qw in tg) for tg in trigs):
                score += 3
            elif qw in trig_ngrams:
                score += 2
            elif qw in desc_lower:
                score += 1
        scored.append((score, skill))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    for score, skill in scored:
        trig = "、".join(skill.get("triggers", [])[:3])
        host = skill.get("host", "")
        host_note = "（在 %s 机，经 SSH 执行）" % host if host else ""
        matched["skills"].append({
            "name": skill["name"],
            "description": skill.get("description", "")[:100],
            "source": skill.get("source", ""),
            "match_score": score,
            "usage_hint": f"可用 skill：{skill['name']}" + (f"（触发词：{trig}）" if trig else "") + host_note
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


# ─── 多机技能注册表（TC-20260816-7）────────────────────────

def load_registry() -> dict:
    """读多机技能注册表；不存在返回空结构。"""
    empty = {"registry_version": 1, "updated_at": "", "hosts": {}, "remote_skills": []}
    if not REGISTRY_PATH.exists():
        return empty
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        data.setdefault("hosts", {})
        data.setdefault("remote_skills", [])
        return data
    except Exception:
        return empty


def _sanitize_remote_skill(s, host_alias: str):
    """远程技能条目结构校验 + 清洗（TC-20260816-8 · 防提示注入）。

    被攻陷主机的技能清单若原样拼入子代理 prompt 即成提示注入通道；
    白名单校验：name 合法（宽松 kebab/dot/underscore）、字段长度上限、去控制字符、条数上限。
    非法条目丢弃并计数。
    """
    if not isinstance(s, dict):
        return None
    name = str(s.get("name", "")).strip()
    if not name or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
        return None
    def _clean(x: str) -> str:
        return "".join(c for c in x if c >= " " or c == "\n")
    desc = _clean(str(s.get("description", "")))[:300]
    trigs = [_clean(str(t))[:40] for t in (s.get("triggers") or []) if isinstance(t, str)][:5]
    return {
        "name": name,
        "description": desc,
        "triggers": trigs,
        "source": "remote:%s" % host_alias,
        "host": host_alias,
        "path": str(s.get("path", ""))[:200],
    }


def merge_registry(payload: dict, host_alias: str) -> dict:
    """合并一份远程枚举清单（skill-registry-agent 输出）进注册表。

    - host_alias：主控侧为主机起的别名（如 dev-01 / home-pc）
    - 同名同源技能按 host 保留（不同机器可有同名技能，路由时按 host 区分）
    - 条目经 _sanitize_remote_skill 校验清洗（结构白名单 + 长度上限 + 去控制字符）
    """
    registry = load_registry()
    skills = payload.get("skills", [])
    if not isinstance(skills, list):
        skills = []
    clean_skills, dropped = [], 0
    for s in skills[:2000]:  # 条数上限防膨胀
        c = _sanitize_remote_skill(s, host_alias)
        if c is not None:
            clean_skills.append(c)
        else:
            dropped += 1
    registry["remote_skills"] = [s for s in registry.get("remote_skills", [])
                                 if s.get("host") != host_alias] + clean_skills
    registry["hosts"][host_alias] = {
        "host": str(payload.get("host", host_alias))[:64],
        "last_sync": str(payload.get("generated_at", ""))[:32],
        "count": len(clean_skills),
        "dropped": dropped,
    }
    registry["updated_at"] = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return registry


def check_registry() -> list:
    """检查各远程主机清单保鲜状态：返回过期主机列表（>REGISTRY_FRESH_DAYS 或从未同步）。"""
    registry = load_registry()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    stale = []
    for alias, info in registry.get("hosts", {}).items():
        last = info.get("last_sync", "")
        days = None
        if last:
            try:
                ts = datetime.datetime.fromisoformat(last)
                days = (now - ts).days
            except ValueError:
                pass
        if days is None or days > REGISTRY_FRESH_DAYS:
            stale.append({
                "alias": alias,
                "host": info.get("host", ""),
                "last_sync": last,
                "age_days": days,
                "count": info.get("count", 0),
            })
    return stale


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

def _print_match(result: dict, label: str):
    """打印匹配结果（--match / --task 共用）"""
    print(f"📋 {label}: {result['issue_type']}")
    print(f"  摘要: {result['summary']}")
    print(f"  匹配专家团: {len(result['expert_teams'])} 个")
    for t in result['expert_teams']:
        print(f"    - {t['display_zh']} ({t['name']})")
    print(f"  匹配 MCP: {len(result['mcp_tools'])} 个")
    for t in result['mcp_tools']:
        print(f"    - {t['name']}: {t['usage_hint']}")
    print(f"  匹配技能: {len(result['skills'])} 个")
    for s in result['skills'][:8]:
        print(f"    - {s['name']} [{s.get('source','')}] {s['usage_hint']}")


def main():
    ap = argparse.ArgumentParser(description="WorkBuddy/DSH 资产解析器（TC-20260816-7 双根版）")
    ap.add_argument("--snapshot", action="store_true", help="全量扫描并生成资产快照")
    ap.add_argument("--match", default="", help="按议题类型匹配资产（如 08-FinanceInvestment）")
    ap.add_argument("--task", default="", help="按自然语言任务匹配资产（如 '做一次竞品分析'）")
    ap.add_argument("--docket", default="", help="从案卷 JSON 中提取议题类型")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--list-types", action="store_true", help="列出所有资产分类")
    ap.add_argument("--registry-merge", default="", metavar="JSON", help="合并远程技能清单（skill-registry-agent 输出）进注册表，如 --registry-merge ./remote-skills.json --host-alias dev-01")
    ap.add_argument("--host-alias", default="", help="--registry-merge 时的主机别名")
    ap.add_argument("--registry-check", action="store_true", help="检查远程技能清单保鲜状态（过期提示刷新）")
    ap.add_argument("--registry-list", action="store_true", help="列出注册表中的远程技能")
    ap.add_argument("--project-dir", default="", help="项目/工作区目录：附加扫描 <dir>/.dsh/skills、<dir>/.agents/skills（换机场景项目级技能）")
    args = ap.parse_args()

    if args.snapshot:
        snapshot = resolve_all(args.project_dir)
        generate_snapshot(snapshot)
        # 顺便更新类型列表
        list_types(snapshot)

    elif args.match:
        result = match_by_issue_type(args.match, project_dir=args.project_dir)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_match(result, "议题类型")

    elif args.task:
        result = match_by_issue_type(args.task, project_dir=args.project_dir)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _print_match(result, "任务")

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

    elif args.registry_merge:
        if not args.host_alias:
            print("❌ 需要 --host-alias 指定主机别名", file=sys.stderr)
            sys.exit(1)
        try:
            payload = json.loads(Path(args.registry_merge).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ 读取远程清单失败: {e}", file=sys.stderr)
            sys.exit(1)
        reg = merge_registry(payload, args.host_alias)
        info = reg["hosts"][args.host_alias]
        print(f"✅ 已合并主机 [{args.host_alias}]（{info.get('host','')}）：{info['count']} 个远程技能")
        print(f"   注册表共 {len(reg['remote_skills'])} 个远程技能 / {len(reg['hosts'])} 台主机")

    elif args.registry_check:
        stale = check_registry()
        if not stale:
            print("✅ 全部远程技能清单在保鲜期内（≤%d 天）" % REGISTRY_FRESH_DAYS)
        else:
            print("⚠️ 以下主机技能清单过期（保鲜期 %d 天）：" % REGISTRY_FRESH_DAYS)
            for s in stale:
                age = "%d 天" % s["age_days"] if s["age_days"] is not None else "未知"
                print(f"  - [{s['alias']}] {s['host']} | 上次同步 {s['last_sync'] or '从未'} | {age} | {s['count']} 技能")
            print("  → 刷新：ssh_exec 在目标机跑 skill-registry-agent.py，取回 JSON 后 --registry-merge")

    elif args.registry_list:
        reg = load_registry()
        if not reg["remote_skills"]:
            print("（注册表为空——先 --registry-merge 合并远程清单）")
        else:
            print(f"远程技能注册表：{len(reg['remote_skills'])} 技能 / {len(reg['hosts'])} 主机")
            for s in sorted(reg["remote_skills"], key=lambda x: (x.get("host",""), x["name"])):
                trig = "、".join(s.get("triggers", [])[:2])
                print(f"  - [{s.get('host','')}] {s['name']}" + (f"（触发词：{trig}）" if trig else ""))

    elif args.list_types:
        list_types(resolve_all())

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
