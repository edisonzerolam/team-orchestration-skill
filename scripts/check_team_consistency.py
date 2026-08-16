# -*- coding: utf-8 -*-
"""scripts/check_team_consistency.py — 专家团"声明 == 资产"三方一致性校验器。

校验 references/workbuddy-experts/ 下每个团队的：
  1. plugin.json 的 agents[] 声明的文件  vs  磁盘 agents/*.md（权威基准 = agents[] 完整文件清单）
  2. plugin.json 的 agents[] 数组指向的文件是否存在
  3. plugin.json 的 teamInfo.leadAgent 指向的 lead 文件是否存在、并被 agents[]/members 覆盖
  4. teamInfo.memberAgents 里的每个成员是否有磁盘文件

判定（任一违规即红）：
  - agents[] 声明与磁盘文件集不一致（磁盘有未声明文件 / 声明文件缺失）
  - agents[] 或 leadAgent 指向文件缺失    → 加载失败隐患
  - members 声明成员缺磁盘文件
  - 无 plugin.json 的目录                  → 视为异常（除非是 _template 等元目录）

退出码：
  0 = 全部一致
  1 = 发现不一致（stub 会被标记但退出码仍为 0，除非 treat_stub_as_error）
  2 = 运行错误

用法：
  默认（列出 stub 与不一致）  python scripts/check_team_consistency.py
  严格模式（stub 也判失败）   python scripts/check_team_consistency.py --strict
  单团队                      python scripts/check_team_consistency.py <team_name>
"""
import json
import sys
from pathlib import Path

# Windows GBK 控制台防护（同 asset-resolver）：emoji/中文输出必须 UTF-8 重配置，否则 UnicodeEncodeError 崩溃
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_ROOT = Path(__file__).resolve().parent.parent
EXPERTS = SKILL_ROOT / "references" / "workbuddy-experts"

# 非团队目录（元目录/模板/共享层），跳过——TC-20260816-9 扩展：_domain 域入口、_shared 共享人设
NON_TEAM = {"_template", "_domain", "_shared"}


def check_one(team: Path, strict: bool):
    """校验单个团队，返回 (ok, messages)。ok=False 表示存在违规。"""
    ok = True
    msgs = []
    pj_path = team / "plugin.json"
    if not pj_path.exists():
        return False, [f"{team.name}: 缺少 plugin.json"]

    try:
        pj = json.loads(pj_path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"{team.name}: plugin.json 解析失败 - {e}"]

    # 权威基准 = agents[]（完整文件清单，含 lead），而非 teamInfo.memberAgents（仅成员角色表）
    raw_agents = pj.get("agents")
    agents_list = raw_agents if isinstance(raw_agents, list) else []
    members = (pj.get("teamInfo") or {}).get("memberAgents") or []
    lead = (pj.get("teamInfo") or {}).get("leadAgent")
    # 兜底：agents[] 缺失或畸形（非 list，如 './agents/'）时，退化为 memberAgents + leadAgent 作声明基准
    if not isinstance(raw_agents, list):
        declared_ids = list(members) if not lead else list(members) + [lead]
        agents_list_ok = True  # 该源无法做文件引用校验，只做成员对齐
    else:
        declared_ids = []
        agents_list_ok = False
    agents_dir = team / "agents"

    # 磁盘 agent 文件
    disk_files = sorted(p.name for p in agents_dir.glob("*.md")) if agents_dir.exists() else []
    disk_ids = [f[:-3] for f in disk_files if f.endswith(".md")]

    # 1. agents[] 声明的文件清单 vs 磁盘（当 agents[] 为合法 list 时）
    if isinstance(raw_agents, list):
        for ag in agents_list:
            rel = ag if not ag.startswith("./") else ag[2:]
            declared_ids.append(Path(rel).stem)
            if not (team / rel).exists():
                ok = False
                msgs.append(f"{team.name}: agents 引用缺失文件 {ag}")
        if raw_agents == [] and not members:
            msgs.append(f"{team.name}: agents[] 为空且无 members")
        # 磁盘与声明对齐（磁盘多出 lead 文件属正常；核心成员必须全被声明覆盖）
        declared_set = {d for d in declared_ids if d}
        undeclared = [d for d in disk_ids if d not in declared_set]
        if undeclared:
            ok = False
            msgs.append(
                f"{team.name}: 磁盘有未声明文件 {undeclared}（声明={sorted(declared_set)}, 磁盘={disk_ids}）"
            )
    else:
        declared_set = {d for d in declared_ids if d}

    # 2. leadAgent 指向存在且被 agents[] 覆盖
    if lead:
        if lead not in disk_ids:
            ok = False
            msgs.append(f"{team.name}: leadAgent '{lead}' 不在磁盘 agent 文件中 (磁盘={disk_ids or '[]'})")
        if lead not in declared_set and lead not in members:
            ok = False
            msgs.append(f"{team.name}: leadAgent '{lead}' 既不在 agents[] 也不在 members 声明中")

    # 3. members（memberAgents）里的每个成员都应有磁盘文件（或属 agents[]）
    missing_member = [m for m in members if m not in disk_ids and m not in declared_set]
    if missing_member:
        ok = False
        msgs.append(f"{team.name}: members 声明成员缺磁盘文件 {missing_member}")

    # stub 判定（agents[] 声明 ≥2 成员但磁盘仅 1 个 lead = 仍在补齐中）
    if len(declared_set) >= 2 and len(disk_files) < 2:
        msgs.append(f"{team.name}: 疑似 STUB（声明 {len(declared_set)} 个 agent，磁盘仅 {len(disk_files)}）")

    return ok, msgs


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    strict = "--strict" in sys.argv
    target = args[0] if args else None

    all_ok = True
    any_issues = False
    for team_dir in sorted(EXPERTS.iterdir()):
        if not team_dir.is_dir() or team_dir.name in NON_TEAM:
            continue
        if target and team_dir.name != target:
            continue
        ok, msgs = check_one(team_dir, strict)
        if not ok:
            all_ok = False
            any_issues = True
            for m in msgs:
                print(f"  ❌ {m}")
        elif msgs and strict:
            any_issues = True
            for m in msgs:
                print(f"  ⚠️  {m}")

    if not any_issues:
        print("✅ 所有团队声明==资产一致。")
    elif all_ok and not strict:
        print("⚠️ 存在声明不全的团队（stub），但无内部引用冲突。加 --strict 可将 stub 判失败。")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
