#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rollback Manager v1.0 — 故障自动回滚引擎

提供快照/回滚 API：
  - create_snapshot(targets, label)  →  snapshot_id
  - restore_snapshot(snapshot_id)    →  恢复文件数
  - snapshot_agent_state(team, agent)→  自动快照 agent 全部状态文件
  - list_snapshots() / cleanup_snapshots()

集成点：
  - self_heal.py: 愈合前快照，验证失败自动回滚
  - orchestrator.py: 任务失败后 agent 状态回滚
"""
import json, shutil, time, argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Union

from scripts._paths import (
    SKILL_DIR as _SKILL_DIR, STATE_DIR as _STATE_DIR,
    SNAPSHOT_DIR as _SNAPSHOT_DIR, SCORES_FILE as _SCORES_FILE,
)

SKILL_DIR = _SKILL_DIR
SNAPSHOT_DIR = _SNAPSHOT_DIR
STATE_DIR = _STATE_DIR
SCORES_FILE = _SCORES_FILE


def _make_snapshot_id(label: str = "") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = label.replace(" ", "_")[:32] if label else ""
    return f"{ts}_{suffix}" if suffix else ts


def _copy_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))


class SnapshotManager:
    def __init__(self):
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def resolve_targets(*targets: Union[str, Path]) -> list[Path]:
        """解析目标路径列表，过滤不存在的文件"""
        result = []
        for t in targets:
            p = Path(t)
            if not p.is_absolute():
                p = SKILL_DIR / p
            if p.exists():
                result.append(p.resolve())
        return result

    def create_snapshot(self, targets: list[Union[str, Path]], label: str = "") -> str:
        """创建快照并返回 snapshot_id"""
        snapshot_id = _make_snapshot_id(label)
        snap_dir = SNAPSHOT_DIR / snapshot_id
        snap_dir.mkdir(parents=True, exist_ok=True)

        resolved = self.resolve_targets(*targets)
        files_map = {}
        for src in resolved:
            rel = src.relative_to(SKILL_DIR) if SKILL_DIR in src.parents else src.name
            dst = snap_dir / rel
            _copy_file(src, dst)
            files_map[str(rel)] = str(src)

        meta = {
            "snapshot_id": snapshot_id,
            "label": label or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": files_map,
            "file_count": len(files_map),
        }
        (snap_dir / "metadata.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return snapshot_id

    def snapshot_agent_state(self, team_id: str, agent_id: str, label: str = "") -> str:
        """自动快照 agent 全部状态文件（CB + repair-records + scores）"""
        targets = []

        cb_dir = STATE_DIR / "circuit-breakers"
        cb_patterns = list(cb_dir.glob(f"{agent_id}.json"))
        cb_patterns += list(cb_dir.glob(f"{agent_id}_*.json"))
        cb_patterns += list(cb_dir.glob(f"*{agent_id}*.json"))
        targets.extend(cb_patterns)

        repair = STATE_DIR / "repair-records" / f"{team_id}.json"
        if repair.exists():
            targets.append(repair)

        if SCORES_FILE.exists():
            targets.append(SCORES_FILE)

        return self.create_snapshot(targets, label or f"agent_{agent_id}")

    def restore_snapshot(self, snapshot_id: str) -> int:
        """事务性恢复快照 — 全部成功或全部回滚"""
        snap_dir = SNAPSHOT_DIR / snapshot_id
        meta_file = snap_dir / "metadata.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"快照不存在: {snapshot_id}")

        meta = json.loads(meta_file.read_text(encoding="utf-8"))

        backups = []
        try:
            for rel, orig in meta.get("files", {}).items():
                src = snap_dir / rel
                if src.exists():
                    dst = Path(orig)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if dst.exists():
                        bk = dst.with_suffix(dst.suffix + ".bak")
                        _copy_file(dst, bk)
                        backups.append((bk, dst))
                    _copy_file(src, dst)
        except Exception:
            for bk, dst in backups:
                if bk.exists():
                    _copy_file(bk, dst)
                    bk.unlink(missing_ok=True)
            raise

        for bk, _ in backups:
            bk.unlink(missing_ok=True)
        return len(meta.get("files", {}))

    def list_snapshots(self, limit: int = 50) -> list[dict]:
        """列出快照（按时间倒序）"""
        if not SNAPSHOT_DIR.exists():
            return []
        entries = []
        for d in sorted(SNAPSHOT_DIR.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            meta_file = d / "metadata.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                except Exception:
                    meta = {"snapshot_id": d.name, "error": "corrupted"}
            else:
                meta = {"snapshot_id": d.name, "label": "(no metadata)"}
            entries.append(meta)
            if len(entries) >= limit:
                break
        return entries

    def cleanup_snapshots(self, max_age_days: int = 7, dry_run: bool = True) -> int:
        """清理过期快照，返回可清理数"""
        now = time.time()
        cutoff = now - max_age_days * 86400
        count = 0
        for d in list(SNAPSHOT_DIR.iterdir()):
            if not d.is_dir():
                continue
            meta_file = d / "metadata.json"
            created = d.stat().st_mtime
            if created < cutoff:
                count += 1
                if not dry_run:
                    shutil.rmtree(str(d))
        return count


def main():
    ap = argparse.ArgumentParser(description="Rollback Manager v1.0")
    ap.add_argument("command", choices=["create", "list", "restore", "cleanup", "agent-snapshot"])
    ap.add_argument("--targets", nargs="*", default=[], help="快照目标文件路径")
    ap.add_argument("--label", default="", help="快照标签")
    ap.add_argument("--snapshot-id", default="", help="要恢复的快照 ID")
    ap.add_argument("--team", default="", help="团队 ID")
    ap.add_argument("--agent", default="", help="Agent ID")
    ap.add_argument("--max-age", type=int, default=7, help="清理天数")
    ap.add_argument("--dry-run", action="store_true", default=True, help="清理时预览模式")
    ap.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="执行清理")
    args = ap.parse_args()

    sm = SnapshotManager()

    if args.command == "create":
        sid = sm.create_snapshot(args.targets or [], args.label)
        print(json.dumps({"status": "ok", "snapshot_id": sid}, ensure_ascii=False))
    elif args.command == "list":
        snaps = sm.list_snapshots()
        print(json.dumps({"count": len(snaps), "snapshots": snaps}, ensure_ascii=False, indent=2))
    elif args.command == "restore":
        if not args.snapshot_id:
            print(json.dumps({"error": "必须提供 --snapshot-id"}, ensure_ascii=False))
            return
        count = sm.restore_snapshot(args.snapshot_id)
        print(json.dumps({"status": "ok", "files_restored": count}, ensure_ascii=False))
    elif args.command == "cleanup":
        count = sm.cleanup_snapshots(args.max_age, args.dry_run)
        print(json.dumps({"status": "ok" if not args.dry_run else "preview",
                          "to_delete": count, "dry_run": args.dry_run}, ensure_ascii=False))
    elif args.command == "agent-snapshot":
        if not args.agent:
            print(json.dumps({"error": "必须提供 --agent"}, ensure_ascii=False))
            return
        sid = sm.snapshot_agent_state(args.team or "default", args.agent, args.label)
        print(json.dumps({"status": "ok", "snapshot_id": sid}, ensure_ascii=False))


if __name__ == "__main__":
    main()
