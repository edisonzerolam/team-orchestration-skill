#!/usr/bin/env python3
"""checkpoint_manager.py — Step checkpoint / resume (P0.8).

Persists per-step state so a long orchestration can survive interruption
and resume from the last completed step instead of restarting.
"""
import os
import re
import sys
import json
import datetime
from pathlib import Path


class CheckpointManager:
    def __init__(self, root_dir):
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _valid_step(step_id):
        """TC-20260816-8：step_id 白名单校验（防 ../ 路径穿越）"""
        if not re.fullmatch(r"[\w-]+", step_id or ""):
            raise ValueError("非法 step_id（仅允许字母/数字/下划线/连字符）: %r" % step_id)
        return step_id

    def _path(self, step_id):
        self._valid_step(step_id)
        return self.root / f"ckpt-{step_id}.json"

    def save(self, step_id, state, status="done"):
        rec = {
            "step_id": step_id,
            "status": status,
            "saved_at": datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=8))
            ).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "state": state,
        }
        p = self._path(step_id)
        # 原子写（临时文件 + rename，防中断损坏）
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, p)
        return rec

    def load(self, step_id):
        p = self._path(step_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None  # 损坏检查点：按不存在处理（可重新保存），不崩溃

    def completed_steps(self, ordered_step_ids):
        done = []
        for sid in ordered_step_ids:
            rec = self.load(sid)
            if rec and rec.get("status") == "done":
                done.append(sid)
        return done

    def next_step(self, ordered_step_ids):
        """First step_id not yet completed, or None if all done."""
        done = set(self.completed_steps(ordered_step_ids))
        for sid in ordered_step_ids:
            if sid not in done:
                return sid
        return None

    def resume_plan(self, ordered_step_ids):
        done = self.completed_steps(ordered_step_ids)
        nxt = self.next_step(ordered_step_ids)
        remaining = [s for s in ordered_step_ids if s not in set(done)]
        return {"completed": done, "next": nxt, "remaining": remaining}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Checkpoint manager")
    ap.add_argument("--root", required=True, help="checkpoint directory")
    ap.add_argument("--action", required=True,
                    choices=["save", "load", "next", "plan"])
    ap.add_argument("--step", default="", help="step id")
    ap.add_argument("--state", default="{}", help="JSON state (for save)")
    ap.add_argument("--steps", default="", help="comma-separated ordered step ids")
    args = ap.parse_args()
    mgr = CheckpointManager(args.root)
    try:
        if args.action == "save":
            mgr.save(args.step, json.loads(args.state))
            print(f"saved step {args.step}")
        elif args.action == "load":
            print(json.dumps(mgr.load(args.step), ensure_ascii=False))
        elif args.action == "next":
            print("NEXT:", mgr.next_step([s for s in args.steps.split(",") if s]))
        elif args.action == "plan":
            print(json.dumps(mgr.resume_plan([s for s in args.steps.split(",") if s]),
                             ensure_ascii=False))
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
