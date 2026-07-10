"""测试 orchestrator.py — Nexus 总控调度器"""
import pytest
from scripts import orchestrator


class TestTrivialPath:
    def test_trivial_task(self):
        o = orchestrator.NexusOrchestrator()
        r = o.run("查一下Python文档")
        assert r["status"] in ("PASS", "PARTIAL")

    def test_trivial_correction_flow(self):
        o = orchestrator.NexusOrchestrator()
        r = o.run("查一下")
        assert r["status"] in ("PASS", "PARTIAL")


class TestStandardPath:
    def test_standard_task(self):
        o = orchestrator.NexusOrchestrator()
        r = o.run("分析腾讯股票")
        assert r["status"] in ("PASS", "PARTIAL")

    def test_with_task_spec(self):
        o = orchestrator.NexusOrchestrator()
        r = o.run("分析腾讯股票的财务数据")
        assert "results" in r or r["status"] in ("PASS",)


class TestAmbiguousPath:
    def test_ambiguous_task(self):
        o = orchestrator.NexusOrchestrator()
        r = o.run("优化一下")
        assert r["status"] == "CLARIFICATION_NEEDED"
        assert "question" in r


class TestSelfCheck:
    def test_extract_valid(self):
        text = "[SELF_CHECK]\ntask_id: t1\nresult: PASS\nconfidence: 0.9\n[/SELF_CHECK]"
        r = orchestrator.NexusOrchestrator._extract_self_check(text)
        assert r is not None
        assert r.get("task_id") == "t1"

    def test_extract_missing_field(self):
        text = "[SELF_CHECK]\ntask_id: t1\n[/SELF_CHECK]"
        r = orchestrator.NexusOrchestrator._extract_self_check(text)
        assert r is None

    def test_extract_no_block(self):
        r = orchestrator.NexusOrchestrator._extract_self_check("no check block here")
        assert r is None

    def test_extract_empty(self):
        r = orchestrator.NexusOrchestrator._extract_self_check("")
        assert r is None


class TestExecuteWithRetry:
    def test_fingerprint_tracking(self):
        o = orchestrator.NexusOrchestrator()
        spec = {"name": "test", "task_id": "t1", "agent_type": "test", "model_id": "m1"}
        o._execute_with_retry(spec, max_retries=1)
        assert len(o.fingerprints) > 0

    def test_retry_counts_not_negative(self):
        o = orchestrator.NexusOrchestrator()
        spec = {"name": "test", "task_id": "t2", "agent_type": "test"}
        r = o._execute_with_retry(spec, max_retries=3)
        assert r["retry_attempts"] >= 0


class TestFingerprint:
    def test_fingerprint_consistency(self):
        spec1 = {"agent_type": "test", "model_id": "m1", "task_id": "t1"}
        spec2 = {"agent_type": "test", "model_id": "m1", "task_id": "t1"}
        fp1 = orchestrator.NexusOrchestrator._fingerprint(spec1)
        fp2 = orchestrator.NexusOrchestrator._fingerprint(spec2)
        assert fp1 == fp2

    def test_fingerprint_different_task(self):
        spec1 = {"agent_type": "test", "model_id": "m1", "task_id": "t1"}
        spec2 = {"agent_type": "test", "model_id": "m1", "task_id": "t2"}
        assert orchestrator.NexusOrchestrator._fingerprint(spec1) != orchestrator.NexusOrchestrator._fingerprint(spec2)


class TestDetectAmbiguous:
    def test_short_task(self):
        r = orchestrator.NexusOrchestrator._detect_ambiguous("hi")
        assert r != ""

    def test_vague_phrase(self):
        r = orchestrator.NexusOrchestrator._detect_ambiguous("帮我优化一下")
        assert r != ""

    def test_clear_task(self):
        r = orchestrator.NexusOrchestrator._detect_ambiguous("请分析腾讯2024年财报")
        assert r == ""
