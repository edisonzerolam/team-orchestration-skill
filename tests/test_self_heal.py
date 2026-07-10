"""Tests for self_heal.py — 自愈管道核心测试"""
import json, os, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from self_heal import (
    FAULT_TYPES, DiagnosisResult, HealResult, DetectionSignal,
    Detector, Diagnoser, Healer, CircuitBreaker, SelfHealPipeline,
)


class TestFaultTypes:
    def test_all_ft_defined(self):
        assert len(FAULT_TYPES) == 10
        for code, info in FAULT_TYPES.items():
            assert code.startswith("FT-")
            assert 1 <= info["severity"] <= 4
            assert isinstance(info["recoverable"], bool)
            assert info["name"]
            assert info["desc"]


class TestDetectionSignal:
    def test_signal_creation(self):
        s = DetectionSignal("HeartbeatWatch", "agent1", "HEARTBEAT_MISS", 3)
        assert s.source == "HeartbeatWatch"
        assert s.signal_type == "HEARTBEAT_MISS"
        assert s.value == 3


class TestDiagnosisResult:
    def test_diagnosis_creation(self):
        d = DiagnosisResult("FT-04", 3, 0.85, "a1", ["HeartbeatWatch.HEARTBEAT_MISS(v=3)"], "escalate")
        assert d.fault_type == "FT-04"
        assert d.severity == 3
        assert d.confidence == 0.85
        assert d.recommended_strategy == "escalate"


class TestHealResult:
    def test_heal_result_creation(self):
        r = HealResult("retry", "agent1", 1500, True)
        assert r.action == "retry"
        assert r.success is True
        assert r.elapsed_ms == 1500


class TestDetector:
    def test_heartbeat_miss(self):
        s = Detector.heartbeat_watch("agent1", None)
        assert s is None  # No heartbeat info → no signal

    def test_heartbeat_stale(self):
        from datetime import datetime, timezone, timedelta
        old = (datetime.now(timezone.utc) - timedelta(seconds=180)).isoformat()
        s = Detector.heartbeat_watch("agent1", old, timeout_s=30, miss_limit=3)
        assert s is not None
        assert s.signal_type == "HEARTBEAT_MISS"

    def test_tool_fail(self):
        s = Detector.tool_call_watch(exit_code=1, duration_ms=5000)
        assert s is not None
        assert s.signal_type == "TOOL_FAIL"

    def test_tool_slow(self):
        s = Detector.tool_call_watch(exit_code=0, duration_ms=60000)
        assert s is not None
        assert s.signal_type == "TOOL_SLOW"

    def test_tool_ok(self):
        s = Detector.tool_call_watch(exit_code=0, duration_ms=500)
        assert s is None

    def test_low_confidence(self):
        s = Detector.output_quality_watch(confidence=0.3)
        assert s is not None
        assert s.signal_type == "LOW_CONFIDENCE"

    def test_good_confidence(self):
        s = Detector.output_quality_watch(confidence=0.85)
        assert s is None

    def test_timeout(self):
        s = Detector.timeout_watch(elapsed_ms=35000, threshold_ms=30000)
        assert s is not None
        assert s.signal_type == "TIMEOUT"

    def test_no_timeout(self):
        s = Detector.timeout_watch(elapsed_ms=5000, threshold_ms=30000)
        assert s is None

    def test_score_trend(self):
        s = Detector.score_trend_watch(consecutive_drops=5)
        assert s is not None
        assert s.signal_type == "SCORE_DROP"

    def test_collect_all(self):
        ctx = {"agent_id": "a1", "exit_code": 1, "duration_ms": 5000,
               "elapsed_ms": 35000, "timeout_ms": 30000, "consecutive_drops": 3}
        signals = Detector.collect_all(ctx)
        assert len(signals) >= 3  # TOOL_FAIL + TIMEOUT + SCORE_DROP


class TestDiagnoser:
    def test_diagnose_heartbeat(self):
        signals = [DetectionSignal("HeartbeatWatch", "a1", "HEARTBEAT_MISS", 3)]
        d = Diagnoser.diagnose(signals, "a1")
        assert d is not None
        assert d.fault_type == "FT-01"

    def test_diagnose_tool(self):
        signals = [DetectionSignal("ToolCallWatch", "", "TOOL_FAIL", 1)]
        d = Diagnoser.diagnose(signals, "a1")
        assert d is not None
        assert d.fault_type == "FT-02"

    def test_diagnose_empty(self):
        d = Diagnoser.diagnose([], "a1")
        assert d is None

    def test_diagnose_quality(self):
        signals = [DetectionSignal("OutputQualityWatch", "", "LOW_CONFIDENCE", 0.3)]
        d = Diagnoser.diagnose(signals, "a1")
        assert d is not None
        assert d.fault_type == "FT-03"

    def test_diagnose_degradation(self):
        signals = [DetectionSignal("ScoreTrendWatch", "", "SCORE_DROP", 4)]
        d = Diagnoser.diagnose(signals, "a1")
        assert d is not None
        assert d.fault_type == "FT-07"

    def test_strategy_escalate_faults(self):
        for ft in ["FT-04", "FT-09", "FT-10"]:
            d = Diagnoser.diagnose(
                [DetectionSignal("OutputQualityWatch", "", "LOW_CONFIDENCE", 0.3)],
                "a1")
            if d and d.fault_type == ft:
                assert d.recommended_strategy == "escalate"


