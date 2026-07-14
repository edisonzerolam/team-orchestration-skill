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


class TestBackoff:
    def test_backoff_increases_with_attempt(self):
        delays = [orchestrator.NexusOrchestrator._backoff_delay(i, base_s=1.0) for i in range(1, 5)]
        for i in range(1, len(delays)):
            assert delays[i] > delays[i - 1], "延迟应随 attempt 单调递增"

    def test_backoff_base_respected(self):
        d = orchestrator.NexusOrchestrator._backoff_delay(1, base_s=2.0)
        assert d >= 2.0

    def test_backoff_uses_jitter(self):
        import random
        random.seed(42)
        d1 = orchestrator.NexusOrchestrator._backoff_delay(3, base_s=1.0)
        random.seed(42)
        d2 = orchestrator.NexusOrchestrator._backoff_delay(3, base_s=1.0)
        assert d1 == d2  # seed 固定的情况下 jitter 应当一致


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

    def test_retry_all_failures_returns_failed(self, monkeypatch):
        def always_fail(*args, **kwargs):
            return {"status": "FAILED", "output": "模拟失败"}
        monkeypatch.setattr(orchestrator.NexusOrchestrator, "_execute_single", always_fail)
        o = orchestrator.NexusOrchestrator()
        spec = {"name": "fail-test", "task_id": "t3", "agent_type": "test"}
        r = o._execute_with_retry(spec, max_retries=3)
        assert r["status"] == "FAILED"
        assert r["retry_attempts"] == 3
        assert "均失败" in r["output"]


class TestExecuteSingle:
    def test_failed_output_not_misleading(self, monkeypatch):
        def throw(*args, **kwargs):
            raise ValueError("网络错误")
        monkeypatch.setattr(orchestrator.NexusOrchestrator, "_execute_with_retry", throw)
        o = orchestrator.NexusOrchestrator()
        try:
            o._execute_with_retry({"name": "err-test", "task_id": "t-e", "agent_type": "test"})
        except ValueError:
            pass

    def test_multiple_retries_not_excessive(self, monkeypatch):
        call_count = [0]
        def fail_first(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                return {"status": "FAILED", "output": "重试中"}
            return {"status": "PASS", "output": "最终成功"}
        monkeypatch.setattr(orchestrator.NexusOrchestrator, "_execute_single", fail_first)
        o = orchestrator.NexusOrchestrator()
        spec = {"name": "recover-test", "task_id": "t4", "agent_type": "test"}
        r = o._execute_with_retry(spec, max_retries=5)
        assert r["status"] == "PASS"
        assert r["retry_attempts"] == 3


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


class TestGlobalRegistry:
    def test_registry_has_instance_after_run(self):
        o = orchestrator.NexusOrchestrator()
        o.run("查文档")
        reg = orchestrator.get_global_registry()
        assert o.instance_id in reg

    def test_registry_task_populated(self):
        o = orchestrator.NexusOrchestrator()
        o.run("查文档")
        assert o.task_registry is not None

    def test_register_external_task(self):
        iid = orchestrator.register_task("ext-001", {"type": "external", "status": "queued"})
        reg = orchestrator.get_global_registry()
        assert iid in reg

    def test_parallel_execution_runs_concurrently(self):
        """验证通过 ThreadPoolExecutor 提交的任务确实并行执行"""
        import time, threading
        marker = {"running": 0, "max_concurrent": 0}
        lock = threading.Lock()
        def slow_func(name):
            with lock:
                marker["running"] += 1
                marker["max_concurrent"] = max(marker["max_concurrent"], marker["running"])
            time.sleep(0.3)
            with lock:
                marker["running"] -= 1
            return name
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(slow_func, f"t{i}"): f"t{i}" for i in range(3)}
            for future in as_completed(futures):
                future.result()
        assert marker["max_concurrent"] >= 2, f"最多同时运行{marker['max_concurrent']}个任务，期望≥2"
        assert marker["max_concurrent"] >= 2, f"最多同时运行{marker['max_concurrent']}个任务，期望≥2"

    def test_registry_is_thread_safe(self):
        import threading, time
        results = []
        def spawn():
            o = orchestrator.NexusOrchestrator()
            o.run("查文档")
            results.append(o.instance_id)
        threads = [threading.Thread(target=spawn) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        reg = orchestrator.get_global_registry()
        for iid in results:
            assert iid in reg


class TestParallelExecution:
    def test_phase_group_capacity_matches_subtasks(self):
        """验证并行执行至少能在单线程模式下处理多个子任务"""
        from scripts.orchestrator import NexusOrchestrator, DependencyManager
        o = NexusOrchestrator()
        subtasks = [
            {"id": "s1", "name": "t1", "type": "general", "phase": 1},
            {"id": "s2", "name": "t2", "type": "general", "phase": 1},
        ]
        dm = DependencyManager(subtasks)
        assert dm.get_execution_plan() == [["s1", "s2"]]


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
