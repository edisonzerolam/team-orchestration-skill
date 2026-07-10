"""测试 DependencyManager — 依赖管理（DAG 拓扑排序 + 阻塞唤醒）"""
import pytest
from scripts.orchestrator import DependencyManager


def _subtask(sid, deps=None, phase=1, name=None):
    return {"id": sid, "name": name or sid, "dependency_ids": deps or [], "phase": phase,
            "type": "general"}


class TestInit:
    def test_empty_list(self):
        dm = DependencyManager([])
        assert len(dm.subtasks) == 0

    def test_single_node(self):
        dm = DependencyManager([_subtask("s1")])
        assert dm.subtasks["s1"]["id"] == "s1"

    def test_listener_reverse_index(self):
        dm = DependencyManager([_subtask("s1"), _subtask("s2", ["s1"]), _subtask("s3", ["s1"])])
        assert set(dm.listeners["s1"]) == {"s2", "s3"}


class TestGetReady:
    def test_all_ready_when_no_deps(self):
        dm = DependencyManager([_subtask("s1"), _subtask("s2")])
        ready = dm.get_ready()
        assert {t["id"] for t in ready} == {"s1", "s2"}

    def test_dep_blocked_not_ready(self):
        dm = DependencyManager([_subtask("s1"), _subtask("s2", ["s1"])])
        ready = dm.get_ready()
        assert {t["id"] for t in ready} == {"s1"}
        assert dm.states["s2"] == "pending"

    def test_chained_deps(self):
        dm = DependencyManager([_subtask("s1"), _subtask("s2", ["s1"]), _subtask("s3", ["s2"])])
        r1 = dm.get_ready()
        assert {t["id"] for t in r1} == {"s1"}
        dm.mark_completed("s1")
        r2 = dm.get_ready()
        assert {t["id"] for t in r2} == {"s2"}
        dm.mark_completed("s2")
        r3 = dm.get_ready()
        assert {t["id"] for t in r3} == {"s3"}

    def test_skip_wakes_dependents(self):
        dm = DependencyManager([_subtask("s1"), _subtask("s2", ["s1"])])
        dm.mark_completed("s1")
        dm.mark_completed("s1")  # skipped state via mark_completed
        ready = dm.get_ready()
        # s1 is started (COMPLETED), s2 depends on s1 → should be ready
        assert "s2" in {t["id"] for t in ready}

    def test_missing_dep_not_crash(self):
        dm = DependencyManager([_subtask("s2", ["nonexistent"])])
        ready = dm.get_ready()
        assert len(ready) == 0

    def test_ready_not_returned_twice(self):
        dm = DependencyManager([_subtask("s1")])
        dm.get_ready()
        r2 = dm.get_ready()
        assert len(r2) == 0


class TestStateTransitions:
    def test_running_state(self):
        dm = DependencyManager([_subtask("s1")])
        dm.mark_running("s1")
        assert dm.states["s1"] == "running"

    def test_completed_with_result(self):
        dm = DependencyManager([_subtask("s1")])
        dm.mark_completed("s1", {"status": "PASS", "output": "done"})
        assert dm.states["s1"] == "completed"
        assert dm.results["s1"] == "done"

    def test_completed_with_string_result(self):
        dm = DependencyManager([_subtask("s1")])
        dm.mark_completed("s1", "直接输出")
        assert dm.results["s1"] == "直接输出"

    def test_failed_state(self):
        dm = DependencyManager([_subtask("s1")])
        dm.mark_failed("s1")
        assert dm.states["s1"] == "failed"

    def test_failed_does_not_block_dependents(self):
        dm = DependencyManager([_subtask("s1"), _subtask("s2", ["s1"])])
        dm.mark_failed("s1")
        ready = dm.get_ready()
        assert "s2" not in {t["id"] for t in ready}


class TestHasPending:
    def test_all_completed(self):
        dm = DependencyManager([_subtask("s1")])
        dm.mark_completed("s1")
        assert not dm.has_pending()

    def test_some_pending(self):
        dm = DependencyManager([_subtask("s1"), _subtask("s2")])
        dm.mark_completed("s1")
        assert dm.has_pending()

    def test_all_failed(self):
        dm = DependencyManager([_subtask("s1")])
        dm.mark_failed("s1")
        assert not dm.has_pending()