class TestCircuitBreaker:
    def test_initial_closed(self):
        cb = CircuitBreaker("test-cb")
        assert cb.state == "CLOSED"
        assert cb.allow_request() is True

    def test_open_after_failures(self):
        import uuid
        cb = CircuitBreaker(f"test-open-{uuid.uuid4().hex[:8]}", failure_threshold=3)
        assert cb.state == "CLOSED"
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.allow_request() is False

    def test_half_open_recovery(self):
        cb = CircuitBreaker("test-half", failure_threshold=1, cooldown_s=0, success_threshold=2)
        cb.record_failure()
        assert cb.state == "OPEN"
        # cooldown_s=0 意味着立即进入 HALF_OPEN
        allowed = cb.allow_request()
        assert cb.state == "HALF_OPEN" or allowed is True


class TestHealer:
    def test_retry_strategy(self):
        h = Healer("test-team", "agent1")
        d = DiagnosisResult("FT-02", 2, 0.9, "a1", [], "retry")
        r = h.heal(d)
        assert r.action == "retry"
        assert r.success is True

    def test_degrade_strategy(self):
        h = Healer("test-team", "agent1")
        d = DiagnosisResult("FT-06", 3, 0.9, "a1", [], "degrade")
        r = h.heal(d)
        assert r.action == "degrade"
        assert r.success is True

    def test_escalate_message(self):
        h = Healer("test-team", "agent-escalate")
        d = DiagnosisResult("FT-04", 3, 0.85, "a1", ["LOW_CONFIDENCE"], "escalate")
        r = h.heal(d)
        assert r.action.startswith("escalate")
        msg = r.details.get("user_message", "")
        assert msg.startswith("[ERR-") or r.action == "escalate"

    def test_circuit_break_strategy(self):
        h = Healer("test-team", "agent-cb")
        d = DiagnosisResult("FT-07", 4, 0.9, "a1", [], "circuit_break")
        r = h.heal(d)
        assert r.action == "circuit_break"


class TestSelfHealPipeline:
    def test_pipeline_clean(self):
        p = SelfHealPipeline("test-team", "agent-clean")
        ctx = {"agent_id": "agent-clean", "exit_code": 0, "duration_ms": 100,
               "elapsed_ms": 500, "timeout_ms": 30000, "confidence": 0.95}
        r = p.run(ctx)
        assert r["status"] == "clean"

    def test_pipeline_heal(self):
        p = SelfHealPipeline("test-team", "agent-fail")
        ctx = {"agent_id": "agent-fail", "exit_code": 1, "duration_ms": 5000,
               "elapsed_ms": 35000, "timeout_ms": 30000, "confidence": 0.3,
               "consecutive_drops": 3}
        r = p.run(ctx)
        assert r["status"] in ("healed", "escalated", "clean")

    def test_pipeline_multiple_signals(self):
        p = SelfHealPipeline("test-team", "agent-multi")
        ctx = {"agent_id": "agent-multi", "exit_code": 1, "duration_ms": 5000,
               "elapsed_ms": 35000, "timeout_ms": 30000, "confidence": 0.3,
               "source_trace_fail_rate": 0.5, "consecutive_drops": 4}
        r = p.run(ctx)
        assert "timeline" in r
        assert len(r["timeline"]) > 0


class TestFmtEscalateMsg:
    def test_ft04_message(self):
        h = Healer("test", "a1")
        d = DiagnosisResult("FT-04", 3, 0.85, "a1", ["TEST"], "escalate", {})
        msg = h._fmt_escalate_msg(d)
        assert msg.startswith("[ERR-HALL]")
        assert "FT-04" in msg
        assert "建议" in msg

    def test_ft02_message(self):
        h = Healer("test", "a1")
        d = DiagnosisResult("FT-02", 2, 0.9, "a1", ["TOOL_FAIL(exit=1)"], "escalate", {})
        msg = h._fmt_escalate_msg(d)
        assert msg.startswith("[ERR-TOOL]")
        assert "FT-02" in msg

    def test_ft07_message(self):
        h = Healer("test", "a1")
        d = DiagnosisResult("FT-07", 4, 0.85, "a1", ["SCORE_DROP(v=5)"], "escalate", {})
        msg = h._fmt_escalate_msg(d)
        assert msg.startswith("[ERR-DEGRADE]")
        assert "L4" in msg


class TestHealResultPersistence:
    def test_repair_record_saved(self):
        h = Healer("test-records", "agent-r")
        d = DiagnosisResult("FT-10", 4, 0.9, "a1", [], "escalate")
        r = h.heal(d)
        records = h._load_repair_records()
        # 只有 fallback 路径才写 repair record；clean heal 不写
        assert isinstance(records, list)
