#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dispatch-planner.py — 团队编排「派工方案生成器」(WorkBuddy 适配)

读取 references/workbuddy-experts/<团队>/plugin.json 与 agents/*.md，
结合 task-decomposer + expert-matcher 的匹配结果，
输出一份结构化派工方案：

    匹配团队 -> 主理人/成员人设(含 .md 路径与专长摘要) -> 逐成员子任务 -> 主理人汇总指令 -> 跨团队协调说明

本脚本**只生成派工方案**，不真正拉起子智能体。
子智能体的拉起由 WorkBuddy 主智能体按 SKILL.md 的「Mode B 执行协议」完成
（读取方案里每个 agent 的 .md 人设，经 Agent 工具逐个拉起 general-purpose 子智能体）。

依赖（与本脚本同目录）：
    expert-matcher.py   —— 提供 load_all_experts() / match()
    task-decomposer.py  —— 提供 decompose()（仅 --task 自动拆解时需要）

用法：
    # 自动：任务 -> 拆解 -> 匹配 -> 派工
    python dispatch-planner.py --task "帮我分析宁德时代的基本面和估值情况" --top-k 2

    # 直接指定团队（跳过匹配）
    python dispatch-planner.py --teams a-share-analysis stock-partner-team

    # 按领域匹配
    python dispatch-planner.py --domains 08-FinanceInvestment 05-SalesMarketing

    # 机器可读 JSON（可管道给其它工具）
    python dispatch-planner.py --task "..." --json

    # 同时落盘到指定文件
    python dispatch-planner.py --task "..." --out ./my-plan.md
"""
import json
import os
import sys
import argparse
import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
EXPERT_DIR = SKILL_DIR / "references" / "workbuddy-experts"

BRIEF_CHARS = 600  # 成员人设摘要长度


def _load_module(filename: str):
    """按文件路径加载同目录脚本（规避连字符文件名无法 import 的问题）。"""
    import importlib.util as _ilu
    p = SKILL_DIR / "scripts" / filename
    spec = _ilu.spec_from_file_location(filename.replace(".", "_"), str(p))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_agent_md(team_dir: Path, agent_id: str):
    """返回 (role_desc, brief, md_rel_path, full_text)。"""
    md = team_dir / "agents" / f"{agent_id}.md"
    rel = f"references/workbuddy-experts/{team_dir.name}/agents/{agent_id}.md"
    if not md.exists():
        return ("", "", rel, "")
    text = md.read_text(encoding="utf-8")
    role_desc = ""
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if line.lower().startswith("description:"):
                    role_desc = line.split(":", 1)[1].strip()
            body = parts[2]
    brief = body.strip()[:BRIEF_CHARS]
    return (role_desc, brief, rel, text)


def _ids_from_agents(data: dict):
    return [os.path.splitext(os.path.basename(a))[0] for a in data.get("agents", [])]


def build_team_plan(team_name: str, match_score=None):
    team_dir = EXPERT_DIR / team_name
    pj = team_dir / "plugin.json"
    if not pj.exists():
        return None
    try:
        data = json.loads(pj.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        print(f"[WARN] 团队配置损坏，跳过: {pj.name} ({e})")
        return None
    members_meta = data.get("members", [])
    meta = {m.get("id"): m for m in members_meta}

    team_info = data.get("teamInfo", {})
    ids_from_agents = _ids_from_agents(data)
    lead_id = (
        team_info.get("leadAgent")
        or (members_meta[0].get("id") if members_meta else None)
        or (ids_from_agents[0] if ids_from_agents else None)
    )
    member_ids = (
        team_info.get("memberAgents")
        or [m.get("id") for m in members_meta if m.get("id") != lead_id]
        or [i for i in ids_from_agents if i != lead_id]
    )
    member_ids = list(dict.fromkeys(member_ids))  # 保序去重，防重复派工

    def member_entry(aid):
        m = meta.get(aid, {})
        role_desc, brief, rel, _ = read_agent_md(team_dir, aid)
        return {
            "id": aid,
            "name_zh": m.get("name", {}).get("zh", ""),
            "profession_zh": m.get("profession", {}).get("zh", ""),
            "role": m.get("role", "member" if aid != lead_id else "lead"),
            "md": rel,
            "role_desc": role_desc,
            "brief": brief,
        }

    lead = member_entry(lead_id) if lead_id else {}
    members = [member_entry(a) for a in member_ids]
    return {
        "name": team_name,
        "display_zh": data.get("displayName", {}).get("zh", ""),
        "profession_zh": data.get("profession", {}).get("zh", ""),
        "category_id": data.get("categoryId", ""),
        "match_score": match_score,
        "init_prompt_zh": data.get("defaultInitPrompt", {}).get("zh", ""),
        "lead": lead,
        "members": members,
    }


def _profession_focus(profession_zh: str) -> str:
    keyword_map = {
        "宏观": "聚焦宏观经济环境、政策传导、周期定位",
        "市场": "聚焦盘面数据、量价关系、情绪指标",
        "个股": "聚焦公司基本面、财务数据、竞争力",
        "估值": "聚焦估值模型（DCF/PE/PB）、安全边际",
        "产业": "聚焦产业链上下游、竞争格局、供需",
        "资金": "聚焦主力资金流向、北向资金、筹码结构",
        "风险": "聚焦风险因子识别、压力测试、对冲建议",
        "策略": "聚焦配置策略、择时建议、组合构建",
        "合规": "聚焦合规审查要点、法规适用性、处罚风险",
        "诉讼": "聚焦诉讼策略、证据链构建、庭审应对",
        "合同": "聚焦合同条款审查、违约责任、争议解决",
        "品牌": "聚焦品牌定位、传播策略、心智占位",
        "增长": "聚焦获客渠道、转化漏斗、ROI优化",
        "内容": "聚焦内容策略、分发渠道、用户互动",
        "架构": "聚焦系统架构设计、技术选型、扩展性",
        "测试": "聚焦测试策略、覆盖率、自动化方案",
        "运维": "聚焦可靠性、监控告警、故障恢复",
    }
    for kw, focus in keyword_map.items():
        if kw in profession_zh:
            return focus
    return f"聚焦你的核心专长（{profession_zh}）"


def assign_subtasks(team_plan: dict, task: str):
    """为每个成员生成子任务提示；为主理人生成汇总提示。"""
    dispatch = []
    for m in team_plan.get("members", []):
        focus = _profession_focus(m.get("profession_zh", ""))
        subtask = (
            f"任务背景：{task}\n"
            f"你的角色：{m.get('profession_zh','')}（{m.get('name_zh','')}）。\n"
            f"你的专属视角：{focus}。\n"
            f"你的立场：{m.get('stance', '中立')}（正/反/中立，请明确表达该立场下的主张）。\n"
            f"请基于你的人设与专长，独立完成你负责的部分；"
            f"聚焦你最擅长的角度，不要越界替其他成员工作。\n"
            f"\n【A3 单页契约·强制输出格式】严格返回如下 JSON（不得自由发挥格式；全文不超过 400 字）：\n"
            f'{{"role":"{m.get("profession_zh","")}",'
            f'"artifacts":{{"conclusions":["..."],"evidence":["..."],'
            f'"risks":["..."],"actions":["..."]}},'
            f'"confidence":0.0,"uncertainties":["..."]}}\n'
            f"字段说明：confidence 为 0.0-1.0 浮点数；uncertainties 为需主理人/用户确认的存疑点。"
        )
        dispatch.append({
            "agent_id": m["id"],
            "subtask": subtask,
            "deliverable_template": {
                "role": m.get("profession_zh",""),
                "tools": [],
                "artifacts": {"conclusions": [], "evidence": [], "risks": [], "actions": []},
                "confidence": 0.0,
                "uncertainties": []
            }
        })
    synthesis = (
        f"任务：{task}\n"
        f"你是「{team_plan.get('display_zh','')}」的主理人 {team_plan.get('lead',{}).get('name_zh','')}。"
        f"你已收到 {len(team_plan.get('members',[]))} 位成员分别提交的成果。\n"
        f"请负责：① 识别各成员结论的共识与冲突；② 交叉验证关键事实；"
        f"③ 汇编成一份结构化、面向用户的终稿（含结论、依据、风险、行动建议）。"
        f"你不做重复分析，只做编排与合成。"
    )
    return dispatch, synthesis


def build_plan(task: str, team_names: list, score_map: dict, domains: list):
    teams = []
    for tn in team_names:
        tp = build_team_plan(tn, score_map.get(tn))
        if tp:
            d, s = assign_subtasks(tp, task)
            tp["dispatch"] = d
            tp["synthesis_prompt"] = s
            teams.append(tp)
    return {
        "task": task,
        "domains": domains,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "team_count": len(teams),
        "teams": teams,
        "cross_team_coordination": (
            "若匹配到多个团队，主智能体应：① 先确定团队间的依赖与交接点；"
            "② 让上游团队的终稿作为下游团队的输入；"
            "③ 最后由一个总主理人（或主智能体自身）做跨团队一致性校验与统一输出。"
        ),
    }


def render_md(plan: dict) -> str:
    lines = []
    lines.append("# 团队编排派工方案")
    lines.append("")
    lines.append(f"- **任务**：{plan.get('task') or '（直接指定团队，无任务文本）'}")
    lines.append(f"- **拆解领域**：{', '.join(plan.get('domains') or []) or '（未拆解）'}")
    lines.append(f"- **匹配团队数**：{plan.get('team_count')}")
    lines.append(f"- **生成时间**：{plan.get('generated_at')}")
    lines.append("")
    for idx, t in enumerate(plan.get("teams", []), 1):
        score = t.get("match_score")
        score_s = f"｜匹配度 {score:.0%}" if isinstance(score, (int, float)) else ""
        lines.append(f"## 团队 {idx}：{t.get('display_zh')}（`{t.get('name')}`）{score_s}")
        lines.append(f"- 定位：{t.get('profession_zh')} ｜ 分类：{t.get('category_id')}")
        if t.get("init_prompt_zh"):
            lines.append(f"- 初始化示例：{t.get('init_prompt_zh')}")
        lead = t.get("lead") or {}
        lines.append("")
        lines.append(f"### 主理人：{lead.get('name_zh')}（{lead.get('profession_zh')}）")
        if lead.get("role_desc"):
            lines.append(f"- 职责：{lead.get('role_desc')}")
        if lead.get("md"):
            lines.append(f"- 人设文件：`{lead.get('md')}`")
        if lead.get("brief"):
            lines.append(f"- 摘要：{lead.get('brief')[:200]}…")
        lines.append("")
        lines.append("### 成员派工")
        for m, disp in zip(t.get("members", []), t.get("dispatch", [])):
            lines.append(f"- **{m.get('name_zh')}（{m.get('profession_zh')}）** — 人设：`{m.get('md')}`")
            lines.append(f"  - 子任务：{disp.get('subtask')}")
            dt = disp.get("deliverable_template")
            if dt:
                lines.append(f"  - 交付物模板：角色={dt.get('role')}｜产物={dt.get('artifacts')}｜置信度占位｜不确定项占位")
        lines.append("")
        lines.append("### 主理人汇总指令")
        lines.append(f"{t.get('synthesis_prompt')}")
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## 跨团队协调")
    lines.append(plan.get("cross_team_coordination", ""))
    lines.append("")
    lines.append("> 执行方式：主智能体按 SKILL.md 的「Mode B 执行协议」，读取上面临各个 agent 的 `人设文件`，")
    lines.append("> 经 Agent 工具逐个拉起 general-purpose 子智能体执行子任务，最后由主理人（或主智能体）合成。")
    return "\n".join(lines)


def main():
    # Windows 控制台默认 GBK，人设文本含 emoji/特殊符号会导致 print 崩溃；
    # 统一以 UTF-8 输出（管道/文件场景保留原字符，控制台场景降级为替换符，不报错）。
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="团队编排派工方案生成器")
    ap.add_argument("--task", default="", help="自然语言任务（自动拆解+匹配）")
    ap.add_argument("--teams", nargs="+", default=[], help="直接指定团队名（跳过匹配）")
    ap.add_argument("--domains", nargs="+", default=[], help="按领域 ID 匹配")
    ap.add_argument("--top-k", type=int, default=2, help="自动匹配时取 Top-K 团队")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    ap.add_argument("--out", default="", help="额外落盘路径（.md 或 .json，按 --json 决定格式）")
    args = ap.parse_args()

    team_names = []
    domains = []
    score_map = {}

    if args.teams:
        team_names = args.teams
    else:
        em = _load_module("expert-matcher.py")
        experts = em.load_all_experts()
        if args.domains:
            domains = args.domains
        else:
            td = _load_module("task-decomposer.py")
            res = td.decompose(args.task)
            domains = res.get("domains", [])
        matches = em.match(experts, domains, args.top_k)
        team_names = [m[1]["name"] for m in matches]
        score_map = {m[1]["name"]: round(m[0], 2) for m in matches}

    plan = build_plan(args.task, team_names, score_map, domains)

    # 始终在技能目录留一份最新方案，便于复查/复用
    out_dir = SKILL_DIR / "scripts" / "output"
    out_dir.mkdir(exist_ok=True)
    if args.json:
        payload = json.dumps(plan, ensure_ascii=False, indent=2)
        (out_dir / "last_dispatch_plan.json").write_text(payload, encoding="utf-8")
        if args.out:
            Path(args.out).write_text(payload, encoding="utf-8")
        print(payload)
    else:
        md = render_md(plan)
        (out_dir / "last_dispatch_plan.md").write_text(md, encoding="utf-8")
        if args.out:
            Path(args.out).write_text(md, encoding="utf-8")
        print(md)


if __name__ == "__main__":
    main()
