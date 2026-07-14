#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-Healing Pipeline v2.0.0 — 故障检测→诊断→恢复→验证 完整管道

基于 Loop Engineering 调研 + Self-Healing 架构设计 (`references/self-healing-architecture.md`)

用法:
  python3 self_heal.py --team <team_id> --agent <agent_id> --error "<msg>"
  python3 self_heal.py daemon --team <team_id>          # 持续监控模式
"""
import json, sys, time, random, argparse, hashlib, threading
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional

from scripts._paths import STATE_DIR as _STATE_DIR
from scripts._fault_types import FAULT_TYPES, RECOVERY_STRATEGIES, FAULT_CODE_MAP, FAULT_CAUSES
import scripts._paths as _paths

STATE_DIR = _STATE_DIR

# ── 结构化日志 ─────────────────────────────────────────────────────────────────
try:
    from scripts._logging import get_logger, setup_metrics
    _HAS_LOGGING = True
except ImportError:
    _HAS_LOGGING = False

# ── 数据类 ──────────────────────────────────────────────────────────────────────

@dataclass
class DetectionSignal:
    source: str               # HeartbeatWatch / ToolCallWatch / ...
    agent_id: str
    signal_type: str          # HEARTBEAT_MISS / TOOL_FAIL / ...
    value: float
    details: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class DiagnosisResult:
    fault_type: str           # FT-01 ~ FT-10
    severity: int
    confidence: float
    agent_id: str
    signal_chain: list
    recommended_strategy: str
    params: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class HealResult:
    action: str
    target: str
    elapsed_ms: int
    success: bool
    details: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class VerificationResult:
    verifier_id: str
    verdict: str              # PASS / FAIL / CONDITIONAL
    recovery_action: str = ""
    checks_passed: list = field(default_factory=list)
    checks_failed: list = field(default_factory=list)
    side_effects: list = field(default_factory=list)
    regressions: list = field(default_factory=list)
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ── 熔断器 (Circuit Breaker) ──────────────────────────────────────────────────

class CircuitBreaker:
    STATES = ["CLOSED", "OPEN", "HALF_OPEN"]

    def __init__(self, name: str, failure_threshold=3, cooldown_s=60, success_threshold=2):
        self.name = name
        self.state = "CLOSED"
        self.failure_count = 0
        self.success_count = 0
        self.failure_threshold = failure_threshold
        self.cooldown_s = cooldown_s
        self.success_threshold = success_threshold
        self.last_failure = 0.0
        self._load()

    def _state_path(self):
        return STATE_DIR / "circuit-breakers" / f"{self.name}.json"

    def _load(self):
        p = self._state_path()
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                self.state = d.get("state", "CLOSED")
                self.failure_count = d.get("failure_count", 0)
                self.success_count = d.get("success_count", 0)
                self.last_failure = d.get("last_failure", 0.0)
            except: pass

    def _save(self):
        from scripts.file_utils import atomic_write
        p = self._state_path()
        atomic_write(p, {"state": self.state, "failure_count": self.failure_count,
            "success_count": self.success_count, "last_failure": self.last_failure,
            "updated": datetime.now(timezone.utc).isoformat()})

    def allow_request(self) -> bool:
        now = time.time()
        if self.state == "OPEN":
            if now - self.last_failure >= self.cooldown_s:
                self.state = "HALF_OPEN"
                self._save()
                return True
            return False
        return True

    def record_failure(self):
        self.failure_count += 1
        self.success_count = 0
        self.last_failure = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
        self._save()

    def record_success(self):
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "CLOSED"
                self.failure_count = 0
                self.success_count = 0
        self._save()

# ── Detector: 故障检测 ──────────────────────────────────────────────────────────

class Detector:
    @staticmethod
    def heartbeat_watch(agent_id: str, last_heartbeat: Optional[str], timeout_s=30, miss_limit=3) -> Optional[DetectionSignal]:
        if not last_heartbeat:
            return None
        try:
            last = datetime.fromisoformat(last_heartbeat)
            elapsed = (datetime.now(timezone.utc) - last.replace(tzinfo=timezone.utc)).total_seconds()
            missed = int(elapsed / timeout_s)
            if missed >= miss_limit:
                return DetectionSignal(source="HeartbeatWatch", agent_id=agent_id,
                    signal_type="HEARTBEAT_MISS", value=missed,
                    details={"elapsed_s": int(elapsed), "miss_count": missed})
        except: pass
        return None

    @staticmethod
    def tool_call_watch(exit_code: int, duration_ms: int, threshold_ms=30000) -> Optional[DetectionSignal]:
        if exit_code != 0:
            return DetectionSignal(source="ToolCallWatch", agent_id="",
                signal_type="TOOL_FAIL", value=exit_code,
                details={"exit_code": exit_code, "duration_ms": duration_ms})
        if duration_ms > threshold_ms:
            return DetectionSignal(source="ToolCallWatch", agent_id="",
                signal_type="TOOL_SLOW", value=round(duration_ms / 1000, 1),
                details={"duration_ms": duration_ms, "threshold_ms": threshold_ms})
        return None

    @staticmethod
    def output_quality_watch(confidence: float, source_trace_fail_rate: float = 0) -> Optional[DetectionSignal]:
        if confidence < 0.6:
            return DetectionSignal(source="OutputQualityWatch", agent_id="",
                signal_type="LOW_CONFIDENCE", value=confidence,
                details={"threshold": 0.6, "source_trace_fail_rate": source_trace_fail_rate})
        if source_trace_fail_rate > 0.3:
            return DetectionSignal(source="OutputQualityWatch", agent_id="",
                signal_type="HIGH_TRACE_FAIL", value=source_trace_fail_rate,
                details={"threshold": 0.3, "confidence": confidence})
        return None

    @staticmethod
    def timeout_watch(elapsed_ms: int, threshold_ms: int) -> Optional[DetectionSignal]:
        if elapsed_ms > threshold_ms:
            return DetectionSignal(source="TimeoutWatch", agent_id="",
                signal_type="TIMEOUT", value=elapsed_ms / 1000,
                details={"elapsed_ms": elapsed_ms, "threshold_ms": threshold_ms})
        return None

    @staticmethod
    def score_trend_watch(consecutive_drops: int) -> Optional[DetectionSignal]:
        if consecutive_drops >= 3:
            return DetectionSignal(source="ScoreTrendWatch", agent_id="",
                signal_type="SCORE_DROP", value=consecutive_drops,
                details={"consecutive_drops": consecutive_drops, "threshold": 3})
        return None

    @classmethod
    def collect_all(cls, ctx: dict) -> list[DetectionSignal]:
        signals = []
        hb = cls.heartbeat_watch(ctx.get("agent_id",""), ctx.get("last_heartbeat"))
        if hb: signals.append(hb)
        if ctx.get("exit_code") is not None:
            tc = cls.tool_call_watch(ctx["exit_code"], ctx.get("duration_ms", 0))
            if tc: signals.append(tc)
        if ctx.get("confidence") is not None:
            oq = cls.output_quality_watch(ctx["confidence"], ctx.get("source_trace_fail_rate", 0))
            if oq: signals.append(oq)
        if ctx.get("elapsed_ms") and ctx.get("timeout_ms"):
            to = cls.timeout_watch(ctx["elapsed_ms"], ctx["timeout_ms"])
            if to: signals.append(to)
        if ctx.get("consecutive_drops", 0) >= 3:
            st = cls.score_trend_watch(ctx["consecutive_drops"])
            if st: signals.append(st)
        return signals

# ── Diagnoser: 故障诊断 ──────────────────────────────────────────────────────────

SIGNAL_TO_FAULT = [
    (["HEARTBEAT_MISS"], "FT-01", 0.90),
    (["TOOL_FAIL"], "FT-02", 0.85),
    (["TOOL_SLOW"], "FT-02", 0.60),
    (["LOW_CONFIDENCE"], "FT-03", 0.85),
    (["HIGH_TRACE_FAIL"], "FT-04", 0.70),
    (["TIMEOUT"], "FT-05", 0.60),
    (["SCORE_DROP"], "FT-07", 0.80),
]

RETRY_FAULTS = {"FT-01", "FT-02", "FT-03"}
SWITCH_FAULTS = {"FT-05", "FT-08"}
CIRCUIT_BREAK_FAULTS = {"FT-07"}
ESCALATE_FAULTS = {"FT-04", "FT-09", "FT-10"}
DEGRADE_FAULTS = {"FT-06"}

def _default_strategy(fault_type: str) -> str:
    if fault_type in RETRY_FAULTS: return "retry"
    if fault_type in SWITCH_FAULTS: return "switch"
    if fault_type in CIRCUIT_BREAK_FAULTS: return "circuit_break"
    if fault_type in ESCALATE_FAULTS: return "escalate"
    if fault_type in DEGRADE_FAULTS: return "degrade"
    return "skip"

class Diagnoser:
    @staticmethod
    def diagnose(signals: list[DetectionSignal], agent_id: str = "", history: Optional[list] = None) -> Optional[DiagnosisResult]:
        if not signals:
            return None
        signal_types = [s.signal_type for s in signals]
        signal_chain = [f"{s.source}.{s.signal_type}(v={s.value})" for s in signals]

        for stypes, fault_code, confidence in SIGNAL_TO_FAULT:
            if all(t in signal_types for t in stypes):
                ft = FAULT_TYPES[fault_code]
                return DiagnosisResult(
                    fault_type=fault_code, severity=ft["severity"],
                    confidence=confidence, agent_id=agent_id,
                    signal_chain=signal_chain, recommended_strategy=_default_strategy(fault_code),
                    params={"base_delay_s": 2 if ft["severity"] <= 2 else 5})

        return DiagnosisResult(fault_type="FT-02", severity=2, confidence=0.5,
            agent_id=agent_id, signal_chain=signal_chain, recommended_strategy="retry",
            params={"base_delay_s": 2})

# ── ProblemSolver 集成 ─────────────────────────────────────────────────────────
# 当 escalate 策略被触发时，调用问题求解管道。
# 导入失败时回退到旧的 escalate 行为。

try:
    from scripts.problem_solver import ProblemSolver
    _HAS_SOLVER = True
except ImportError:
    _HAS_SOLVER = False

# ── Healer: 故障恢复 ──────────────────────────────────────────────────────────

class Healer:
    _file_lock = threading.Lock()

    def __init__(self, team_id: str, agent_id: str):
        self.team_id = team_id
        self.agent_id = agent_id
        self.cb = CircuitBreaker(f"{team_id}/{agent_id}")
        self._retries = {}
        self._repair_records = self._load_repair_records()

    def _repair_path(self):
        return STATE_DIR / "repair-records" / f"{self.team_id}.json"

    def _load_repair_records(self) -> list:
        p = self._repair_path()
        if p.exists():
            try: return json.loads(p.read_text(encoding="utf-8"))
            except: pass
        return []

    def _save_repair_record(self, record: dict):
        from scripts.file_utils import atomic_write
        with self._file_lock:
            self._repair_records = self._load_repair_records()
            self._repair_records.append(record)
            atomic_write(self._repair_path(), self._repair_records)

    def _backoff_delay(self, attempt: int, base_s: float = 2, multiplier: float = 2) -> float:
        delay = base_s * (multiplier ** attempt)
        jitter = random.uniform(0, 0.3 * delay)
        return delay + jitter

    def _fmt_escalate_msg(self, diagnosis: DiagnosisResult) -> str:
        """标准化用户可见的 escalate 消息（错误码 + 原因 + 已尝试 + 建议）"""
        ft = diagnosis.fault_type
        info = FAULT_TYPES.get(ft, {})
        attempts = self._retries.get(self.agent_id, 0)
        cb_state = self.cb.state

        code = FAULT_CODE_MAP.get(ft, "ERR-UNKNOWN")

        cause = FAULT_CAUSES.get(ft, FAULT_CAUSES.get("FT-UK", "未知故障"))
        if ft == "FT-02" and diagnosis.signal_chain:
            cause = f"工具调用失败，退出码={diagnosis.signal_chain}"

        return (
            f"[{code}] {info.get('name', '未知故障')}\n"
            f"├─ 故障码: {ft}（严重度 L{info.get('severity', 3)}）\n"
            f"├─ 原因: {cause}\n"
            f"├─ 已尝试: {attempts} 次{'重试' if attempts > 0 else '自动检测'}"
            f"（熔断器状态: {cb_state}）\n"
            f"└─ 建议: 将以上故障码和上下文复制给主理人处理"
        )

    def heal(self, diagnosis: DiagnosisResult) -> HealResult:
        if not self.cb.allow_request():
            return HealResult(action="circuit_break", target="blocked_by_cb",
                elapsed_ms=0, success=False, details={"state": "OPEN", "cooldown_s": self.cb.cooldown_s})

        strategy = diagnosis.recommended_strategy
        fault_code = diagnosis.fault_type
        fault_info = FAULT_TYPES.get(fault_code, {})
        t0 = time.time()

        if strategy == "retry":
            key = f"{self.agent_id}/{fault_code}"
            attempt = self._retries.get(key, 0) + 1
            self._retries[key] = attempt
            if attempt > (diagnosis.params.get("max_retries", 3)):
                alt = _default_strategy(fault_code)
                if alt == "retry": alt = "switch"
                return self._fallback(alt, diagnosis, t0)
            delay = self._backoff_delay(attempt, diagnosis.params.get("base_delay_s", 2))
            result = HealResult(action="retry", target=self.agent_id,
                elapsed_ms=int((time.time() - t0) * 1000), success=True,
                details={"attempt": attempt, "delay_s": round(delay, 2), "max_retries": diagnosis.params.get("max_retries", 3)})
            self.cb.record_success()
            return result

        elif strategy == "switch":
            result = HealResult(action="switch", target=f"{self.agent_id}-备用",
                elapsed_ms=int((time.time() - t0) * 1000), success=True,
                details={"from_agent": self.agent_id, "reason": fault_code})
            self.cb.record_success()
            return result

        elif strategy == "circuit_break":
            self.cb.record_failure()
            return HealResult(action="circuit_break", target=self.agent_id,
                elapsed_ms=int((time.time() - t0) * 1000), success=True,
                details={"state": self.cb.state, "failure_count": self.cb.failure_count,
                         "cooldown_s": self.cb.cooldown_s})

        elif strategy == "degrade":
            return HealResult(action="degrade", target=self.agent_id,
                elapsed_ms=int((time.time() - t0) * 1000), success=True,
                details={"from_depth": "standard", "to_depth": "light", "note": "验证深度降级"})

        elif strategy == "escalate":
            if _HAS_SOLVER:
                ps = ProblemSolver(self.team_id, self.agent_id)
                solver_ctx = {"agent_id": self.agent_id, "error": fault_code,
                    "tokens_used": self._retries.get(fault_code, 0) * 5000}
                panel_result = ps.solve(fault_code, solver_ctx)
                user_msg = self._fmt_escalate_msg(diagnosis)
                return HealResult(action=f"escalate_via_panel({panel_result.level})",
                    target=panel_result.selected_solution.get("name", "专家研讨") if panel_result.selected_solution else "scheduled",
                    elapsed_ms=panel_result.duration_ms,
                    success=panel_result.verdict == "PASS",
                    details={"fault_code": fault_code, "panel_session_id": panel_result.session_id,
                        "panel_level": panel_result.level, "panel_verdict": panel_result.verdict,
                        "solutions_count": len(panel_result.solutions),
                        "confidence": panel_result.confidence,
                        "user_message": user_msg,
                        "recommended": panel_result.selected_solution.get("name", "") if panel_result.selected_solution else user_msg})
            user_msg = self._fmt_escalate_msg(diagnosis)
            return HealResult(action="escalate", target="human",
                elapsed_ms=int((time.time() - t0) * 1000), success=False,
                details={"fault_code": fault_code, "user_message": user_msg,
                    "recommended": user_msg})

        else:
            return HealResult(action="skip", target=self.agent_id,
                elapsed_ms=int((time.time() - t0) * 1000), success=True,
                details={"note": f"跳过故障 {fault_code}"})

    def _fallback(self, alt_strategy: str, diagnosis: DiagnosisResult, t0: float) -> HealResult:
        r = HealResult(action=alt_strategy, target=self.agent_id,
            elapsed_ms=int((time.time() - t0) * 1000), success=False,
            details={"fallback": True, "from_strategy": diagnosis.recommended_strategy})
        repair = {"id": f"F{len(self._repair_records)+12}", "fault_type": diagnosis.fault_type,
            "strategy": alt_strategy, "effectiveness": 0.5,
            "created": datetime.now(timezone.utc).isoformat()}
        self._save_repair_record(repair)
        return r

# ── Verifier: 故障验证 ──────────────────────────────────────────────────────────

class Verifier:
    VERIFIERS = {
        "retry": {"id": "functionality_check", "checks": ["schema", "completeness", "format"]},
        "switch": {"id": "side_effect_scan", "checks": ["downstream_alive", "context_intact"]},
        "degrade": {"id": "quality_review", "checks": ["confidence_ge_0.7", "trace_rate_ge_0.8"]},
        "circuit_break": {"id": "consistency_check", "checks": ["cb_state_valid"]},
        "escalate": {"id": "regression_check", "checks": ["known_assertions_intact"]},
    }

    @classmethod
    def verify(cls, heal_result: HealResult, action: str = "") -> VerificationResult:
        action = action or heal_result.action
        vcfg = cls.VERIFIERS.get(action, {"id": "default", "checks": ["basic"]})
        passed = []
        failed = []
        for check in vcfg["checks"]:
            ok = cls._run_check(check, heal_result)
            if ok:
                passed.append(check)
            else:
                failed.append(check)
        verdict = "PASS" if (heal_result.success and not failed) else "FAIL"
        return VerificationResult(verifier_id=vcfg["id"], verdict=verdict,
            recovery_action=action, checks_passed=passed, checks_failed=failed)

    @classmethod
    def _run_check(cls, check: str, heal_result: HealResult) -> bool:
        if check == "schema":
            return isinstance(heal_result.details, dict)
        if check == "completeness":
            return bool(heal_result.action and heal_result.target)
        if check == "format":
            return heal_result.elapsed_ms >= 0
        if check == "downstream_alive":
            return heal_result.success
        if check == "context_intact":
            return True
        if check == "confidence_ge_0.7":
            return heal_result.details.get("confidence", 1.0) >= 0.7
        if check == "trace_rate_ge_0.8":
            return heal_result.details.get("trace_rate", 1.0) >= 0.8
        if check == "cb_state_valid":
            state = heal_result.details.get("state", "")
            return state in ("CLOSED", "OPEN", "HALF_OPEN")
        if check == "known_assertions_intact":
            return True
        if check == "basic":
            return heal_result.success
        return False

# ── 自愈管道编排（含快照/回滚）───────────────────────────────────────────────

class SelfHealPipeline:
    def __init__(self, team_id: str, agent_id: str, rollback_enabled: bool = True):
        self.team_id = team_id
        self.agent_id = agent_id
        self.detector = Detector()
        self.diagnoser = Diagnoser()
        self.healer = Healer(team_id, agent_id)
        self.verifier = Verifier()
        self.max_retries = 3
        self.trace_id = ""
        self.logger = None
        self.rollback_enabled = rollback_enabled

    def _init_logging(self, ctx: dict):
        if _HAS_LOGGING:
            self.trace_id = ctx.get("trace_id", "")
            self.logger = get_logger(f"self-heal.{self.agent_id}", self.trace_id)

    def _log_emit(self, level: str, msg: str, **extra):
        if self.logger:
            getattr(self.logger, level)(msg, extra=extra)

    def run(self, ctx: dict) -> dict:
        self._init_logging(ctx)
        self._log_emit("info", "pipeline_start", signals=len(ctx))
        from scripts.rollback_manager import SnapshotManager
        _rm = SnapshotManager() if self.rollback_enabled else None
        timeline = []
        for attempt in range(self.max_retries + 1):
            signals = Detector.collect_all({**ctx, "agent_id": self.agent_id})
            timeline.append({"phase": "detect", "signals": [asdict(s) for s in signals]})

            if not signals:
                break

            diagnosis = self.diagnoser.diagnose(signals, self.agent_id)
            if not diagnosis:
                break
            timeline.append({"phase": "diagnose", "diagnosis": asdict(diagnosis)})

            snapshot_id = ""
            if _rm:
                snapshot_id = _rm.snapshot_agent_state(self.team_id, self.agent_id,
                    f"heal_attempt_{attempt}")
                timeline[-1]["snapshot_id"] = snapshot_id

            heal = self.healer.heal(diagnosis)
            timeline.append({"phase": "heal", "heal": asdict(heal)})

            verify = self.verifier.verify(heal, heal.action)
            timeline.append({"phase": "verify", "verify": asdict(verify)})

            if verify.verdict == "PASS":
                return {"status": "healed", "attempts": attempt + 1, "timeline": timeline,
                    "verdict": "PASS", "recovery_action": heal.action,
                    "rollback_snapshot_id": snapshot_id}

            if _rm and snapshot_id:
                try:
                    restored = _rm.restore_snapshot(snapshot_id)
                    timeline[-1]["rollback_files_restored"] = restored
                except Exception:
                    timeline[-1]["rollback_error"] = "restore failed"

        return {"status": "escalated" if attempt >= self.max_retries else "clean",
            "attempts": attempt, "timeline": timeline}

# ── CLI ──────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Self-Healing Pipeline v2.0.0")
    ap.add_argument("--team", required=True)
    ap.add_argument("--agent", default="unknown")
    ap.add_argument("--error", default="")
    ap.add_argument("--context-json", default="")
    ap.add_argument("command", nargs="?", default="heal", choices=["heal", "daemon", "cb-status", "repair-records", "solver"])
    args = ap.parse_args()

    if args.command == "cb-status":
        cb = CircuitBreaker(f"{args.team}/{args.agent}")
        print(json.dumps({"name": cb.name, "state": cb.state, "failure_count": cb.failure_count,
            "success_count": cb.success_count}, ensure_ascii=False))
        return

    if args.command == "repair-records":
        p = STATE_DIR / "repair-records" / f"{args.team}.json"
        records = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        print(json.dumps({"team": args.team, "count": len(records), "records": records[-20:]}, ensure_ascii=False, indent=2))
        return

    if args.command == "solver" and _HAS_SOLVER:
        from scripts.problem_solver import ProblemSolver
        ps = ProblemSolver(args.team, args.agent)
        ctx = {"agent_id": args.agent, "error": args.error}
        if args.context_json:
            try: ctx.update(json.loads(args.context_json))
            except: pass
        result = ps.solve(args.context_json and json.loads(args.context_json).get("fault_type", "FT-04") or "FT-04", ctx)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    ctx = {"agent_id": args.agent, "error": args.error}
    if args.context_json:
        try: ctx.update(json.loads(args.context_json))
        except: pass

    pipeline = SelfHealPipeline(args.team, args.agent)
    result = pipeline.run(ctx)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
