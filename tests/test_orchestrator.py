"""测试 orchestrator.py — Nexus 总控调度器"""
import pytest
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("orch",
    str(Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "scripts" / "orchestrator.py"))
orch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orch)


class TestTrivialPath:
    def test_trivial_task(self):
        o = orch.NexusOrchestrator()
        r = o.run("查一下Python文档")
        assert r["status"] == "PASS"

    def test_trivial_correction_flow(self):
        """Trivial 任务反向校验失败时升级"""
        o = orch.NexusOrchestrator()
        r = o.run("查一下")
        assert r["status"] in ("PASS", "PARTIAL")


class TestStandardPath:
    def test_standard_task(self):
        o = orch.NexusOrchestrator()
        r = o.run("分析腾讯股票")
        assert r["status"] in ("PASS", "PARTIAL")

    def test_with_task_spec(self):
        o = orch.NexusOrchestrator()
        r = o.run("分析腾讯股票的财务数据")
        assert "results" in r or r["status"] in ("PASS",)


class TestAmbiguousPath:
    def test_ambiguous_task(self):
        o = orch.NexusOrchestrator()
        r = o.run("优化一下")
        assert r["status"] == "CLARIFICATION_NEEDED"
        assert "question" in r


class TestSelfCheck:
    def test_extract_valid(self):
        text = "[SELF_CHECK]\ntask_id: t1\nresult: PASS\nconfidence: 0.9\n[/SELF_CHECK]"
        r = orch.NexusOrchestrator._extract_self_check(text)
        assert r is not None
        assert r.get("task_id") == "t1"

    def test_extract_missing_field(self):
        text = "[SELF_CHECK]\ntask_id: t1\n[/SELF_CHECK]"
        r = orch.NexusOrchestrator._extract_self_check(text)
        assert r is None  # 缺 result 和 confidence

    def test_extract_no_block(self):
        r = orch.NexusOrchestrator._extract_self_check("no check block here")
        assert r is None

    def test_extract_empty(self):
        r = orch.NexusOrchestrator._extract_self_check("")
        assert r is None


class TestCorrectionLoop:
    def test_max_retries_exceeded(self):
        o = orch.NexusOrchestrator()
        r = o._correction_loop({"task_id": "t1"}, ["error1"], "", 3)
        assert r["status"] == "FAILED"

    def test_fingerprint_tracking(self):
        o = orch.NexusOrchestrator()
        spec = {"task_id": "t1", "agent_type": "test", "model_id": "m1"}
        o._correction_loop(spec, ["error x"], "", 1)
        assert "m1" in o.fingerprints
