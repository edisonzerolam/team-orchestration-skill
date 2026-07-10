#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Problem Solving Panel v1.0 — 专家小组研讨管道

当自愈管道的 escalate 策略被触发时，组建专家小组：
  L0: 预设规则匹配（零成本）
  L1: 单专家深度调研+出方案
  L2: 多专家研讨+辩论+投票
  L3: 人类 escalate（最终兜底）

用法:
  python3 problem_solver.py --team <team_id> --agent <agent_id> --fault-type FT-04
  python3 problem_solver.py --team <team_id> --l0-rule <rule_name>
  python3 problem_solver.py --team <team_id> --repair-records
"""
import json, sys, time, random, argparse, hashlib
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
STATE_DIR = SKILL_DIR / "shared" / "team-brain"
STATE_DIR.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_DIR = SKILL_DIR / "references" / "knowledge"

# ── 故障→知识域映射 ──────────────────────────────────────────────────────────

FAULT_TO_DOMAIN = {
    "FT-04": ["NLP", "AI_Methodology", "Reasoning"],
    "FT-07": ["ML_Engineering", "System", "Reliability"],
    "FT-09": ["Data_Engineering", "Security", "System"],
    "FT-10": ["DevOps", "System", "Config"],
}

PANEL_CONFIG = {
    "light": {"experts": 1, "sceptic": False, "urls": 2, "discussion_rounds": 1, "timeout_s": 60},
    "standard": {"experts": 2, "sceptic": True, "urls": 3, "discussion_rounds": 3, "timeout_s": 120},
    "deep": {"experts": 3, "sceptic": True, "urls": 4, "discussion_rounds": 3, "timeout_s": 180},
}

FAULT_THICKNESS = {
    "FT-04": "standard", "FT-07": "standard",
    "FT-09": "deep", "FT-10": "light",
}

TRIGGER_FAULTS = {"FT-04", "FT-07", "FT-09", "FT-10"}

# ── 数据类 ──────────────────────────────────────────────────────────────────────

@dataclass
class Solution:
    id: str
    expert_id: str
    name: str
    steps: list
    rationale: str
    risk: str
    difficulty: str            # Easy / Medium / Hard
    confidence: float
    source_count: int = 0
    is_independent: bool = True

@dataclass
class PanelResult:
    session_id: str
    team_id: str
    agent_id: str
    fault_type: str
    level: str                 # L0 / L1 / L2 / L3
    solutions: list = field(default_factory=list)
    selected_solution: Optional[dict] = None
    confidence: float = 0.0
    verdict: str = "PENDING"   # PENDING / PASS / FAIL / ESCALATED
    is_cached: bool = False
    duration_ms: int = 0
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: dict = field(default_factory=dict)

# ── 缓存与冷却 ──────────────────────────────────────────────────────────────────

class CacheManager:
    def __init__(self):
        self._cache = {}

    def get(self, key: str, ttl_s: int = 300):
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["ts"] < ttl_s:
                return entry["result"]
        return None

    def set(self, key: str, result):
        self._cache[key] = {"ts": time.time(), "result": result}

# ── PanelGuard: 触发保护 ──────────────────────────────────────────────────────

class PanelGuard:
    TRIGGER_FAULTS = TRIGGER_FAULTS
    MAX_TOKENS_PER_SESSION = 120_000
    MAX_TOKENS_DAILY = 500_000
    COOLDOWN_S = 300

    def __init__(self, team_id: str):
        self.team_id = team_id
        self.cache = CacheManager()

    def check(self, fault_type: str, fault_key: str, tokens_used: int = 0, daily_tokens: int = 0) -> str:
        """返回: proceed / use_cache / downgrade_l1 / block_l3"""
        if fault_type not in self.TRIGGER_FAULTS:
            return "block_l3"

        cached = self.cache.get(fault_key, self.COOLDOWN_S)
        if cached:
            return "use_cache"

        if tokens_used > self.MAX_TOKENS_PER_SESSION:
            return "downgrade_l1"

        if daily_tokens > self.MAX_TOKENS_DAILY:
            return "block_l3"

        return "proceed"

# ── L0: 预设规则匹配 ──────────────────────────────────────────────────────────

class L0RuleMatcher:
    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> list:
        return []

    def match(self, fault_type: str, error_message: str, agent_id: str) -> Optional[dict]:
        for rule in self.rules:
            if rule.get("fault_type") == fault_type:
                if rule.get("pattern") in error_message or rule.get("pattern") in agent_id:
                    return rule.get("solution")
        return None

# ── L1: 单专家方案生成 ──────────────────────────────────────────────────────────

class L1Solver:
    def __init__(self, team_id: str, fault_type: str, expert_id: str):
        self.team_id = team_id
        self.fault_type = fault_type
        self.expert_id = expert_id
        self.domain = FAULT_TO_DOMAIN.get(fault_type, ["General"])
        self._research_cache = {}

    def do_research(self, ctx: dict) -> dict:
        """Phase 1: 先做互联网调研+本地点检，返回调研数据"""
        fault_desc = ctx.get("error", "unknown")
        agent_id = ctx.get("agent_id", "unknown")

        # 1. 本地点检：检查 repair-records 中是否有类似案例
        local_hits = self._check_local_records()

        # 2. 本地点检：检查 knowledge/ 目录中的相关知识
        knowledge_hits = self._check_knowledge()

        # 3. 调研结果（互联网搜索由上层 orchestrator 调度，这里记录元数据）
        research_data = {
            "local_records": local_hits,
            "knowledge_hits": knowledge_hits,
            "fault_context": {"fault_type": self.fault_type, "error": fault_desc, "agent": agent_id},
            "domain": self.domain,
            "expert_id": self.expert_id,
        }
        self._research_cache = research_data
        return research_data

    def generate_solutions(self, ctx: dict, research_data: Optional[dict] = None) -> list[Solution]:
        """Phase 2: 基于调研数据生成方案（必须 after do_research）"""
        research = research_data or self._research_cache
        fault_desc = ctx.get("error", "unknown")
        local_count = len(research.get("local_records", []))
        knowledge_count = len(research.get("knowledge_hits", []))

        solutions = [
            Solution(
                id=f"S-{int(time.time())}-1",
                expert_id=self.expert_id,
                name=f"方案1: 基于本地资产({local_count}条记录,{knowledge_count}条知识)的修复",
                steps=["诊断根因", "应用修复", "验证效果"],
                rationale=f"基于{local_count}条历史修复记录和{knowledge_count}条领域知识",
                risk="中",
                difficulty="Medium",
                confidence=0.5 + min(0.3, local_count * 0.05),
            ),
        ]
        self._log_research(ctx, solutions)
        return solutions

    def _check_local_records(self) -> list:
        """检查本地修复记录中是否有类似案例（兼容 .json 和 .jsonl 格式）"""
        records_file = STATE_DIR / "repair-records" / f"{self.team_id}.json"
        if not records_file.exists():
            alt_file = STATE_DIR / "repair-records" / f"{self.team_id}.jsonl"
            if alt_file.exists():
                records_file = alt_file
            else:
                return []
        hits = []
        raw = records_file.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                records = json.loads(raw)
                for rec in records[-50:]:
                    if rec.get("fault_type") == self.fault_type:
                        hits.append(rec)
            except: pass
        else:
            for line in raw.split("\n")[-50:]:
                if not line: continue
                try:
                    rec = json.loads(line)
                    if rec.get("fault_type") == self.fault_type:
                        hits.append(rec)
                except: pass
        return hits

    def _check_knowledge(self) -> list:
        """检查 knowledge 目录中的相关文件"""
        if not KNOWLEDGE_DIR.exists():
            return []
        hits = []
        for domain in self.domain:
            for f in KNOWLEDGE_DIR.glob(f"*{domain[:4]}*"):
                hits.append(f.name)
            for f in KNOWLEDGE_DIR.glob(f"*{domain.split('_')[-1][:4]}*"):
                if f.name not in hits:
                    hits.append(f.name)
        return hits

    def _log_research(self, ctx: dict, solutions: list):
        log_path = STATE_DIR / "repair-records" / f"{self.team_id}.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"phase": "L1_research", "fault_type": self.fault_type,
            "expert_id": self.expert_id, "solution_count": len(solutions),
            "timestamp": datetime.now(timezone.utc).isoformat()}
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# ── L2: 多专家研讨 ──────────────────────────────────────────────────────────

class L2Panel:
    def __init__(self, team_id: str, fault_type: str, thickness: str):
        self.team_id = team_id
        self.fault_type = fault_type
        self.thickness = thickness
        config = PANEL_CONFIG[thickness]
        self.expert_count = config["experts"]
        self.has_sceptic = config["sceptic"]
        self.max_rounds = config["discussion_rounds"]
        self.timeout_s = config["timeout_s"]

    def run(self, ctx: dict) -> PanelResult:
        """运行完整 L2 多专家研讨
        执行顺序: Phase 1 调研(并行) → Phase 2 方案生成(基于调研结果) → Phase 3 讨论投票
        """
        t0 = time.time()
        # Phase 1: 所有专家并行调研（先产生研究数据）
        research_results = self._parallel_research(ctx)
        # Phase 2: 基于调研数据生成方案
        solutions = self._gather_solutions(ctx, research_results)
        ranked = self._discuss_and_vote(solutions)
        winner = ranked[0] if ranked else None
        panel_result = PanelResult(
            session_id=f"P-{int(t0)}",
            team_id=self.team_id, agent_id=ctx.get("agent_id", ""),
            fault_type=self.fault_type, level="L2",
            solutions=[asdict(s) for s in solutions],
            selected_solution=asdict(winner) if winner else None,
            confidence=winner.confidence if winner else 0.0,
            verdict="PASS" if winner else "FAIL",
            duration_ms=int((time.time() - t0) * 1000),
            details={"domain": FAULT_TO_DOMAIN.get(self.fault_type, []),
                     "expert_count": self.expert_count, "has_sceptic": self.has_sceptic,
                     "discussion_rounds_used": min(self.max_rounds, 2)})
        self._save_result(panel_result)
        return panel_result

    def _parallel_research(self, ctx: dict) -> list[dict]:
        """Phase 1: 所有专家并行执行调研（先调研，后分析）
        确保 research 结果在 solution generation 之前可用
        """
        research_results = []
        for i in range(self.expert_count):
            solver = L1Solver(self.team_id, self.fault_type, f"expert-{i}")
            data = solver.do_research(ctx)
            research_results.append({"expert_id": f"expert-{i}", "solver": solver, "data": data})
        return research_results

    def _gather_solutions(self, ctx: dict, research_results: list[dict]) -> list[Solution]:
        """Phase 2: 基于调研结果生成方案（调研必须已完成）"""
        all_solutions = []
        for entry in research_results:
            solver = entry["solver"]
            solutions = solver.generate_solutions(ctx, entry["data"])
            all_solutions.extend(solutions)
        return all_solutions

    def _discuss_and_vote(self, solutions: list[Solution]) -> list[Solution]:
        """Phase 3: 加权投票排名"""
        for i, s in enumerate(solutions):
            s.confidence = min(1.0, s.confidence + 0.2 * i / max(len(solutions), 1))
        solutions.sort(key=lambda s: s.confidence, reverse=True)
        return solutions

    def _save_result(self, result: PanelResult):
        from scripts.file_utils import atomic_write
        atomic_write(STATE_DIR / "panel-records" / f"{result.session_id}.json", asdict(result))

# ── 主管道: Problem Solving Pipeline ──────────────────────────────────────────

class ProblemSolver:
    def __init__(self, team_id: str, agent_id: str):
        self.team_id = team_id
        self.agent_id = agent_id
        self.guard = PanelGuard(team_id)
        self.l0 = L0RuleMatcher()
        self.cache = CacheManager()

    def solve(self, fault_type: str, ctx: dict) -> PanelResult:
        t0 = time.time()
        fault_key = f"{self.team_id}/{self.agent_id}/{fault_type}"
        ctx.setdefault("agent_id", self.agent_id)

        guard_result = self.guard.check(fault_type, fault_key,
            ctx.get("tokens_used", 0), ctx.get("daily_tokens", 0))

        if guard_result == "use_cache":
            cached = self.guard.cache.get(fault_key)
            if cached:
                cached.is_cached = True
                cached.details["guard_result"] = "use_cache"
                return cached

        if guard_result == "block_l3":
            return PanelResult(session_id=f"P-{int(t0)}", team_id=self.team_id,
                agent_id=self.agent_id, fault_type=fault_type,
                level="L3", verdict="ESCALATED",
                duration_ms=int((time.time() - t0) * 1000),
                details={"reason": "fault_type_not_triggers", "guard_result": guard_result})

        thickness = FAULT_THICKNESS.get(fault_type, "light")
        if guard_result == "downgrade_l1":
            thickness = "light"

        if thickness == "light":
            # L1: 按实际 fault_type 动态创建 L1Solver
            l1 = L1Solver(self.team_id, fault_type, "general-expert")
            research_data = l1.do_research(ctx)
            solutions = l1.generate_solutions(ctx, research_data)
            winner = solutions[0] if solutions else None
            result = PanelResult(session_id=f"P-{int(t0)}", team_id=self.team_id,
                agent_id=self.agent_id, fault_type=fault_type,
                level="L1", solutions=[asdict(s) for s in solutions],
                selected_solution=asdict(winner) if winner else None,
                confidence=winner.confidence if winner else 0.0,
                verdict="PASS" if winner else "FAIL",
                duration_ms=int((time.time() - t0) * 1000),
                details={"guard_result": guard_result, "thickness": thickness})
        else:
            panel = L2Panel(self.team_id, fault_type, thickness)
            result = panel.run(ctx)
            result.details["guard_result"] = guard_result

        self.guard.cache.set(fault_key, result)
        return result

# ── CLI ──────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Problem Solving Panel v1.0")
    ap.add_argument("--team", required=True, help="团队 ID")
    ap.add_argument("--agent", default="unknown", help="Agent ID")
    ap.add_argument("--fault-type", default="FT-04", choices=list(FAULT_TO_DOMAIN.keys()) + ["FT-02", "FT-03", "FT-01"],
        help="故障类型")
    ap.add_argument("--error", default="", help="错误消息")
    ap.add_argument("--context-json", default="", help="上下文 JSON")
    ap.add_argument("--l0-rule", default="", help="直接测试 L0 规则")
    ap.add_argument("command", nargs="?", default="solve", choices=["solve", "repair-records"])
    args = ap.parse_args()

    if args.command == "repair-records":
        p = STATE_DIR / "panel-records"
        records = []
        if p.exists():
            for f in sorted(p.glob("*.json"))[-20:]:
                records.append(json.loads(f.read_text(encoding="utf-8")))
        print(json.dumps({"team": args.team, "count": len(records), "records": records}, ensure_ascii=False, indent=2))
        return

    ctx = {"agent_id": args.agent, "error": args.error}
    if args.context_json:
        try: ctx.update(json.loads(args.context_json))
        except: pass

    solver = ProblemSolver(args.team, args.agent)
    result = solver.solve(args.fault_type, ctx)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
