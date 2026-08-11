#!/usr/bin/env python3
# 审判庭核心调度器（现行后端，二审终审制）：案卷 docket / 证据阶段 / 质证 / 一审裁决+回灌修订 / 二审终审归档 / 自学习 S1(计数)+S2(专家评分写回) / verdict 模板（投票+辩论合并策略）
# -*- coding: utf-8 -*-
"""trial-court-orchestrator.py — 审判庭核心调度器

提供审判庭五阶段（二审终审制）的核心辅助工具：
  1. docket — 议题立案登记、争点提取辅助
  2. evidence — 举证阶段 prompt 模板生成
  3. cross_exam — 质证阶段 prompt 模板生成
  4. revision — 一审回灌修订 prompt 模板生成（固定 1 轮）
  5. verdict-template — 一审判决书 / 二审终审意见书模板生成（--instance first|second）
  6. archive — 审判记录归档 + 自学习触发

用法：
    # 立案（在 Phase A 开始前运行，生成案卷信息 JSON）
    python trial-court-orchestrator.py docket --issue "..." --roles 3 --out ./docket.json

    # 生成举证子代理 prompt（在 Phase B 前运行）
    python trial-court-orchestrator.py prompt --phase evidence --role "正方" --docket ./docket.json

    # 生成质证子代理 prompt（在 Phase C 前运行）
    python trial-court-orchestrator.py prompt --phase cross-exam --role "正方" --docket ./docket.json --evidence-dir ./01-举证/

    # 生成一审回灌修订 prompt（Phase D 一审裁决后运行，固定 1 轮）
    python trial-court-orchestrator.py prompt --phase revision --role "正方" --docket ./docket.json --verdict-file ./03-一审/first-instance-verdict.md --evidence-dir ./02-质证/

    # 生成一审判决书模板（Phase D 一审裁决前运行）
    python trial-court-orchestrator.py verdict-template --docket ./docket.json --instance first --out ./03-一审/first-instance-verdict.md

    # 生成二审终审意见书模板（Phase E 前运行，终局不回灌）
    python trial-court-orchestrator.py verdict-template --docket ./docket.json --instance second --out ./05-二审终审/final-verdict.md

    # 归档整次审判（Phase E 完成后运行）
    python trial-court-orchestrator.py archive --docket ./docket.json --trial-dir ./deliverables/trial/TC-XXX/

    # 自学习：查看学习状态
    python trial-court-orchestrator.py learning-status

    # 自学习：初始化评分表
    python trial-court-orchestrator.py init-learning

    # 自学习：获取改进建议
    python trial-court-orchestrator.py improvements
"""
import json
import os
import sys
import argparse
import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_DIR = Path(__file__).resolve().parent.parent
# TRIAL_BASE：优先环境变量覆盖（ZCode 适配，归档到工作区根）；缺省 = 当前工作目录下 deliverables/trial
TRIAL_BASE = Path(os.environ.get("TRIAL_BASE", str(Path.cwd() / "deliverables" / "trial")))
LEARNING_DIR = SKILL_DIR / "references" / "learning-data"

# ─── 辅助函数 ───────────────────────────────────────────────

def _now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")

def _date_tag():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y%m%d")

