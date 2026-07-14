"""测试 rollback-manager.py — 快照/回滚引擎"""
import json
import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

from rollback_manager import SnapshotManager, SNAPSHOT_DIR, SKILL_DIR


@pytest.fixture(autouse=True)
def _clean_snapshots():
    """每个测试前后确保目录存在并清理"""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for d in list(SNAPSHOT_DIR.iterdir()):
        if d.is_dir():
            import shutil
            shutil.rmtree(str(d))
    yield
    for d in list(SNAPSHOT_DIR.iterdir()):
        if d.is_dir():
            import shutil
            shutil.rmtree(str(d))


class TestSnapshotCore:
    def test_create_snapshot_returns_id(self):
        sm = SnapshotManager()
        sid = sm.create_snapshot([], label="test")
        assert sid
        assert "test" in sid

    def test_create_snapshot_creates_dir(self):
        sm = SnapshotManager()
        sid = sm.create_snapshot([], label="mkdir")
        assert (SNAPSHOT_DIR / sid).is_dir()

    def test_snapshot_metadata_written(self):
        sm = SnapshotManager()
        sid = sm.create_snapshot([], label="meta")
        meta_file = SNAPSHOT_DIR / sid / "metadata.json"
        assert meta_file.exists()
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        assert meta["snapshot_id"] == sid
        assert meta["file_count"] == 0

    def test_snapshot_copies_file_content(self, tmp_path):
        src = tmp_path / "test.txt"
        src.write_text("hello world", encoding="utf-8")
        sm = SnapshotManager()
        sid = sm.create_snapshot([str(src)], label="copy")
        snap_file = SNAPSHOT_DIR / sid / src.name
        assert snap_file.exists()
        assert snap_file.read_text(encoding="utf-8") == "hello world"

    def test_snapshot_skips_missing_files(self):
        sm = SnapshotManager()
        sid = sm.create_snapshot(["/nonexistent/path.json"], label="skip")
        meta = json.loads((SNAPSHOT_DIR / sid / "metadata.json").read_text(encoding="utf-8"))
        assert meta["file_count"] == 0

    def test_restore_snapshot_recovers_files(self, tmp_path):
        orig = tmp_path / "recover.txt"
        orig.write_text("original", encoding="utf-8")
        sm = SnapshotManager()
        sid = sm.create_snapshot([str(orig)], label="recover")
        orig.write_text("modified", encoding="utf-8")
        count = sm.restore_snapshot(sid)
        assert count == 1
        assert orig.read_text(encoding="utf-8") == "original"

    def test_restore_nonexistent_raises(self):
        sm = SnapshotManager()
        with pytest.raises(FileNotFoundError):
            sm.restore_snapshot("nonexistent_snapshot_12345")


class TestListSnapshots:
    def test_list_empty(self):
        sm = SnapshotManager()
        snaps = sm.list_snapshots()
        assert snaps == []

    def test_list_returns_latest_first(self):
        sm = SnapshotManager()
        sid_a = sm.create_snapshot([], label="a")
        import time; time.sleep(1)
        sid_b = sm.create_snapshot([], label="b")
        snaps = sm.list_snapshots(limit=5)
        assert snaps[0]["snapshot_id"] == sid_b
        assert snaps[1]["snapshot_id"] == sid_a


class TestCleanup:
    def test_cleanup_does_not_delete_fresh(self):
        sm = SnapshotManager()
        sm.create_snapshot([], label="fresh")
        count = sm.cleanup_snapshots(max_age_days=7, dry_run=True)
        assert count == 0

    def test_cleanup_dry_run_no_deletion(self):
        sm = SnapshotManager()
        sid = sm.create_snapshot([], label="old")
        snap_dir = SNAPSHOT_DIR / sid
        assert snap_dir.exists()
        import time; time.sleep(0.05)
        count = sm.cleanup_snapshots(max_age_days=0, dry_run=True)
        assert count == 1
        assert snap_dir.exists()


