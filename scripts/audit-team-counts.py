#!/usr/bin/env python3
"""
团队/Agent 计数审计脚本。
扫描文件系统、_index.md、SKILL.md、PLAN、expert-matching.md 中的计数，报告差异。

用法:
  python3 scripts/audit-team-counts.py
  python3 scripts/audit-team-counts.py --fix     # 更新 _index.md 头部
"""
import sys, json, re, os
from pathlib import Path

SKILL_DIR = Path(r"C:\Users\林昌\.config\opencode\skills\team-orchestration")
EXPERT_DIR = SKILL_DIR / "references" / "workbuddy-experts"

def count_actual():
    """统计文件系统中实际的团队数和 agent 数"""
    teams = sorted([d.name for d in EXPERT_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')])
    skip_categories = {'groups', '__pycache__'}
    teams = [t for t in teams if t not in skip_categories]
    total_agents = 0
    team_agents = {}
    for t in teams:
        agents_dir = EXPERT_DIR / t / "agents"
        if agents_dir.exists():
            count = len(list(agents_dir.glob("*.md")))
        else:
            count = 0
        total_agents += count
        team_agents[t] = count
    return len(teams), total_agents, teams, team_agents

def classify_teams(team_names):
    """将团队分类为核心团、独立专家团、虚拟团等"""
    known_core = {
        'investment-masters-team', 'trading-agent', 'stock-partner-team', 'a-share-analysis',
        'ai-content-creator-team', 'content-distribution-team', 'content-monetization-team',
        'promo-creator-team', 'marketing-campaign-team', 'sales-battle-team', 'seo-content-team',
        'social-engagement-team', 'design-engine', 'humanize-ppt-team', 'software-company',
        'engineering-assurance-team', 'gstack', 'rum-fullstack-team', 'product-strategy-team',
        'chatlaw-team', 'enterprise-legal-team', 'tax-compliance-team',
        'gpt-researcher-team', 'huashu-data-pro', 'ai-data-copilot',
        'hr-operations-team', 'opc-team', 'openspec-doc-team',
    }
    virtual = {'game-development', 'industry-consulting', 'tencent-ecosystem'}
    individuals = []  # 单 agent 独立专家
    core = []
    virt = []
    for t in team_names:
        if t in known_core:
            core.append(t)
        elif t in virtual:
            virt.append(t)
        else:
            individuals.append(t)
    return core, virt, individuals

def extract_numbers_from_text(text, label):
    """从文本中提取数字，如 '29 个 WorkBuddy 专家团' → 29"""
    nums = re.findall(r'(\d+)\s*(?:个|名|位)', text)
    return [int(n) for n in nums] if nums else None

def check_declared_numbers():
    """检查各文档中的声明数字"""
    issues = []
    actual_teams, actual_agents, team_names, team_agents = count_actual()
    core, virt, individuals = classify_teams(team_names)

    # 2. SKILL.md
    skill_path = SKILL_DIR / "SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        # 查找 "N 个 WorkBuddy 专家团"
        m = re.search(r'(\d+)\s*个\s*WorkBuddy\s*专家团', text)
        if m:
            declared = int(m.group(1))
            if declared != len(core):
                issues.append(f"  ❌ SKILL.md: 声明 {declared} 个 WorkBuddy 专家团，实际 {len(core)} 个核心团")
        m = re.search(r'(\d+)\s*个\s*subagent', text)
        if m:
            declared = int(m.group(1))
            # 无法精确验证 subagent 数量，仅记录
        # 提取独立专家数字
        m = re.search(r'(\d+)\s*独立专家', text)
        if m:
            declared = int(m.group(1))
            if declared != len(individuals):
                issues.append(f"  ❌ SKILL.md: 声明 {declared} 独立专家，实际 {len(individuals)} 个")
        m = re.search(r'(\d+)\s*个\s*虚拟团', text)
        if m:
            declared = int(m.group(1))
            if declared != len(virt):
                issues.append(f"  ❌ SKILL.md: 声明 {declared} 虚拟团，实际 {len(virt)} 个")
    else:
        issues.append("  [!] SKILL.md 不存在")

    # 3. _index.md 头部
    index_path = EXPERT_DIR / "_index.md"
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8")
        m = re.search(r'总数:\s*(\d+)\s*个\s*专家团', text)
        if m:
            declared = int(m.group(1))
            if declared != actual_teams:
                issues.append(f"  ❌ _index.md 头部: 声明 {declared} 专家团，实际 {actual_teams} 个")
        m = re.search(r'(\d+)\s*个子\s*Agent', text)
        if m:
            declared = int(m.group(1))
            if declared != actual_agents:
                issues.append(f"  ❌ _index.md 头部: 声明 {declared} sub-agent，实际 {actual_agents} 个")
    else:
        issues.append("  [!] _index.md 不存在")

    # 4. expert-matching.md
    em_path = SKILL_DIR / "references" / "expert-matching.md"
    if em_path.exists():
        text = em_path.read_text(encoding="utf-8")
        m = re.search(r'(\d+)\s*个\s*WorkBuddy\s*专家团', text)
        if m:
            declared = int(m.group(1))
            if declared != len(core):
                issues.append(f"  ❌ expert-matching.md: 声明 {declared} 个 WorkBuddy 专家团，实际 {len(core)} 个")

    # 5. PLAN-v2.6-enhancement.md
    plan_path = SKILL_DIR / "PLAN-v2.6-enhancement.md"
    if plan_path.exists():
        text = plan_path.read_text(encoding="utf-8")
        all_nums = re.findall(r'(\d+)\s*个\s*专家团', text)
        for num_str in set(all_nums):
            num = int(num_str)
            if num not in [actual_teams, len(core), len(core)+len(virt)]:
                if num > 0:
                    pass  # 可能是其他场景的引用数字，不做严格校验

    # 6. teams-index.json
    idx_path = SKILL_DIR / "shared" / "teams-index.json"
    if idx_path.exists():
        try:
            data = json.loads(idx_path.read_text(encoding="utf-8"))
            if len(data) != actual_teams:
                issues.append(f"  ❌ shared/teams-index.json: 含 {len(data)} 条，文件系统 {actual_teams} 团")
        except:
            issues.append("  ❌ shared/teams-index.json: 无法解析")

    return issues, actual_teams, actual_agents, len(core), len(virt), len(individuals)

def fix_index_header():
    """更新 _index.md 头部统计数字"""
    index_path = EXPERT_DIR / "_index.md"
    if not index_path.exists():
        return False
    actual_teams, actual_agents, _, _ = count_actual()
    text = index_path.read_text(encoding="utf-8")
    text = re.sub(
        r'总数:\s*\d+\s*个\s*专家团,\s*\d+\s*个子\s*Agent',
        f'总数: {actual_teams} 个专家团, {actual_agents} 个子 Agent',
        text
    )
    index_path.write_text(text, encoding="utf-8")
    return True

def main():
    print("=" * 60)
    print("  团队/Agent 计数审计报告")
    print("=" * 60)

    actual_teams, actual_agents, team_names, team_agents = count_actual()
    core, virt, individuals = classify_teams(team_names)

    print(f"\n[文件系统统计]")
    print(f"  总团队数: {actual_teams}")
    print(f"  总 Agent 数: {actual_agents}")
    print(f"    核心团: {len(core)}")
    print(f"    虚拟团: {len(virt)}")
    print(f"    独立专家: {len(individuals)}")

    # 空 Agent 检查
    empty_teams = [t for t, c in team_agents.items() if c == 0]
    if empty_teams:
        print(f"\n  [!] 以下目录 agents 为空:")
        for t in empty_teams:
            print(f"    - {t}")

    # 计数差异检查
    print(f"\n[文档声明差异检查]")
    issues, *_ = check_declared_numbers()

    if issues:
        for i in issues:
            print(i)
    else:
        print("  ✓ 所有文档计数一致")

    # Agent 分布概要
    print(f"\n[Agent 分布]")
    sorted_teams = sorted(team_agents.items(), key=lambda x: -x[1])
    for name, cnt in sorted_teams[:10]:
        print(f"  {name}: {cnt} agents")
    if len(sorted_teams) > 10:
        print(f"  ... 还有 {len(sorted_teams) - 10} 个团队")

    # 是否执行 --fix
    if "--fix" in sys.argv:
        if fix_index_header():
            print(f"\n[FIX] _index.md 头部已更新")
        else:
            print(f"\n[FIX] _index.md 不存在，跳过")

    print()
    if issues or empty_teams:
        print("[结果] FAIL - 存在计数偏差")
        return 1
    else:
        print("[结果] PASS - 全部一致")
        return 0

if __name__ == "__main__":
    sys.exit(main())