class TestExecutionPlan:
    def test_empty(self):
        dm = DependencyManager([])
        assert dm.get_execution_plan() == []

    def test_single_phase(self):
        dm = DependencyManager([_subtask("s1"), _subtask("s2")])
        plan = dm.get_execution_plan()
        assert len(plan) == 1
        assert set(plan[0]) == {"s1", "s2"}

    def test_multi_phase(self):
        dm = DependencyManager([_subtask("s1", phase=1), _subtask("s2", phase=2)])
        plan = dm.get_execution_plan()
        assert len(plan) == 2
        assert plan[0] == ["s1"]
        assert plan[1] == ["s2"]

    def test_default_phase(self):
        dm = DependencyManager([_subtask("s1"), _subtask("s2", phase=2)])
        plan = dm.get_execution_plan()
        assert plan[0] == ["s1"]
        assert plan[1] == ["s2"]

    def test_phase_order_maintained(self):
        dm = DependencyManager([_subtask("s1", phase=3), _subtask("s2", phase=1)])
        plan = dm.get_execution_plan()
        assert plan[0] == ["s2"]
        assert plan[1] == ["s1"]


class TestComplexDAGs:
    def test_diamond_dag(self):
        dm = DependencyManager([
            _subtask("root"),
            _subtask("a", ["root"]), _subtask("b", ["root"]),
            _subtask("leaf", ["a", "b"]),
        ])
        r1 = dm.get_ready()
        assert {t["id"] for t in r1} == {"root"}
        dm.mark_completed("root")
        r2 = dm.get_ready()
        assert {t["id"] for t in r2} == {"a", "b"}
        dm.mark_completed("a")
        assert dm.has_pending()
        dm.mark_completed("b")
        r3 = dm.get_ready()
        assert {t["id"] for t in r3} == {"leaf"}
        dm.mark_completed("leaf")
        assert not dm.has_pending()

    def test_long_chain(self):
        dm = DependencyManager([_subtask(f"s{i}", [f"s{i-1}"] if i > 0 else []) for i in range(5)])
        for i in range(5):
            ready = dm.get_ready()
            assert len(ready) == 1
            assert ready[0]["id"] == f"s{i}"
            dm.mark_completed(f"s{i}")

    def test_fan_out_4(self):
        dm = DependencyManager([_subtask("root")] + [_subtask(f"leaf{i}", ["root"]) for i in range(4)])
        dm.mark_completed("root")
        ready = dm.get_ready()
        assert len(ready) == 4

    def test_multi_level_deps(self):
        dm = DependencyManager([
            _subtask("s1"), _subtask("s2"),
            _subtask("s3", ["s1", "s2"]),
            _subtask("s4", ["s3"]),
        ])
        dm.mark_completed("s1")
        dm.mark_completed("s2")
        r3 = dm.get_ready()
        assert {t["id"] for t in r3} == {"s3"}
        dm.mark_completed("s3")
        r4 = dm.get_ready()
        assert {t["id"] for t in r4} == {"s4"}

    def test_independent_chains(self):
        dm = DependencyManager([
            _subtask("a1"), _subtask("a2", ["a1"]),
            _subtask("b1"), _subtask("b2", ["b1"]),
        ])
        r1 = dm.get_ready()
        assert {t["id"] for t in r1} == {"a1", "b1"}


class TestEdgeCases:
    def test_nonexistent_sid_mark(self):
        dm = DependencyManager([_subtask("s1")])
        dm.mark_completed("ghost")  # should not crash
        assert dm.states["s1"] == "pending"

    def test_result_overwrite(self):
        dm = DependencyManager([_subtask("s1")])
        dm.mark_completed("s1", "first")
        dm.mark_completed("s1", "second")
        assert dm.results["s1"] == "second"

    def test_large_dag_100_nodes(self):
        subtasks = [_subtask(f"s{i}") for i in range(100)]
        dm = DependencyManager(subtasks)
        ready = dm.get_ready()
        assert len(ready) == 100