def _next_docket_id():
    """生成格式 TC-YYYYMMDD-NNN"""
    tag = _date_tag()
    seq = 1
    # 尝试从已有案卷中找最大序号
    archive_dir = SKILL_DIR / "deliverables" / "trial" / "archive"
    if archive_dir.exists():
        for f in archive_dir.rglob("案卷信息.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                did = data.get("docket_id", "")
                if did.startswith(f"TC-{tag}"):
                    n = int(did.split("-")[-1])
                    seq = max(seq, n + 1)
            except Exception:
                pass
    return f"TC-{tag}-{seq:03d}"


def _require_confirmed(docket: dict, args) -> bool:
    """P0.9 用户确认关卡：未确认且非 --force 时拒绝执行后续阶段。"""
    if getattr(args, "force", False):
        return True
    if docket.get("confirmed") is not True:
        print("❌ 案卷尚未确认(confirm-docket)。请先运行确认命令，或使用 --force 紧急放行。", file=sys.stderr)
        sys.exit(2)
    return True


# ─── Phase A: 立案 ──────────────────────────────────────────

CMD_DOCKET_DESC = """\
生成案卷信息 JSON（Phase A 立案步骤的产物模板）。
输出包含 docket_id、争点清单骨架、角色分配表、资产解析占位符。
"""

def cmd_docket(args):
    issue = args.issue
    role_count = args.roles
    docket_id = _next_docket_id()

    roles_pool = ["正方(主张方)", "反方(质疑方)", "中立(比较方)",
                   "技术专家", "实务专家", "行业顾问"]
    assigned_roles = roles_pool[:role_count]

    record = {
        "docket_id": docket_id,
        "issue": issue,
        "issue_type": args.type or "Unclassified",
        "created_at": _now(),
        "complexity": f"L{min(role_count, 4)}",
        "sub_agent_count": role_count,
        "roles": [{"id": chr(65+i), "name": r, "status": "pending"}
                   for i, r in enumerate(assigned_roles)],
        "core_point": issue,       # 主理人可后续精化
        "sub_points": [],       # 主理人填写
        "assets_resolved": {    # 资产解析后由主理人或 asset-resolver 补充
            "expert_teams": [],
            "mcp_tools": [],
            "skills": [],
            "connectors": []
        },
        "status": "docketed",
        "cross_exam": {
            "max_rounds": getattr(args, "max_rounds", 2) or 2,
            "current_round": 0,
            "converged": False
        },
        # 二审终审制：一审裁决后回灌修订固定 1 轮（不追加、不因收敛提前）
        "revision": {
            "max_rounds": 1,
            "current_round": 0,
            "done": False
        },
        "confirmed": False
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 案卷已生成: {out_path}")
    else:
        print(json.dumps(record, ensure_ascii=False, indent=2))

    # 也写一份到 Skill 内的 learning-data/
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    (LEARNING_DIR / f"docket-{docket_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


# ─── Phase B/C: Prompt 模板生成 ─────────────────────────────

CMD_PROMPT_DESC = """\
生成子代理的 Prompt 模板（Phase B 举证 / Phase C 质证）。
输出可直接用于 Agent 工具的 prompt 文本。
"""

def cmd_prompt(args):
    phase = args.phase
    role = args.role

    if not args.docket:
        print("❌ 需要 --docket 参数（案卷信息 JSON 路径）", file=sys.stderr)
        sys.exit(1)

    try:
        docket = json.loads(Path(args.docket).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ 读取案卷失败: {e}", file=sys.stderr)
        sys.exit(1)

    # P0.9 用户确认关卡
    _require_confirmed(docket, args)

    # P0.5 质证轮次控制参数
    max_rounds = 2
    if docket.get("cross_exam"):
        max_rounds = docket["cross_exam"].get("max_rounds", 2)
    round_no = getattr(args, "round", 1) or 1

    assets = docket.get("assets_resolved", {})
    asset_lines = []
    if assets.get("mcp_tools"):
        asset_lines.append("### 🛠 MCP 工具")
        for t in assets["mcp_tools"]:
            asset_lines.append(f"- {t.get('name','?')}: {t.get('description','')}")
    if assets.get("skills"):
        asset_lines.append("### 📦 技能")
        for s in assets["skills"]:
            asset_lines.append(f"- {s.get('name','?')}: {s.get('usage_hint','')}")
    if assets.get("expert_teams"):
        asset_lines.append("### 👥 专家团建议")
        for e in assets["expert_teams"]:
            asset_lines.append(f"- {e.get('name','?')}: {e.get('usage_hint','')}")
    asset_block = "\n".join(asset_lines) if asset_lines else "（当前议题暂无自动匹配的资产，可使用联网搜索或已有知识）"

    if phase == "evidence":
        prompt = f"""\
## 角色：{role}

你是本次审判庭的「{role}」。议题编号：{docket.get('docket_id','?')}

### 议题
{docket.get('issue','')}

### 核心争点
{docket.get('core_point','（等待主理人填写）')}

### 子争点
{chr(10).join(f'- {p}' for p in docket.get('sub_points',['（等待主理人填写）']))}

### 你的立场分工
作为「{role}」，请从你的专业/立场角度对上述争点进行举证调查。

### 举证要求
1. 结论先行，然后展示依据
2. 每条依据必须标明来源（法条/文献/数据源/URL）
3. **严禁虚构**，存疑标注"存疑/待查"
4. 这是第一轮举证，稍后你会收到其他方产物并需要质证修正

### 可用资源
{asset_block}

### 产出格式
## 产物 P{{i}}（阶段B）— 角色：{role}
### 一、核心主张（结论先行）
### 二、举证依据（表格：| # | 依据/事实 | 来源 | 可信度 |）
### 五、给审判长的裁决建议
"""
    elif phase == "cross-exam":
        evidence_dir = Path(args.evidence_dir) if args.evidence_dir else None
        evidence_text = ""
        if evidence_dir and evidence_dir.exists():
            for f in sorted(evidence_dir.glob("*.md")):
                evidence_text += f"\n\n--- 来自 {f.name} ---\n"
                evidence_text += f.read_text(encoding="utf-8")[:2000]

        prompt = f"""\
## 阶段 C: 交叉质证 — {role}

你已经完成了第一轮举证。现在审判长把其他方的产物全部交给你。

### 质证要求
1. 对他方产物逐条质证：哪些可信？哪些有偏颇？遗漏了什么？
2. 修正己方立场：撤回站不住的主张，加强可坚守的，补充新反驳。
3. 注明相比上一轮的变更要点。

### 其他方产物
{evidence_text or "（产物将由审判长分发）"}

### 产出格式
## 产物 P{{i}}（阶段C）— 角色：{role}
### 一、对他方质证意见（逐方逐条）
### 二、己方立场修正说明
### 三、修正后的终局建议
"""
    elif phase == "revision":
        verdict_path = Path(args.verdict_file) if getattr(args, "verdict_file", "") else None
        verdict_text = ""
        if verdict_path and verdict_path.exists():
            verdict_text = verdict_path.read_text(encoding="utf-8")
        evidence_dir = Path(args.evidence_dir) if args.evidence_dir else None
        evidence_text = ""
        if evidence_dir and evidence_dir.exists():
            for f in sorted(evidence_dir.glob("*.md")):
                evidence_text += f"\n\n--- 来自 {f.name} ---\n"
                evidence_text += f.read_text(encoding="utf-8")[:2000]

        prompt = f"""\
## 阶段 D: 一审回灌修订 — {role}

一审已结束。审判长把《一审判决书》和各方最新产物全部交给你，请为二审终审做最后一轮修订（固定 1 轮，修订后直接进入二审终审，不再回灌）。

### 修订要求
1. 对一审判决逐条回应：接受（服判）或异议（给出理由与依据）
2. 基于判决与他方产物修正己方立场：撤回站不住的主张 / 加强可坚守的 / 补充新的反驳依据
3. 注明相比上一轮的变更要点（变与不变）

### 一审判决书
{verdict_text or "（一审判决书将由审判长分发）"}

### 其他方最新产物
{evidence_text or "（产物将由审判长分发）"}

### 产出格式
## 产物 P{{i}}（阶段D 回灌修订）— 角色：{role}
### 一、对一审判决的逐条回应（服判/异议+理由）
### 二、己方立场再修订说明
### 三、给二审审判长的终局建议
"""
    # P0.5 轮次控制提示（质证适用）；一审回灌修订固定 1 轮
    if phase == "revision":
        prompt += "\n\n### ⚠ 轮次控制\n本轮回灌修订为固定 1 轮，不追加、不因收敛提前结束。修订完成后直接进入二审终审(Phase E)，审判长将不再回灌。"
        if docket.get("revision"):
            docket["revision"]["current_round"] = 1
            docket["revision"]["done"] = True
        try:
            Path(args.docket).write_text(json.dumps(docket, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    elif phase == "cross-exam":
        if round_no >= max_rounds:
            prompt += f"\n\n### ⚠ 轮次控制\n已达到最大质证轮次({max_rounds})。请基于现有材料形成终局立场，不再开启新一轮，直接进入一审裁决(Phase D)。"
        else:
            prompt += f"\n\n### 轮次提示\n当前为第 {round_no}/{max_rounds} 轮质证。若各方立场已稳定收敛(连续两轮无实质变更)，可提前结束并进入一审裁决。"
        # 回写当前轮次到案卷
        if docket.get("cross_exam"):
            docket["cross_exam"]["current_round"] = round_no
            if round_no >= max_rounds:
                docket["cross_exam"]["converged"] = True
            try:
                Path(args.docket).write_text(json.dumps(docket, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
    else:
        print(f"❌ 未知阶段: {phase}", file=sys.stderr)
        sys.exit(1)

    print(prompt)
    return prompt


# ─── Phase D: 终审裁决模板 ──────────────────────────────────

CMD_VERDICT_DESC = """\
生成一审判决书 / 二审终审意见书 Markdown 模板（二审终审制，--instance first|second）。
"""

def cmd_verdict_template(args):
    if not args.docket:
        print("❌ 需要 --docket 参数", file=sys.stderr)
        sys.exit(1)
    try:
        docket = json.loads(Path(args.docket).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ 读取案卷失败: {e}", file=sys.stderr)
        sys.exit(1)

    _require_confirmed(docket, args)

    roles_str = " / ".join(r.get("name", "?") for r in docket.get("roles", []))
    assets_str = json.dumps(docket.get("assets_resolved", {}), ensure_ascii=False, indent=2)
    instance = getattr(args, "instance", "second") or "second"

    # C3: 合并器分型 — 根据 issue_type 判定裁决策略
    issue_type = (docket.get("issue_type") or "").lower()
    _VOTE_KEYWORDS = ("fact", "verify", "validation", "data", "check")
    _DEBATE_KEYWORDS = ("strategy", "tradeoff", "risk", "decision", "design", "plan")
    if any(k in issue_type for k in _VOTE_KEYWORDS):
        merger_type = "投票制（多数采信）"
        merger_note = "各方独立举证，按多数一致性采信；置信度 = 一致比例。"
    elif any(k in issue_type for k in _DEBATE_KEYWORDS):
        merger_type = "辩论+裁决制（审判长独任）"
        merger_note = "经质证辩论后由审判长综合裁决；置信度由审判长标注。"
    else:
        merger_type = "混合型（逐争点分型）"
        merger_note = "事实争点用投票制，价值/策略争点用辩论+裁决制。"

    if instance == "first":
        template = f"""\
## 一审判决书 — {docket.get('issue','?')}

### 一、案卷信息
- **docket_id**: {docket.get('docket_id','?')}
- **议题**: {docket.get('issue','?')}
- **审判日期**: {docket.get('created_at','?')}
- **参与方**: {roles_str}
- **议题分类**: {docket.get('issue_type','?')}
- **复杂度**: {docket.get('complexity','?')}
- **裁决策略**: {merger_type} — {merger_note}

### 二、争点回顾
| 争点 | 正方主张 | 反方主张 | 中立观察 |
|------|---------|---------|---------|
| （填写） | （填写） | （填写） | （填写） |

### 三、逐条裁决（一审）
| # | 争点 | 裁决（采信/部分采信/排除） | 采信哪方 | 理由 | 依据来源 |
|---|------|--------------------------|---------|------|---------|
| 1 | | | | | |

### 四、一审结论
（综合上述裁决，形成一审结论）

### 五、存疑/遗留事项
- （如实标注未解决的问题）

---
*本一审判决由审判长 {docket.get('docket_id','?')} 出具。一审判决为中间产物，将连同各方产物回灌各举证方修订 1 轮后进入二审终审。*
"""
    else:
        template = f"""\
## 终审意见书 — {docket.get('issue','?')}（二审终审 · 终局）

### 一、案卷信息
- **docket_id**: {docket.get('docket_id','?')}
- **议题**: {docket.get('issue','?')}
- **审判日期**: {docket.get('created_at','?')}
- **参与方**: {roles_str}
- **议题分类**: {docket.get('issue_type','?')}
- **复杂度**: {docket.get('complexity','?')}
- **裁决策略**: {merger_type} — {merger_note}
- **一审判决书**: 03-一审/first-instance-verdict.md

### 二、争点回顾
| 争点 | 正方主张 | 反方主张 | 中立观察 |
|------|---------|---------|---------|
| （填写） | （填写） | （填写） | （填写） |

### 三、质证与一审修订记录
| 阶段 | 轮数 | 关键变更（变与不变） |
|------|------|---------------------|
| 质证 | （填写） | （填写） |
| 一审回灌修订 | 1 轮 | （填写） |

### 四、逐条裁决（二审终局）
| # | 争点 | 裁决（采信/部分采信/排除） | 采信哪方 | 理由 | 与一审异同 | 依据来源 |
|---|------|--------------------------|---------|------|-----------|---------|
| 1 | | | | | | |

### 五、终局结论
（综合上述裁决，形成终局结论。标注"二审终审，不再回灌"）

### 六、存疑/遗留事项
- （如实标注未解决的问题）

### 七、资产使用评价
| 资产 | 类型 | 是否使用 | 贡献度 | 下次建议 |
|------|------|---------|-------|---------|
（由主理人填写）

---
*本终审意见书由审判长 {docket.get('docket_id','?')} 出具（二审终审 · 终局，不再回灌修订）。所有依据已在举证、质证与一审回灌修订阶段公开。*
"""
    if args.out:
        Path(args.out).write_text(template, encoding="utf-8")
        label = "一审判决书" if instance == "first" else "二审终审意见书"
        print(f"✅ 裁决文书模板已生成（{label}）: {args.out}")
    else:
        print(template)
    return template


# ─── 归档 ────────────────────────────────────────────────────

CMD_ARCHIVE_DESC = """\
归档整次审判记录到 archive/，触发自学习层。
"""

def cmd_archive(args):
    if not args.docket or not args.trial_dir:
        print("❌ 需要 --docket 和 --trial-dir 参数", file=sys.stderr)
        sys.exit(1)

    try:
        docket = json.loads(Path(args.docket).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ 读取案卷失败: {e}", file=sys.stderr)
        sys.exit(1)

    _require_confirmed(docket, args)

    trial_path = Path(args.trial_dir)
    if not trial_path.exists():
        print(f"❌ 审判目录不存在: {trial_path}", file=sys.stderr)
        sys.exit(1)

    # 归档路径
    docket_id = docket.get("docket_id", "unknown")
    date_prefix = docket_id.split("-")[1][:6]  # YYYYMM
    archive_root = SKILL_DIR / "deliverables" / "trial" / "archive"
    archive_dir = archive_root / date_prefix / docket_id
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 复制案卷信息
    (archive_dir / "00-案卷信息.json").write_text(
        json.dumps(docket, ensure_ascii=False, indent=2), encoding="utf-8")

    # 复制各阶段产物（二审终审制五阶段）
    for subdir in ["00-立案", "01-举证", "02-质证", "03-一审", "04-回灌修订", "05-二审终审"]:
        src = trial_path / subdir
        if src.exists():
            dst = archive_dir / subdir
            dst.mkdir(exist_ok=True)
            for f in src.glob("*"):
                dst.joinpath(f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

    # 生成归档摘要
    summary = {
        "docket_id": docket_id,
        "archive_path": str(archive_dir),
        "archived_at": _now(),
        "phases": ["立案", "举证", "质证", "一审", "回灌修订", "二审终审"],
        "sub_agent_count": docket.get("sub_agent_count", 0),
        "status": "archived"
    }
    (archive_dir / "归档摘要.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ 审判记录已归档: {archive_dir}")

    # 触发自学习
    _trigger_learning(docket, archive_dir)
    return archive_dir


def _writeback_expert_scores(docket: dict):
    scores_file = LEARNING_DIR / "expert_scores.json"
    scores = {}
    if scores_file.exists():
        try:
            scores = json.loads(scores_file.read_text(encoding="utf-8"))
        except Exception:
            scores = {}
    teams = docket.get("assets_resolved", {}).get("expert_teams", [])
    for t in teams:
        name = t.get("name", "") if isinstance(t, dict) else str(t)
        if name:
            prev = scores.get(name, 0.5)
            scores[name] = round(min(prev + 0.05, 1.0), 4)
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    scores_file.write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")


def _trigger_learning(docket: dict, archive_dir: Path):
    """触发自学习层（Layer S1 + S2 轻量版）"""
    # B6: 专家评分回写
    _writeback_expert_scores(docket)
    # S1: 更新审判计数
    learning_file = LEARNING_DIR / "trial-count.json"
    counts = {"total": 0, "by_type": {}}
    if learning_file.exists():
        try:
            counts = json.loads(learning_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    counts["total"] = counts.get("total", 0) + 1
    issue_type = docket.get("issue_type", "Unclassified")
    by_type = counts.setdefault("by_type", {})
    by_type[issue_type] = by_type.get(issue_type, 0) + 1
    learning_file.parent.mkdir(parents=True, exist_ok=True)
    learning_file.write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📊 自学习计数已更新: 总 {counts['total']} 次")

    # P0.3: S2-S4 自学习管道（容错：异常不影响归档主流程）
    try:
        import importlib.util as _ilu
        _sl_path = Path(__file__).resolve().parent / "self_learning.py"
        if _sl_path.exists():
            _sl_spec = _ilu.spec_from_file_location("self_learning_mod", str(_sl_path))
            _sl_mod = _ilu.module_from_spec(_sl_spec)
            _sl_spec.loader.exec_module(_sl_mod)
            _sl_mod.process_trial(docket, archive_dir)
    except Exception as _e:
        print(f"⚠ 自学习S2-S4跳过(异常): {_e}")


# ─── C4: AdvEvol 三本外部记忆追加 ─────────────────────────────

def append_to_memory(docket: dict, verdict: dict):
    """终审后追加记录到 facts/strategies/cases 三本外部记忆。"""
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    ts = _now()
    did = docket.get("docket_id", "unknown")

    def _append(filename, entry):
        p = LEARNING_DIR / filename
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"entries": []}
        data["entries"].append(entry)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # cases: 每次审判必追加
    _append("cases.json", {
        "id": f"C-{did}", "docket_id": did,
        "issue_summary": docket.get("issue", "")[:120],
        "issue_type": docket.get("issue_type", ""),
        "complexity": docket.get("complexity", ""),
        "roles_used": [r.get("name", "") for r in docket.get("roles", [])],
        "merger_type": verdict.get("merger_type", "mixed"),
        "verdict_confidence": verdict.get("confidence", 0.0),
        "key_lessons": verdict.get("lessons", []),
        "assets_used": list(docket.get("assets_resolved", {}).keys()),
        "created_at": ts,
    })
    # strategies: 仅当裁决置信度 >= 0.7 时追加
    if verdict.get("confidence", 0) >= 0.7:
        _append("strategies.json", {
            "id": f"S-{did}", "issue_type": docket.get("issue_type", ""),
            "strategy": verdict.get("strategy_summary", ""),
            "merger_type": verdict.get("merger_type", ""),
            "effectiveness": verdict.get("confidence", 0),
            "applied_in": [did], "created_at": ts,
        })
    # facts: 仅当 verdict 含 verified_facts 时追加
    for i, f in enumerate(verdict.get("verified_facts", []), 1):
        _append("facts.json", {
            "id": f"F-{did}-{i}", "fact": f.get("fact", ""),
            "domain": docket.get("issue_type", ""),
            "source": f.get("source", ""), "confidence": f.get("confidence", 0.8),
            "verified_in": [did], "created_at": ts, "last_verified": ts,
        })
    print(f"📝 AdvEvol 记忆已追加: cases +{1}, strategies +{1 if verdict.get('confidence',0)>=0.7 else 0}, facts +{len(verdict.get('verified_facts',[]))}")


# ─── 自学习 ──────────────────────────────────────────────────

CMD_LEARNING_STATUS_DESC = """\
查看当前自学习状态：审判总次数、按类型分布、改进建议数量。
"""

def cmd_learning_status(args):
    learning_file = LEARNING_DIR / "trial-count.json"
    if not learning_file.exists():
        print("📊 尚无审判记录。第一次审判完成后将自动初始化。")
        return {"total": 0}

    counts = json.loads(learning_file.read_text(encoding="utf-8"))
    print(f"📊 自学习状态")
    print(f"━━━━━━━━━━━━━━━━━━━")
    print(f"  审判总次数: {counts.get('total', 0)}")
    print(f"  按议题类型分布:")
    for t, c in counts.get("by_type", {}).items():
        print(f"    {t}: {c} 次")
    print(f"━━━━━━━━━━━━━━━━━━━")
    print(f"  建议：随着审判次数增加，专家调度和资产匹配将自动优化。")
    return counts


CMD_INIT_LEARNING_DESC = """\
初始化自学习系统：创建学习目录和初始评分表。
"""

def cmd_init_learning(args):
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    init_data = {
        "initialized_at": _now(),
        "trial_count": 0,
        "expert_scores": {},
        "mcp_scores": {},
        "skill_scores": {},
        "improvements": []
    }
    (LEARNING_DIR / "learning-init.json").write_text(
        json.dumps(init_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (LEARNING_DIR / "trial-count.json").write_text(
        json.dumps({"total": 0, "by_type": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ 自学习系统已初始化")
    print(f"   目录: {LEARNING_DIR}")
    return init_data


CMD_IMPROVEMENTS_DESC = """\
基于历史审判记录生成流程改进建议。
"""

def cmd_improvements(args):
    learning_dir = LEARNING_DIR
    improvements = []

    # 查看是否有归档记录
    archive_dir = SKILL_DIR / "deliverables" / "trial" / "archive"
    if archive_dir.exists():
        archives = list(archive_dir.rglob("00-案卷信息.json"))
        improvements.append(f"✅ 已有 {len(archives)} 次审判归档可参考")
    else:
        improvements.append("ℹ️ 尚无归档记录，完成一次审判后将有更多建议")

    # 查看连接器与技能的匹配建议
    mcp_suggestions = [
        "💡 建议：金融类议题优先使用 tdx-connector(通达信) + westock-mcp(自选股) 作为数据源",
        "💡 建议：法律类议题可借助 chatlaw-team 或 enterprise-legal-team 专家团",
        "💡 建议：需调研的议题可加载 deep-research skill 增强调研深度",
        "💡 建议：跨议题知识积累将在 5 次以上审判后产生实质性推荐"
    ]
    improvements.extend(mcp_suggestions)

    for imp in improvements:
        print(imp)

    return improvements


# ─── P0.9 用户确认关卡 ──────────────────────────────────────

CMD_CONFIRM_DESC = """确认案卷(用户确认关卡)。docket 生成后需经此确认方可进入举证/质证/终审。"""

def cmd_confirm_docket(args):
    if not args.docket:
        print("❌ 需要 --docket 参数", file=sys.stderr)
        sys.exit(1)
    p = Path(args.docket)
    if not p.exists():
        print(f"❌ 案卷不存在: {p}", file=sys.stderr)
        sys.exit(1)
    docket = json.loads(p.read_text(encoding="utf-8"))
    docket["confirmed"] = True
    if docket.get("status") == "docketed":
        docket["status"] = "confirmed"
    p.write_text(json.dumps(docket, ensure_ascii=False, indent=2), encoding="utf-8")
    dup = LEARNING_DIR / f"docket-{docket.get('docket_id','?')}.json"
    if dup.exists():
        dup.write_text(json.dumps(docket, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 案卷已确认: {docket.get('docket_id','?')} — 可进入举证/质证/终审阶段")
    return docket


# ─── P0.5 收敛检测 ──────────────────────────────────────────

CMD_CONVERGE_DESC = """检查两轮质证产物是否收敛(文本相似度 >= 阈值即收敛)。"""

def cmd_convergence_check(args):
    import difflib

    def _load(path):
        pp = Path(path)
        if pp.exists():
            return pp.read_text(encoding="utf-8")
        return path

    prev = _load(args.prev)
    curr = _load(args.curr)
    if not prev or not curr:
        print("⚠ 缺少对比文本，无法判定收敛", file=sys.stderr)
        sys.exit(1)
    ratio = difflib.SequenceMatcher(None, prev, curr).ratio()
    threshold = args.threshold
    converged = ratio >= threshold
    print(f"收敛相似度: {ratio:.2%} (阈值 {threshold:.0%}) -> {'已收敛' if converged else '未收敛'}")
    print(f"建议: {'可进入一审裁决' if converged else '继续下一轮质证'}")
    return {"similarity": ratio, "converged": converged}


# ─── P0.4 交叉验证集成 ──────────────────────────────────────

CMD_XV_DESC = """将举证产物送入交叉验证引擎，产出验证报告(集成 cross-validator.py)。"""

def cmd_cross_validate(args):
    import subprocess
    cv_path = Path(__file__).resolve().parent / "cross-validator.py"
    if not cv_path.exists():
        print("❌ 未找到 cross-validator.py", file=sys.stderr)
        sys.exit(1)
    docket_path = Path(args.docket)
    if not docket_path.exists():
        print(f"❌ 案卷不存在: {docket_path}", file=sys.stderr)
        sys.exit(1)
    ev_dir = Path(args.evidence_dir)
    claims = []
    if ev_dir.exists():
        for f in sorted(ev_dir.glob("*.md")):
            claims.append({"agent": f.stem, "text": f.read_text(encoding="utf-8")})
    if not claims:
        print("⚠ 无举证产物可验证", file=sys.stderr)
        sys.exit(1)
    tmp = ev_dir / "_xv_input.json"
    tmp.write_text(json.dumps(claims, ensure_ascii=False), encoding="utf-8")
    try:
        res = subprocess.run(
            [sys.executable, str(cv_path), "--task", args.docket, "--depth", args.depth,
             "--input", str(tmp)], capture_output=True, text=True, encoding="utf-8")
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass
    if res.returncode != 0:
        print(f"❌ 交叉验证执行失败: {res.stderr}", file=sys.stderr)
        sys.exit(1)
    report = json.loads(res.stdout)
    out_path = Path(args.out) if args.out else (ev_dir / "validation-report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 交叉验证报告已生成: {out_path}")
    print(f"   总体置信度: {report.get('overall_confidence')}  冲突数: {len(report.get('conflicts', []))}")
    return report


# ─── P0.10 错误恢复(集成 self_heal.py) ──────────────────────

CMD_HEAL_DESC = """对错误进行分类并给出恢复建议(集成 self_heal.py)。"""

def cmd_self_heal(args):
    try:
        import importlib.util as _ilu
        sh_path = Path(__file__).resolve().parent / "self_heal.py"
        if not sh_path.exists():
            print("❌ 未找到 self_heal.py", file=sys.stderr)
            sys.exit(1)
        _sh_spec = _ilu.spec_from_file_location("self_heal_mod", str(sh_path))
        _sh_mod = _ilu.module_from_spec(_sh_spec)
        _sh_spec.loader.exec_module(_sh_mod)
        etype = _sh_mod.classify_error(args.error_message)
        info = _sh_mod.ERROR_TYPES.get(etype, _sh_mod.ERROR_TYPES["unknown"])
        result = {
            "error_type": etype,
            "severity": info["severity"],
            "recoverable": info["recoverable"],
            "fix_actions": info["fix_actions"],
            "max_retries": info["max_retries"],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except Exception as _e:
        print(f"❌ 错误恢复模块加载失败: {_e}", file=sys.stderr)
        sys.exit(1)


# ─── P0.11 孤立脚本集成 ─────────────────────────────────────

CMD_HEALTH_DESC = """运行 health-monitor 检查团队/Agent 健康(集成 health-monitor.py)。"""

def cmd_health(args):
    import subprocess
    hm_path = Path(__file__).resolve().parent / "health-monitor.py"
    if not hm_path.exists():
        print("❌ 未找到 health-monitor.py", file=sys.stderr)
        sys.exit(1)
    cli = [sys.executable, str(hm_path), args.action]
    if args.team_id:
        cli.append(args.team_id)
    res = subprocess.run(cli, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        sys.exit(1)
    print(res.stdout)
    return res.stdout


CMD_AUTO_DESC = """根据错误类型与重试次数自动决策 retry/skip/abort(集成 auto-decider.py)。"""

def cmd_auto_decide(args):
    import subprocess
    ad_path = Path(__file__).resolve().parent / "auto-decider.py"
    if not ad_path.exists():
        print("❌ 未找到 auto-decider.py", file=sys.stderr)
        sys.exit(1)
    cli = [sys.executable, str(ad_path), "--error-message", args.error_message,
           "--error-type", args.error_type, "--retry-count", str(args.retry_count)]
    res = subprocess.run(cli, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        sys.exit(1)
    print(res.stdout)
    return res.stdout


# ─── 主入口 ──────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="审判庭核心调度器")
    sub = ap.add_subparsers(dest="command", required=True)

    # docket
    p_docket = sub.add_parser("docket", description=CMD_DOCKET_DESC)
    p_docket.add_argument("--issue", required=True, help="议题描述")
    p_docket.add_argument("--roles", type=int, default=3, choices=[2,3,4,5,6], help="子代理数量")
    p_docket.add_argument("--type", default="", help="议题类型标签(如 08-FinanceInvestment)")
    p_docket.add_argument("--max-rounds", type=int, default=2, help="质证最大轮次(默认2, 二审终审制统一口径)")
    p_docket.add_argument("--out", default="", help="输出路径")

    # prompt
    p_prompt = sub.add_parser("prompt", description=CMD_PROMPT_DESC)
    p_prompt.add_argument("--phase", required=True, choices=["evidence", "cross-exam", "revision"], help="阶段: evidence=举证 / cross-exam=质证 / revision=一审回灌修订")
    p_prompt.add_argument("--role", required=True, help="角色名")
    p_prompt.add_argument("--docket", default="", help="案卷信息 JSON 路径")
    p_prompt.add_argument("--evidence-dir", default="", help="产物目录（质证/回灌修订阶段需要，指向他方产物目录）")
    p_prompt.add_argument("--verdict-file", default="", help="一审判决书路径（回灌修订阶段需要，如 03-一审/first-instance-verdict.md）")
    p_prompt.add_argument("--round", type=int, default=1, help="质证轮次序号(从1开始)")
    p_prompt.add_argument("--force", action="store_true", help="跳过用户确认关卡(紧急放行)")

    # verdict-template
    p_vt = sub.add_parser("verdict-template", description=CMD_VERDICT_DESC)
    p_vt.add_argument("--docket", required=True, help="案卷信息 JSON 路径")
    p_vt.add_argument("--instance", default="second", choices=["first", "second"], help="裁决文书类型: first=一审判决书 / second=二审终审意见书(默认,终局不回灌)")
    p_vt.add_argument("--out", default="", help="输出路径")
    p_vt.add_argument("--force", action="store_true", help="跳过用户确认关卡(紧急放行)")

    # archive
    p_arc = sub.add_parser("archive", description=CMD_ARCHIVE_DESC)
    p_arc.add_argument("--docket", required=True, help="案卷信息 JSON 路径")
    p_arc.add_argument("--trial-dir", required=True, help="审判产物目录路径")
    p_arc.add_argument("--force", action="store_true", help="跳过用户确认关卡(紧急放行)")

    # learning
    sub.add_parser("learning-status", description=CMD_LEARNING_STATUS_DESC)
    sub.add_parser("init-learning", description=CMD_INIT_LEARNING_DESC)
    sub.add_parser("improvements", description=CMD_IMPROVEMENTS_DESC)

    # P0.9 用户确认关卡
    p_conf = sub.add_parser("confirm-docket", description=CMD_CONFIRM_DESC)
    p_conf.add_argument("--docket", required=True, help="案卷信息 JSON 路径")

    # P0.5 收敛检测
    p_conv = sub.add_parser("convergence-check", description=CMD_CONVERGE_DESC)
    p_conv.add_argument("--prev", required=True, help="上一轮质证产物(文件或文本)")
    p_conv.add_argument("--curr", required=True, help="本轮质证产物(文件或文本)")
    p_conv.add_argument("--threshold", type=float, default=0.85, help="收敛阈值(默认0.85)")

    # P0.4 交叉验证集成
    p_xv = sub.add_parser("cross-validate", description=CMD_XV_DESC)
    p_xv.add_argument("--docket", required=True, help="案卷信息 JSON 路径")
    p_xv.add_argument("--evidence-dir", required=True, help="举证产物目录")
    p_xv.add_argument("--depth", default="standard", choices=["skip", "light", "standard", "deep", "auto"], help="验证深度")
    p_xv.add_argument("--out", default="", help="验证报告输出路径")

    # P0.10 错误恢复
    p_heal = sub.add_parser("self-heal", description=CMD_HEAL_DESC)
    p_heal.add_argument("--error-message", required=True, help="错误文本")

    # P0.11 孤立脚本集成
    p_h = sub.add_parser("health", description=CMD_HEALTH_DESC)
    p_h.add_argument("action", choices=["check", "watch", "summary"])
    p_h.add_argument("team_id", nargs="?", default=None)
    p_ad = sub.add_parser("auto-decide", description=CMD_AUTO_DESC)
    p_ad.add_argument("--error-message", required=True, help="错误文本")
    p_ad.add_argument("--error-type", default="auto", help="错误类型(auto=自动推断)")
    p_ad.add_argument("--retry-count", type=int, default=0, help="已重试次数")

    args = ap.parse_args()

    if args.command == "docket":
        cmd_docket(args)
    elif args.command == "prompt":
        cmd_prompt(args)
    elif args.command == "verdict-template":
        cmd_verdict_template(args)
    elif args.command == "archive":
        cmd_archive(args)
    elif args.command == "learning-status":
        cmd_learning_status(args)
    elif args.command == "init-learning":
        cmd_init_learning(args)
    elif args.command == "improvements":
        cmd_improvements(args)
    elif args.command == "confirm-docket":
        cmd_confirm_docket(args)
    elif args.command == "convergence-check":
        cmd_convergence_check(args)
    elif args.command == "cross-validate":
        cmd_cross_validate(args)
    elif args.command == "self-heal":
        cmd_self_heal(args)
    elif args.command == "health":
        cmd_health(args)
    elif args.command == "auto-decide":
        cmd_auto_decide(args)

if __name__ == "__main__":
    main()
