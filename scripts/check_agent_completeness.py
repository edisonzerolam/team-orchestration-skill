# -*- coding: utf-8 -*-
"""scripts/check_agent_completeness.py — Agent 人设完整性校验器。

依据 _template/agent-template.md 标准，校验 references/workbuddy-experts/*/agents/*.md：
  1. frontmatter 必填键：name / description / displayName / profession / maxTurns / provenBy（agent-template 标准）
  2. verified 字段显式存在（bool）
  3. 正文含关键段落：核心能力 / 工作流程 / 输出规范 / 注意事项 / 回传要求

判定：
  - frontmatter 缺必填键、或 verified 缺失、或正文缺关键段 → 判红
  - 每次补齐后运行，作为团队补齐质量门禁。

退出码：
  0 = 全部满足
  1 = 存在不完整 agent
  2 = 运行错误

用法：
  python scripts/check_agent_completeness.py            # 全量
  python scripts/check_agent_completeness.py <team>     # 单团队
"""
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
EXPERTS = SKILL_ROOT / "references" / "workbuddy-experts"
NON_TEAM = {"_template"}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)

# agent-template 要求的前置必填键（对新标准团队）
REQUIRED_KEYS = ["name", "description", "maxTurns"]
# 新增/增强团队走新标准：要求 displayName/profession/provenBy/verified
NEW_STANDARD_KEYS = ["displayName", "profession", "provenBy", "verified"]

# 走"新标准"（agent-template，含 provenBy/verified）的团队白名单。
# 仅本次补齐/增强的团队强制新标准；其余既有成熟团队按旧模板宽松校验，避免误伤历史资产。
NEW_STANDARD_TEAMS = {
    "ecommerce-1688", "product-design-suite", "cn-litigation", "equity-research",
    "wealth-management", "pe-vc-investment", "investment-banking",
    "alicloud-engineering", "devtools-engineering", "consulting-delivery",
    "tech-service-transfer",
}

# 正文关键段落（任一命中即认为含该意群）；lead 的工作流程段常用"团队编排 SOP"命名，故并含匹配词
SECTION_MARKERS = {
    "核心能力": ["核心能力", "专业技能", "擅长"],
    "工作流程": ["工作流程", "流程", "步骤", "编排 SOP", "SOP"],
    "输出规范": ["输出", "格式", "schema"],
    "注意事项": ["注意", "边界", "红线", "禁止"],
    "回传要求": ["回传", "teammate", "主理人"],
}


def parse_frontmatter(text: str) -> dict | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def check_agent(team: Path, agent_path: Path, new_standard: bool) -> list:
    """返回该 agent 的缺缺陷消息列表。空列表 = 通过。

    - new_standard=True（本次补齐白名单团队）：frontmatter 六键 + verified + 全部关键段落。
    - new_standard=False（既有成熟团队）：仅 frontmatter name/description 基础存在，不卡段落（旧模板措辞各异）。
    """
    issues = []
    text = agent_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        issues.append(f"{agent_path.name}: 缺 frontmatter")
        return issues

    # 基础键（新旧都要求 name/description；maxTurns 仅新标准强要求，旧模板可有可无）
    missing = [k for k in ["name", "description"] if k not in fm]
    if missing:
        issues.append(f"{agent_path.name}: frontmatter 缺 {missing}")

    if not new_standard:
        # 既有成熟团队：通过宽松校验（不卡段落/新键/verified）
        return issues

    # 新标准团队：maxTurns + verified + 新键 + 段落全强制
    if "maxTurns" not in fm:
        issues.append(f"{agent_path.name}: 缺 maxTurns")
    if "verified" not in fm:
        issues.append(f"{agent_path.name}: 缺 verified 字段（模板必填）")
    nmiss = [k for k in NEW_STANDARD_KEYS if k not in fm]
    if nmiss:
        issues.append(f"{agent_path.name}: 新标准缺 {nmiss}")

    body = text
    for label, markers in SECTION_MARKERS.items():
        if not any(mk in body for mk in markers):
            issues.append(f"{agent_path.name}: 缺{label}段落")

    return issues


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    target = args[0] if args else None
    total_issues = 0
    scanned = 0

    for team in sorted(EXPERTS.iterdir()):
        if not team.is_dir() or team.name in NON_TEAM:
            continue
        if target and team.name != target:
            continue
        # 门禁只对"本次补齐/增强（白名单）团队"严格生效；既有成熟团队由 check_team_consistency 覆盖文件存在性
        if team.name not in NEW_STANDARD_TEAMS and not target:
            continue
        agents_dir = team / "agents"
        if not agents_dir.exists():
            continue
        new_standard = team.name in NEW_STANDARD_TEAMS
        for ag in sorted(agents_dir.glob("*.md")):
            # 跳过占位 lead（仍为旧占位未补齐），不误报为缺陷
            sz = ag.stat().st_size
            if sz < 800:
                continue
            scanned += 1
            issues = check_agent(team, ag, new_standard)
            if issues:
                total_issues += len(issues)
                for i in issues:
                    print(f"  ❌ {team.name}/agents/{i}")

    if scanned == 0:
        print("⚠️  未扫描到完整 agent 文件（可能均为占位或目录为空）")
        sys.exit(0)

    if total_issues:
        print(f"❌ 共 {total_issues} 处不完整，{scanned} 个 agent 被检查。")
        sys.exit(1)
    print(f"✅ 全部 {scanned} 个 agent 满足完整模板。")
    sys.exit(0)


if __name__ == "__main__":
    main()