class TestSnapshotAgentState:
    def test_agent_snapshot_empty_no_error(self):
        sm = SnapshotManager()
        sid = sm.snapshot_agent_state("test-team", "no-such-agent")
        assert sid

    def test_agent_snapshot_captures_cb(self, tmp_path):
        cb_dir = pathlib.Path(__file__).parent.parent / "shared" / "team-brain" / "circuit-breakers"
        cb_dir.mkdir(parents=True, exist_ok=True)
        cb_file = cb_dir / "test-agent-cb.json"
        cb_file.write_text(json.dumps({"name": "test-agent-cb", "state": "CLOSED"}), encoding="utf-8")
        sm = SnapshotManager()
        sid = sm.snapshot_agent_state("test-team", "test-agent-cb")
        meta = json.loads((SNAPSHOT_DIR / sid / "metadata.json").read_text(encoding="utf-8"))
        assert meta["file_count"] >= 1

    def test_rollback_restores_cb_state(self, tmp_path):
        cb_dir = pathlib.Path(__file__).parent.parent / "shared" / "team-brain" / "circuit-breakers"
        cb_dir.mkdir(parents=True, exist_ok=True)
        cb_file = cb_dir / "rollback-agent.json"
        cb_file.write_text(json.dumps({"name": "rollback-agent", "state": "CLOSED"}), encoding="utf-8")
        sm = SnapshotManager()
        sid = sm.snapshot_agent_state("test-team", "rollback-agent", "rollback_test")
        cb_file.write_text(json.dumps({"name": "rollback-agent", "state": "OPEN"}), encoding="utf-8")
        count = sm.restore_snapshot(sid)
        assert count >= 1
        restored = json.loads(cb_file.read_text(encoding="utf-8"))
        assert restored["state"] == "CLOSED"


class TestSelfHealIntegration:
    def test_pipeline_snapshot_before_heal(self, monkeypatch):
        from self_heal import SelfHealPipeline
        pipe = SelfHealPipeline("test-s7", "agent-s7", rollback_enabled=False)
        ctx = {"error": "timeout", "agent_id": "agent-s7"}
        result = pipe.run(ctx)
        assert "timeline" in result
        assert result.get("status") in ("healed", "clean", "escalated")

    def test_pipeline_rollback_disabled_no_error(self, monkeypatch):
        from self_heal import SelfHealPipeline
        import importlib
        import scripts.self_heal as sh_mod
        importlib.reload(sh_mod)
        pipe = SelfHealPipeline("test-s7-off", "agent-s7-off", rollback_enabled=False)
        ctx = {"error": "hang", "agent_id": "agent-s7-off"}
        result = pipe.run(ctx)
        assert result["status"] in ("healed", "clean", "escalated")

    def test_pipeline_returns_rollback_snapshot_id_on_healed(self, monkeypatch):
        from self_heal import SelfHealPipeline
        pipe = SelfHealPipeline("test-s7-rsid", "agent-s7-rsid")
        ctx = {"error": "tool_failure", "agent_id": "agent-s7-rsid"}
        result = pipe.run(ctx)
        if result.get("status") == "healed":
            assert "rollback_snapshot_id" in result


class TestOrchestratorIntegration:
    def test_execute_retry_fail_triggers_rollback(self, monkeypatch):
        import scripts.orchestrator as orch_mod
        from scripts.orchestrator import NexusOrchestrator
        def always_fail(*args, **kwargs):
            return {"status": "FAILED", "output": "模拟失败"}
        monkeypatch.setattr(orch_mod.NexusOrchestrator, "_execute_single", always_fail)
        o = NexusOrchestrator()
        spec = {"name": "s7-fail", "task_id": "s7-1", "agent_type": "s7-agent"}
        r = o._execute_with_retry(spec, max_retries=2)
        assert r["status"] == "FAILED"
        assert r.get("rollback_triggered") is True

    def test_execute_retry_success_no_rollback(self, monkeypatch):
        import scripts.orchestrator as orch_mod
        from scripts.orchestrator import NexusOrchestrator
        def always_pass(*args, **kwargs):
            return {"status": "PASS", "output": "ok"}
        monkeypatch.setattr(orch_mod.NexusOrchestrator, "_execute_single", always_pass)
        o = NexusOrchestrator()
        spec = {"name": "s7-pass", "task_id": "s7-2", "agent_type": "s7-agent"}
        r = o._execute_with_retry(spec, max_retries=2)
        assert r["status"] == "PASS"
        assert "rollback_triggered" not in r
